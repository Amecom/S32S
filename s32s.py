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

TXT_TRANSFER_INFO = """
 TRANSFER INFORMATION:

    * FROM {origin_info} ORIGIN : '{origin_path}'
   >> TO {destination_info} DESTINATION : '{destination_path}'
"""
TXT_DELETE_WARNING = """
  ********* WARNING  ********* 

  ALL OBJECTS STORED in {info}: '{path}'
  WILL BE PERMANENTLY DELETE.

 ***************************** 
"""
TXT_RESTART = " Restart script."
TXT_MODE_INFO = " *** MODE: {mode} | S3 MAPS PATH: {mapspath} ***"
TXT_ACTION_MASTER = "REPLACE S3 OBJECT WITH LOCAL ONES"
TXT_ACTION_SLAVE = "REPLACE LOCAL OBJECTS WITH THOSE STORED IN S3"
TXT_NOTDO = " NOTHING DONE!"
TXT_DO = " DONE!"
TXT_LOADING_MAPS = " Loading maps... "
TXT_REPLACE_ALL_OPTION = " all = REPLACE ALL"
TXT_MENU_MODE = """
SELECT RUN MODE:

    {inp_master} = MASTER - {info_master}
    {inp_slave} = SLAVE - {info_slave}
"""
TXT_MENU_OPTION = """
 OPTIONS:

  md = Maps Details
  mr = Maps Reload
  mo = Maps Open
  sm = Switch to {mode}
  up = Script Update
   x = Exit
"""

TXT_INPUT = "\n > Enter input: "
TXT_INPUT_OPTION = "\n > Enter input {option}: "
TXT_INPUT_ENTER = "\n > Press ENTER to continue..."
TXT_INPUT_INSERT_MAPS_PATH = "\n > Insert S3 path contains mapping files for '{mode}' [x to Exit]: "
TXT_INPUT_DELETE_CONFIRM = " > Confirm permanent delete [y/n] ?" 

TXT_ERR_CONFIGURATION_FAILS = " !! ERROR Configuration fails."
TXT_ERR_S3_LIST_CONNECTION = " !! ERROR S3 PATH '{path}': bucket not found or access denied or no internet access."
TXT_ERR_S3_LIST_CONTENTS = " !! ERROR S3 PATH '{path}': path does not have a contents or not exists."
TXT_ERR_SCRIPT_UPDATE_CONFIG = " !! ERROR not found 'url_script_update' property in configuration file."
TXT_ERR_MAP_INVALID = " !! ERROR IN MAPS"
TXT_ERR_MAP_LINUX_USERHOME = " !! ERROR MAP {path}: Path can't start with ~"
TXT_ERR_MAP_EMPTY = " !! ERROR EMPTY MAPS"
TXT_ERR_MAP_EMPTY_NAME = " !! ERROR MAP '{filename}' list element number '{number}' does not have 'name' property."
TXT_ERR_MAP_EMPTY_S3 = " !! ERROR MAP '{filename}' list element name '{name}' does not have 's3' property."
TXT_ERR_MAP_EMPTY_MASTER = " !! ERROR MAP '{filename}' list element name '{name}' does not have 'master' property."
TXT_ERR_MAP_EMPTY_SLAVE = " !! ERROR MAP '{filename}' list element name '{name}' does not have 'slave' property."
TXT_DELETE_OBJECT = " {storage} DELETE: {object}"
TXT_CREATE_OBJECT = " {storage} CREATE: {object}"


def mode_name(ismaster):
    """Return string name used, for examples, in config."""
    return "MASTER" if ismaster else "SLAVE"

def str_action(ismaster=None):
    """Return string that describes transfert mode."""
    if not ismaster : ismaster = ISMASTER
    return  TXT_ACTION_MASTER if ismaster else TXT_ACTION_SLAVE

