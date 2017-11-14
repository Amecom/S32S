#!/usr/bin/python3
# -*- coding: utf-8 -*-

import configparser
import os
import boto3
import shutil
import json
import subprocess
import urllib.request
import errno
from time import sleep

S3CLIENT = boto3.client('s3', config = boto3.session.Config(signature_version = 's3v4'))
S3RESOURCE =  boto3.resource('s3', config=boto3.session.Config(signature_version='s3v4'))
CONFIG = configparser.ConfigParser()
CONFIG_FILENAME = 's32s.cf'
ISMASTER = None
MAPS = None
os.sep = "/"

DEL_ALERT = """
  ********* WARNING  ********* 

  ALL OBJECTS STORED in {}: '{}'
  WILL BE PERMANENTLY DELETE.

 ***************************** 

 > Confirm permanent delete [y/n] ? """


def mode_name(ismaster):
    """Return string name used, for examples, in config."""
    return "MASTER" if ismaster else "SLAVE"

def str_action(ismaster=None):
    """Return string that describes transfert mode."""
    if not ismaster : ismaster = ISMASTER
    return "REPLACE S3 OBJECT WITH LOCAL ONES" if ismaster else "REPLACE LOCAL OBJECTS WITH THOSE STORED IN S3"

def enter_to_continue():
    """Create a break to allow the user to read output."""
    input("\n > Press ENTER to continue...")

def clear():
    """Clear Screen."""
    os.system('cls' if os.name=='nt' else 'clear')


##def filter_files(data:list):
##    """Regole di esclusione
##    dalla sincronizzazione file.
##    In questo esempio escludo sempre i file della cache di Python
##    """
##    return [ d for d in data if d.find("__pycache__") == -1 ]


def normalize_external_path(path):
    """Normalize 'path'.
    
    Return external path.
    External paths, contrary to what happens internally,
    NOT ENDS WITH / and
    path separator is always /
    """
    r = path.replace("\\","/")
    if r.endswith("/"):
        r = r[:-1]
    return r


def slipt_s3path(path):
    """Split path into bucket and prefix.

    Return a tuple with bucket name and prefix.
    Prefix can be a empty string."""
    p = path.split("/")
    bucket = p[0]
    prefix = "/".join( p[1:] ) if len(p) > 1 else ""
    return bucket, prefix


def get_master_file(filepath):
    """Return binary data from 'filepath' in master repository."""
    f = get_pc_file if ISMASTER else get_s3_file
    return f(filepath)

def get_slave_file(filepath):
    """Return binary data from 'filepath' in slave repository."""
    f = get_s3_file if ISMASTER else get_pc_file
    return f(filepath)

def get_pc_file(filepath):
    """Return binary data from 'filepath' in local files."""
    with open( filepath, "rb" ) as file:
        return file.read()

def get_s3_file(filepath):
    """Return binary data from 'filepath' in S3 files."""
    bucket, prefix = slipt_s3path(filepath)
    file = S3RESOURCE.Object(bucket, prefix).get()
    return file['Body'].read()


def ls_master_path(path):
    """Return a generator with list of objects stored in master repository.

    If current run mode is master the master repository is local repository
    otherwise is S3 repository
    """
    return ls_pc_path(path) if ISMASTER else ls_s3_path(path)

def ls_slave_path(path):
    """Return a generator with list of objects stored in slave repository

    If current run mode is master the slave repository is local repository
    otherwise is S3 repository.
    """
    return ls_s3_path(path) if ISMASTER else ls_pc_path(path)

def ls_pc_path(path):
    """Return generator of list of objects stored in local 'path'.

    Objects's Path is relative to given 'path'
    and directories ends with "/" char.
    """
        # norm function with os.sep = "/" ca be unnecessary
    norm = lambda p: p.replace("\\","/")
    base = norm(path)
    make_relative = lambda p: norm(p).replace(base, "")[1:]
    for root, dirs, files in os.walk(base):
        for name in files:
            yield make_relative(os.path.join(root, name))
        for name in dirs:
            yield make_relative(os.path.join( root, name ) + "/") 

