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
   return "MASTER" if ismaster else "SLAVE"

def str_action(ismaster=None):
    if not ismaster : ismaster = ISMASTER
    return "REPLACE S3 OBJECT WITH LOCAL ONES" if ismaster else "REPLACE LOCAL OBJECTS WITH THOSE STORED IN S3"


def stopscreen():
    input("\n > Press ENTER to continue...")


def clear():
    """Pulisce lo schermo"""
    os.system('cls' if os.name=='nt' else 'clear')


def filter_files(data:list):
    """Regole di esclusione
    dalla sincronizzazione file.
    In questo esempio escludo sempre i file della cache di Python
    """
    return [ d for d in data if d.find("__pycache__") == -1 ]


def normalize_external_path(p):
    # al contrario di come succede internamente
    # i path directory provenienti dagli input esterni,
    # percorsi di mapping
    # non devono terminare con /
    # e anche in windows il separatore di path deve essere  /
    r = p.replace("\\","/")
    if r.endswith("/"):
        r = r[:-1]
    return r


def slipt_s3path(s3path):
    """Return a tuple with bucket name and prefix from a given s3path.
    """
    s3_part = s3path.split("/")
    bucket = s3_part[0]
    prefix = "/".join( s3_part[1:] ) if len(s3_part) > 1 else ""
    return bucket, prefix

def ls_master(path):
    return ls_localpath(path) if ISMASTER else ls_s3path(path)

def ls_slave(path):
    return ls_s3path(path) if ISMASTER else ls_localpath(path)

def ls_localpath(path):
    """
    Return generator of objects contained in 'path'.

    Path objects are relative to 'path'
    and directories endswith "/" char.
    """
        # con aggiunta di os.sep = "/" non dovrebbe essere piu necessario 'norm'...
    norm = lambda p: p.replace("\\","/")
    base = norm(path)
    make_relative = lambda p: norm(p).replace(base, "")[1:]
    for root, dirs, files in os.walk(base):
        for name in files:
            yield make_relative(os.path.join(root, name))
        for name in dirs:
            yield make_relative(os.path.join( root, name ) + "/") 

def ls_s3path(s3path):
    """
    Return a generator of objects contained in 's3path'.

    Path objects are relative to 's3path'
    and directories endswith "/" char.
    """
    bucket, prefix = slipt_s3path(s3path)
    try:
        objects = S3CLIENT.list_objects_v2( Bucket=bucket, Prefix=prefix)
    except:
        print(" !! S3 PATH '{}' CONNECTION ERROR: BUCKET NOT FOUND or ACCESS DENIED or NO INTERNET ACCESS.".format(s3path))
        return []

    if objects.get("Contents") is None:
        print(" !! S3 PATH '{}' ERROR: NO HAVE CONTENTS.".format(s3path))
        return []

    for object in objects["Contents"]:
        # rendo il percorso relativo al prefix
        #  (+1 per rimuovere il '/' iniziale )
        name = object["Key"][len(prefix)+1:]
        # la radice diventa un file vuoto che non includo
        if name != "":
            yield name

################

def get_master(path):
    f = get_localfile if ISMASTER else get_s3file
    return f(path)

def get_slave(path):
    f = get_s3file if ISMASTER else get_localfile
    return f(path)

def get_localfile(path):
    with open( path, "rb" ) as file:
        return file.read()

def get_s3file(s3filepath):
    bucket, prefix = slipt_s3path(s3filepath)
    file = S3RESOURCE.Object(bucket, prefix).get()
    return file['Body'].read()

################

def rm_slave(path):
    f = rm_s3object if ISMASTER else rm_localobject
    return f(path)

# COMMENTATA PER NON SI DOVREBBE MAI USARE QUESTA FUNZIONE
#def rm_master(path):
#    rm_localobject(path) if ISMASTER else return rm_s3object(path)

def rm_localobject(object):
    print(" LOCAL DEL: {}".format( object ))
    if os.path.isdir(object):
        shutil.rmtree(object)
    elif os.path.isfile(object):
        os.remove(object)
    # e' utile fare una pausa prima per permettere al sistema di rilasciare i files
    sleep(3)
    return True

def rm_s3object(s3object):
    print(" S3 DEL: {}".format( s3object ))
    bucket, prefix = slipt_s3path(s3object)
    b = S3RESOURCE.Bucket(bucket)
    try:
        request = b.objects.filter(Prefix=prefix).delete()
    except Exception as e:
        print(e)
        return False
    else:
        return True