def enter_to_continue():
    """Create a break to allow the user to read output."""
    input(TXT_INPUT_ENTER)

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
    Prefix can be a empty string.
    """
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
        print(TXT_ERR_S3_LIST_CONNECTION.format(path=path))
        return []

    if objects.get("Contents") is None:
        print(TXT_ERR_S3_LIST_CONTENTS.format(path=path))
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
    print(TXT_DELETE_OBJECT.format(storage="LOCAL", object=object_path ))
    if os.path.isdir(object_path):
        shutil.rmtree(object_path)
    elif os.path.isfile(object_path):
        os.remove(object_path)
    # e' utile fare una pausa prima per permettere al sistema di rilasciare i files
    sleep(3)
    return True

def rm_s3_object(object_path):
    """Drop all contents from S3 'object_path'."""
    print(TXT_DELETE_OBJECT.format(storage="S3", object=object_path ))
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
    print(TXT_CREATE_OBJECT.format(storage="LOCAL", object=object_path ))
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
    print(TXT_CREATE_OBJECT.format(storage="S3", object=object_path ))
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
        print(TXT_ERR_SCRIPT_UPDATE_CONFIG)
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
        i = input(TXT_INPUT_INSERT_MAPS_PATH.format(mode=mode_name(ISMASTER)))
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
    """Load all maps stored in S3 'path'."""
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

    print( TXT_ERR_MAP_INVALID )
    enter_to_continue()


def is_valid_maps(maps):
    """Return True if maps is valid.
    
    If error print details.
    """

    def check_path_error(path):
        """check common error of 'path'"""
        if path[0] == "~":
            return TXT_ERR_MAP_LINUX_USERHOME
        return None

    if len(maps) == 0:
        print(TXT_ERR_MAP_EMPTY) 
        return False

    for n, e in enumerate(maps):

        name = e.get("name")
        s3_path = e.get("s3")
        master_path = e.get("master")
        slave_path = e.get("slave")

        if name is None:
            print( TXT_ERR_MAP_EMPTY_NAME.format(
                filename=e['filename'],
                number=n )) 
            break

        if s3_path is None:
            print( TXT_ERR_MAP_EMPTY_S3.format(
                filename=e['filename'],
                name=name ))
            break

        if ISMASTER:
            if master_path is None:
                print(TXT_ERR_MAP_EMPTY_MASTER.format(
                    filename=e['filename'],
                    name=name ))
                break

            if check_path_error(master_path):
                break

        else:
            if slave_path is None:
                print(TXT_ERR_MAP_EMPTY_SLAVE.format(
                    filename=e['filename'],
                    name=name ))
                break

            if check_path_error(slave_path):
                break
    else:
        # uscita dal ciclo senza errori
        return True

    return False


def transfer(xmap):
    """Transfer data from master to slave using information path stored in 'xmap'."""
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

    print(TXT_TRANSFER_INFO.format(
        origin_info = ( origin_info['location'], origin_info['name'] ),
        origin_path = origin,
        destination_info = ( destination_info['location'], destination_info['name'] ),
        destination_path = destination ))


    if not CONFIG['MAIN'].getboolean('skip_delete_alert'):
        print( TXT_DELETE_WARNING.format(
                        info = ( destination_info['location'], destination_info['name'] ),
                        path = destination
                    )
              )
        confirm = input(TXT_INPUT_DELETE_CONFIRM).lower()
    else:
        confirm = "y"

    if confirm == "y":
        rm_slave_object(destination)
        # need add '/' to 'mk_slave_object' destination because external path don't have
        mk_slave_object(destination + "/")
        for obj in objects:
            data = None if obj.endswith("/") else get_master_file( "/".join([origin, obj]) )
            mk_slave_object("/".join([destination, obj]), data)

    else:
        print(TXT_NOTDO)



def httpd_restart():
    """Restart HTTPD service """
    cmd = "sudo service httpd restart"
    subprocess.check_call(cmd.split())


def switch_mode():
    """Switch program mode from MASTER and SLAVE and restart."""
    CONFIG['MAIN']['ismaster'] = str(not ISMASTER)
    save_config()
    main()


def input_is_master():
    """Form to ask user the programm mode (MASTER/SLAVE)."""
    # option value for master mast be "1"!
    option = ("1", "0")
    while True:
        clear()
        print( TXT_MENU_MODE.format(
                inp_master=option[0],
                info_master=str_action(True), 
                inp_slave=option[1],
                info_slave=str_action(False)))

        i = input( TXT_INPUT_OPTION.format(option=option))
        if i not in option:
            continue
        else:
            CONFIG['MAIN']['ismaster'] = i
            save_config()
            break
    return bool(int(i))


def show_maps():
    """Show to user loaded maps details."""
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
    """Main user interface."""
    global MAPS

    while True:

        clear()

        print(TXT_MODE_INFO .format(
            mode= mode_name(ISMASTER),
            mapspath=CONFIG[mode_name(ISMASTER)].get("s3_path_mapfiles")))

        print(TXT_MENU_OPTION.format(mode=mode_name(not ISMASTER)))

        print("\n {}:\n".format(str_action()))
        for n, m in enumerate( MAPS ):
            print(" {:>3} = {}".format( n , m['name'] ) )

        print(TXT_REPLACE_ALL_OPTION)

        i = input(TXT_INPUT).lower()

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
                print(TXT_DO)
                print(TXT_RESTART)
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
    """Load configuration and save it in global var CONFIG. 
    
    If configiguration file not exists create it with default values.
    """
    global CONFIG
    if not CONFIG.read(CONFIG_FILENAME):
        CONFIG = default_config()
        save_config()


def default_config():
    """return default configuration."""
    config = {}
    config['MAIN'] = {
        'url_script_update': "https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py",
        'reorder_map_elements': True,
        'skip_delete_alert': False,
        'ismaster': ''
        }
    config[mode_name(True)] = {
        's3_path_mapfiles': ''
        }
    config[mode_name(False)] = {
        's3_path_mapfiles': ''
        }
    return config

def save_config():
    """Save configuration change."""
    with open(CONFIG_FILENAME, 'w') as configfile:
        CONFIG.write(configfile)


def get_maps():
    """Return maps. if not exists ask user for insert maps path."""
    path = CONFIG[mode_name(ISMASTER)].get("s3_path_mapfiles")
    if path:
        maps = load_maps_from_s3path(path)
        if maps:
            return maps

    # if not exists maps, ask for it
    return input_s3path_maps()


def main():
    """Main function"""
    global ISMASTER
    global MAPS

    clear()

    load_config()
    if CONFIG['MAIN'].get('ismaster'):
        ISMASTER = CONFIG['MAIN'].getboolean('ismaster')
    else:
        ISMASTER = input_is_master()
        clear()

    print(TXT_LOADING_MAPS)
    maps = get_maps()
    if maps:
        MAPS = maps
        menu()

    else:
        print(TXT_ERR_CONFIGURATION_FAILS)
        print(TXT_RESTART)


if __name__ == "__main__":
    main()