def ls_s3_path(path):
    """Return a generator of list objects stored in S3 'path'.

    Objects Path are relative to 'path'
    and directories ends with "/" char.

    If error return empty list.
    """
    bucket, prefix = slipt_s3path(path)
    try:
        objects = S3CLIENT.list_objects_v2( Bucket=bucket, Prefix=prefix)
    except:
        print(" !! ERROR S3 PATH '{}': BUCKET NOT FOUND or ACCESS DENIED or NO INTERNET ACCESS.".format(path))
        return []

    if objects.get("Contents") is None:
        print(" !! ERROR S3 PATH '{}': PATH NOT HAVE CONTENTS OR NOT EXISTS.".format(path))
        return []

    for object in objects["Contents"]:
        # rendo il percorso relativo al prefix
        #  (+1 per rimuovere il '/' iniziale )
        name = object["Key"][len(prefix)+1:]
        # la radice diventa un file vuoto che non includo
        if name != "":
            yield name


def rm_slave_object(object_path):
    """Drop all contents from slave repository 'object_path'."""
    f = rm_s3_object if ISMASTER else rm_pc_object
    return f(object_path)

# UNUSED FUNCTION COMMENTED FOR SECURITY REASON
#def rm_master_object(object_path):
#    """Remove all contents from 'object_path' in master repository."""
#    rm_pc_object(path) if ISMASTER else return rm_s3_object(path)

def rm_pc_object(object_path):
    """Drop all contents from local 'object_path'."""
    print(" LOCAL DEL: {}".format( object_path ))
    if os.path.isdir(object_path):
        shutil.rmtree(object_path)
    elif os.path.isfile(object_path):
        os.remove(object_path)
    # e' utile fare una pausa prima per permettere al sistema di rilasciare i files
    sleep(3)
    return True

def rm_s3_object(object_path):
    """Drop all contents from S3 'object_path'."""
    print(" S3 DEL: {}".format(object_path))
    bucket, prefix = slipt_s3path(object_path)
    b = S3RESOURCE.Bucket(bucket)
    try:
        request = b.objects.filter(Prefix=prefix).delete()
    except Exception as e:
        print(e)
        return False
    else:
        return True


# UNUSED FUNCTION COMMENTED FOR SECURITY REASON
#def mk_master_object(object_path, data=None):
#    """Create object in master repository 'object_path'."""
#    f = mk_pc_object if ISMASTER else mk_s3_object
#    return f(object_path, data)

def mk_slave_object(object_path, data=None):
    """Create object in slave repository 'object_path'."""
    f = mk_s3_object if ISMASTER else mk_pc_object
    return f(object_path, data)

def mk_pc_object(object_path, data=None):
    """Create object on local 'object_path'."""
    print(" LOCAL CREATE: {}".format( object_path ))
    if data:
        # PATH IN THE SCRIPT ALWAYS MUST ENDS WITH "/"
        directory = "/".join(object_path.split("/")[:-1]) + "/"
    else:
        directory = object_path

    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    if data:
        with open(object_path, "wb") as file:
            file.write(data)

    return True


def mk_s3_object(object_path, data=None):
    """Create object on S3 'object_path'."""
    print(" S3 CREATE: {}".format(object_path))
    bucket, prefix = slipt_s3path(object_path)
    object = S3RESOURCE.Object( bucket, prefix )
    if data:
        request = object.put(Body=data)
    else:
        # crea directory
        request = object.put()    
    result = request['ResponseMetadata']['HTTPStatusCode'] == 200
    return result




def update_script():
    if CONFIG['MAIN'].get('url_script_update', None):
        current_path = os.path.dirname(os.path.realpath(__file__))
        #script_path = os.path.join( current_path, "s323.py" )
        #os.remove(script_path)
        #sleep(2)
        #urllib.request.urlretrieve(CONFIG['MAIN']['url_script_update'], script_path )
    else:
        print("FILE CONFIG ERROR: not found 'url_script_update'")
        enter_to_continue()
        return False

    return True

def input_s3path_maps(save_configuration=True):
    """Ask user and save in configuration the s3 path of mapping files

    Return: 
        - maps list
            or
        - None (on error or user exit)
    """
    while True:
        clear()
        i = input(" > Insert S3 path contains mapping files for '{}' [x to Exit]: ".format(mode_name(ISMASTER)))
        if i.lower() == "x":
            return
        i = normalize_external_path(i)
        maps = load_maps_from_s3path(i)
        if maps:
            if save_configuration:
                CONFIG[mode_name(ISMASTER)]['s3_path_mapfiles'] = i
                save_config()
            return maps