#############
# COMMENTATA PER NON SI DOVREBBE MAI USARE QUESTA FUNZIONE
#def mk_master(path, data=None):
#    return mk_localpath(path, data=None) if ISMASTER else mk_s3path(path, data=None)

def mk_slave(path, data=None):
    f = mk_s3path if ISMASTER else mk_localpath
    return f(path, data)

def mk_localpath(path, data=None):
    print(" LOCAL CREATE: {}".format( path ))
    if data:
        # internamente le directory terminano sempre con "/"
        directory = "/".join(path.split("/")[:-1]) + "/"
    else:
        directory = path

    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    if data:
        with open(path, "wb") as file:
            file.write(data)
    result = True
    return result


def mk_s3path(s3object, data=None):
    print(" S3 CREATE: {}".format(s3object))

    bucket, prefix = slipt_s3path(s3object)
    object = S3RESOURCE.Object( bucket, prefix )
    if data:
        request = object.put(Body=data)
    else:
        # crea directory
        request = object.put()    
    result = request['ResponseMetadata']['HTTPStatusCode'] == 200
    return result


def copy(origin, destination, objects):
    print("""
 EXECUTE TRANSFER:

    * FROM '{}' ORIGIN: '{}'
   >> TO '{}' DESTINATION: '{}'
""".format(
        "LOCAL" if ISMASTER else "S3",
        origin,
        "S3" if ISMASTER else "LOCAL",
        destination ))

    alert_text = DEL_ALERT.format(
        "S3 PATH" if ISMASTER else "LOCAL PATH",
        destination)

    confirm = "y" if CONFIG['MAIN'].getboolean('skip_delete_alert') else input(alert_text).lower()
    if confirm == "y":
        rm_slave(destination)
        # ricreo la directory principale (le directory devono terminare con /
        mk_slave(destination + "/")
        for obj in objects:
            data = None if obj.endswith("/") else get_master( "/".join([origin, obj]) )
            ###if data is None:
            ###    assert objendswith("/"), "If data; object filename can't be endswith /"
            ###else:
            ###    assert not obj.endswith("/"), "If data is None, object must be a directory. Directory ends with /"
            mk_slave("/".join([destination, obj]), data)

    else:
        print("NOTHING DO")


def update_script():
    if CONFIG['MAIN'].get('url_script_update', None):
        current_path = os.path.dirname(os.path.realpath(__file__))
        #script_path = os.path.join( current_path, "s323.py" )
        #os.remove(script_path)
        #sleep(2)
        #urllib.request.urlretrieve(CONFIG['MAIN']['url_script_update'], script_path )
    else:
        print("FILE CONFIG ERROR: not found 'url_script_update'")
        stopscreen()
        return False

    return True

def input_s3path_maps(save_configuration=True):
    """Ask user and save in configuration the s3path of mapping files

    Return: 
        - maps list
        - None (on error or user exit)
    """
    while True:
        clear()
        i = input(" > Insert S3 path contains mapping files for '{}' [x to Exit]: ".format(mode_name(ISMASTER)))
        if i.lower() == "x":
            return
        if i.endswith("/"):
            i = i[:-1]
        maps = load_maps_from_s3path(i)
        if maps:
            if save_configuration:
                CONFIG[mode_name(ISMASTER)]['s3_path_mapfiles'] = i
                save_config()
            return maps

def load_maps_from_s3path(s3path):
    maps = []
    for object in ls_s3path(s3path):
        if object.endswith(".json"):
            file = get_s3file( "/".join([s3path, object] ))
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
    stopscreen()


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

    # se nella definizione è presente un lista di files
    # sincronizzo solo quelli
    # ATTENZIONE eventuali altri file presenti localmenti nella directory verranno comunque rimossi!
    # Altrimenti sincronizzo tutti i file presenti nel percorso S3 specificato

    if ISMASTER:
        origin = 'master'
        destination = 's3'
    else:
        origin = 's3'
        destination = 'slave'

    objects = xmap.get('objects')
    if not objects: 
        objects = ls_master(xmap[origin])
    copy(xmap[origin], xmap[destination], objects)


def httpd_restart():
    """Riavvia il servizio HTTPD"""
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
            stopscreen()

        elif i == "up":
            if update_script():
                print(" DONE. Restart script.")
                break

        elif i == "rh":
            httpd_restart()
            stopscreen()

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

            stopscreen()


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
    s3path = CONFIG[mode_name(ISMASTER)].get("s3_path_mapfiles")
    if s3path:
        maps = load_maps_from_s3path(s3path)
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