def load_maps_from_s3path(path):
    maps = []
    for object in ls_s3_path(path):
        if object.endswith(".json"):
            file = get_s3_file( "/".join([path, object] ))
            xmap = json.loads(file.decode('utf8'))
            for m in xmap:
                m['filename'] = object
                for prop in ["master","s3", "slave"]:
                    if m.get(prop):
                        m[prop] = normalize_external_path(m[prop])
            maps += xmap
    else:
        # on successuful end for
        if is_valid_maps(maps):
            if CONFIG['MAIN'].getboolean('reorder_map_elements'):
                maps = sorted(maps, key=lambda k:k['name'])
            return maps

    print( "*** MAP ERROR ***" )
    enter_to_continue()


def is_valid_maps(maps):

    def check_path_error(path):
        if path[0] == "~":
            return "path can't start with ~"
        return None

    if len(maps) == 0:
        print("EMPTY MAPS") 
        return False

    for n, e in enumerate(maps):

        name = e.get("name")
        s3_path = e.get("s3")
        master_path = e.get("master")
        slave_path = e.get("slave")

        if name is None:
            print( "MAP ERROR Filename '{}' list element number '{}': empty 'name' property.".format(e['filename'], n) ) 
            break

        if s3_path is None:
            print( "MAP ERROR Filename '{}' list element name '{}': empty 's3' property.".format(e['filename'], name) )
            break

        if ISMASTER:
            if master_path is None:
                print( "MAP ERROR Filename '{}' list element name '{}': empty 'master' property.".format(e['filename'], name) )
                break

            err = check_path_error(master_path)
            if err:
                print( "MAP ERROR Filename '{}' list element name '{}': {}.".format(e['filename'], name, err) )
                break

        else:
            if slave_path is None:
                print( "MAP ERROR Filename '{}' list element name '{}': empty 'slave' property.".format(e['filename'], name) )
                break

            err = check_path_error(slave_path)
            if err:
                print( "MAP ERROR Filename '{}' list element name '{}': {}.".format(e['filename'], name, err) )
                break
    else:
        # uscita dal ciclo senza errori
        return True

    return False


def transfer(xmap):

    if ISMASTER:
        origin_info = {
            'name' : 'master',
            'location' : 'LOCAL'
            }
        destination_info = {
            'name' : 's3',
            'location' : 'REMOTE'
            }
    else:
        origin_info = {
            'name' : 's3',
            'location' : 'REMOTE'
            }
        destination_info = {
            'name' : 'slave',
            'location' : 'LOCAL'
            }

    # retrieve path from map property
    origin = xmap[origin_info['name']] 
    destination = xmap[destination_info['name']]

    objects = xmap.get('objects')
    # if not objects, get all objects in origin path.
    if not objects: 
        objects = ls_master_path(origin)

    print("""
 TRANSFER INFORMATION:

    * FROM {} ORIGIN : '{}'
   >> TO {} DESTINATION : '{}'
""".format(
        ( origin_info['location'], origin_info['name'] ),
        origin,
        ( destination_info['location'], destination_info['name'] ),
        destination ))

    alert_text = DEL_ALERT.format(
        ( destination_info['location'], destination_info['name'] ),
        destination)

    skip_alert = CONFIG['MAIN'].getboolean('skip_delete_alert')

    confirm = "y" if skip_alert else input(alert_text).lower()
    if confirm == "y":
        rm_slave_object(destination)
        # need add '/' to 'mk_slave_object' destination because external path don't have
        mk_slave_object(destination + "/")
        for obj in objects:
            data = None if obj.endswith("/") else get_master_file( "/".join([origin, obj]) )
            mk_slave_object("/".join([destination, obj]), data)

    else:
        print(" NOTHING DO!")



def httpd_restart():
    """Restart HTTPD service """
    cmd = "sudo service httpd restart"
    subprocess.check_call(cmd.split())


def switch_mode():
    CONFIG['MAIN']['ismaster'] = str(not ISMASTER)
    save_config()
    main()


def input_is_master():
    # master deve essere 1 (true)
    option = ("1", "0")
    while True:
        clear()
        print( """
SELECT RUN MODE:

    {} = MASTER - {}
    {} = SLAVE - {}

""".format(
    option[0],
   str_action(True), 
    option[1],
   str_action(False) ))

        i = input( " > Enter input {}: ".format(option))
        if i not in option:
            continue
        else:
            CONFIG['MAIN']['ismaster'] = i
            save_config()
            break
    return bool(int(i))

def show_maps():

    for n, m in enumerate( MAPS ):
        if ISMASTER:
            print("""\
{} - '{}'
    FROM ORIGIN (LOCAL MASTER) : {}
    TO DESTINATION  (S3)       : {}
""".format( m.get('name'), m.get('filename'), m.get('master'), m.get('s3') ) )

        else:
            print("""\
{} - '{}'
    FROM ORIGIN (S3)             : {}
    TO DESTINATION (LOCAL SLAVE) : {}
""".format( m.get('name'), m.get('filename'), m.get('s3'), m.get('slave') ) )


def menu():
    global MAPS

    while True:

        clear()

        print(" *** MODE: {} | S3 MAPS PATH: {} ***".format(
            mode_name(ISMASTER),
            CONFIG[mode_name(ISMASTER)].get("s3_path_mapfiles")
            )
        )

        print("""
 OPTIONS:

  md = Maps Details
  mr = Maps Reload
  mo = Maps Open
  sm = Switch to {} Mode
  up = Script Update
   x = Exit""".format( 
        mode_name(not ISMASTER)
    ))

        print("\n {}:\n".format(str_action()))
        for n, m in enumerate( MAPS ):
            print(" {:>3} = {}".format( n , m['name'] ) )

        print(" all = REPLACE ALL")

        i = input("\n > Enter input: ").lower()

        clear()

        if i == "x":
            break

        elif i == "sm":
            switch_mode()
            break

        elif i == "mr":
            maps = get_maps()
            if maps : MAPS = maps

        elif i == "mo":
            maps = input_s3path_maps()
            if maps : MAPS = maps

        elif i == "md":
            show_maps()
            enter_to_continue()

        elif i == "up":
            if update_script():
                print(" DONE. Restart script.")
                break

        elif i == "rh":
            httpd_restart()
            enter_to_continue()

        else:

            if i == "all":
                selected_xmap = [ x for x in range(len(MAPS))]
            else:
                try:
                    i = int(i)
                except:
                    # invalid choice
                    continue
                else:
                    if i >= 0 and i < len(MAPS):
                        selected_xmap = [ i ]
                    else:
                        # invalid choice
                        continue

            for xmap in selected_xmap:
                transfer(MAPS[xmap])

            enter_to_continue()


def load_config():
    global CONFIG
    if not CONFIG.read(CONFIG_FILENAME):
        load_default_config()
        save_config()


def load_default_config():
    global CONFIG
    CONFIG['MAIN'] = {
        'url_script_update': "https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py",
        'reorder_map_elements': True,
        'skip_delete_alert': False,
        'ismaster': ''
        }
    CONFIG[mode_name(True)] = {
        's3_path_mapfiles': ''
        }
    CONFIG[mode_name(False)] = {
        's3_path_mapfiles': ''
        }


def save_config():
    with open(CONFIG_FILENAME, 'w') as configfile:
        CONFIG.write(configfile)


def get_maps():
    path = CONFIG[mode_name(ISMASTER)].get("s3_path_mapfiles")
    if path:
        maps = load_maps_from_s3path(path)
        if maps:
            return maps

    # se non è presente una mappa valida nel file di configurazione
    return input_s3path_maps()


def main():
    global ISMASTER
    global MAPS

    clear()
    load_config()

    if CONFIG['MAIN'].get('ismaster'):
        ISMASTER = CONFIG['MAIN'].getboolean('ismaster')
    else:
        ISMASTER = input_is_master()
        clear()

    print(" Loading maps... ")
    maps = get_maps()
    if maps:
        MAPS = maps
        menu()
    else:
        print(" *** Configuration fails, restart the script *** ")

if __name__ == "__main__":
    main()

