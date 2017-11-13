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

config = configparser.ConfigParser()

MASTER = 0
SLAVE = 1
MODE_NAME = ["MASTER","SLAVE"]
FILENAME_CONFIG = 's32s.cf'
# creazione del client S3, utilizzando le credenziali
# salvate in ~/.aws/credentials
S3CLIENT = boto3.client('s3', config = boto3.session.Config(signature_version = 's3v4'))
S3RESOURCE =  boto3.resource('s3', config=boto3.session.Config(signature_version='s3v4'))

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
STR_CONTINUE = "\nDone. Press ENTER to continue... "
MODE = None
MAPS = None

def clear_screen():
    """Pulisce lo schermo"""
    os.system('cls' if os.name=='nt' else 'clear')

def filter_files(data:list):
    """Regole di esclusione
    dalla sincronizzazione file.
    In questo esempio escludo sempre i file della cache di Python
    """
    return [ d for d in data if d.find("__pycache__") == -1 ]


def slipt_s3path(s3path):
    """Return a tuple with bucket name and prefix from a given s3path.
    """
    s3_part = s3path.split("/")
    bucket = s3_part[0]
    prefix = "/".join( s3_part[1:] ) if len(s3_part) > 1 else ""
    return bucket, prefix

def ls_master(path):
    return ls_localpath(path) if MODE == MASTER else ls_s3path(path)

def ls_slave(path):
    return ls_localpath(path) if MODE == SLAVE else ls_s3path(path)

def ls_localpath(path):
    """
    Return generator of objects contained in 'path'.

    Path objects are relative to 'path'
    and directories endswith "/" char.
    """
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
        print(" !! S3 PATH '{}' ERROR: BUCKET NOT FOUND OR ACCESS DENIED.".format(s3path))
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
    f = get_localfile if MODE == MASTER else get_s3file
    return f(path)

def get_slave(path):
    f = get_localfile if MODE == SLAVE else get_s3file
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
    f = rm_s3object if MODE == MASTER else rm_localobject
    return f(path)

# COMMENTATA PER NON SI DOVREBBE MAI USARE QUESTA FUNZIONE
#def rm_master(path):
#    return rm_s3object(path) if MODE == SLAVE else rm_localobject(path)

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
        print( " ERROR" )
        print(e)
        return False
    else:
        print( "OK" )
        return True

#############
# COMMENTATA PER NON SI DOVREBBE MAI USARE QUESTA FUNZIONE
#def mk_master(path, data=None):
#    return mk_localpath(path, data=None) if MODE == MASTER else mk_s3path(path, data=None)

def mk_slave(path, data=None):
    f = mk_localpath if MODE == SLAVE else mk_s3path
    return f(path, data)

def mk_localpath(path, data=None):
    print("LOCAL CREATE: {} ... ".format( path ) , end="")
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
    print( result )
    return result


def mk_s3path(s3object, data=None):
    print("S3 CREATE: {} ... ".format(s3object) , end="")

    bucket, prefix = slipt_s3path(s3object)
    object = S3RESOURCE.Object( bucket, prefix )
    if data:
        request = object.put(Body=data)
    else:
        # crea directory
        request = object.put()
    
    result = request['ResponseMetadata']['HTTPStatusCode'] == 200
    print( result )
    return result

def copy(origin, destination, objects):
    print("\nEXECUTE COPY...\n * FROM ORIGIN '{}'\t\t: {}\n * TO DESTINATION '{}'\t: {}\n".format(
                "LOCAL" if MODE == MASTER else "S3",
                origin,
                "LOCAL" if MODE == SLAVE else "S3",
                destination
            )
          )
    confirm = "y" if config['MAIN'].getboolean('skip_delete_alert') else input("*** ATTENTION ***\nALL FILES STORED in '{}' WILL BE PERMANENTLY DELETE.\n\nType 'y' to confirm: ".format(destination)).lower()
    if confirm == "y":
        rm_slave(destination)
        # ricreo la directory principale (le directory devono terminare con /
        mk_slave(destination + "/")
        for obj in objects:
            data = None if obj[-1] == "/" else get_master( "/".join([origin, obj]) )
            if data is None:
                assert obj[-1] == "/", "If data; object filename can't be endswith /"
            else:
                assert obj[-1] != "/", "If data is None, object must be a directory. Directory ends with /"
            mk_slave("/".join( [destination, obj]), data )

    else:
        print("NOTHING DO")


def update_script():
    script_path = os.path.join( CURRENT_PATH, "s323.py" )
    os.remove(script_path)
    sleep(2)
    urllib.request.urlretrieve(config['MAIN']['url_script_update'], script_path )


def input_s3path_maps(save_configuration=True):
    """Ask user and save in configuration the s3path of mapping files

    Return: 
        - maps list
        - None (on error or user exit)
    """
    while True:
        i = input("Insert S3Path of the folder contains json files for '{}' (x to Exit): ".format(MODE_NAME[MODE]))
        if i.lower() == "x":
            return
        if i[-1] == "/":
            i = i[:-1]
        maps = load_maps_from_s3path(i)
        if maps:
            if save_configuration:
                config[MODE_NAME[MODE]]['s3_path_mapfiles'] = i
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
            maps += xmap
    else:
        # on successuful end for
        if is_valid_maps(maps):
            if config['MAIN'].getboolean('reorder_map_elements'):
                maps = sorted(maps, key=lambda k:k['name'])
            return maps

    print( "*** MAP ERROR ***" )
    input(STR_CONTINUE)


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

        if MODE == SLAVE:
            if slave_path is None:
                print( "MAP ERROR Filename '{}' list element name '{}': empty 'slave' property.".format(e['filename'], name) )
                break

            err = check_path_error(slave_path)
            if err:
                print( "MAP ERROR Filename '{}' list element name '{}': {}.".format(e['filename'], name, err) )
                break

        else:
            if master_path is None:
                print( "MAP ERROR Filename '{}' list element name '{}': empty 'master' property.".format(e['filename'], name) )
                break

            err = check_path_error(master_path)
            if err:
                print( "MAP ERROR Filename '{}' list element name '{}': {}.".format(e['filename'], name, err) )
                break

    else:
        # uscita dal ciclo senza errori
        return True

    return False




def syncronize(xmap):

    # se nella definizione è presente un lista di files
    # sincronizzo solo quelli
    # ATTENZIONE eventuali altri file presenti localmenti nella directory verranno comunque rimossi!
    # Altrimenti sincronizzo tutti i file presenti nel percorso S3 specificato

    if MODE == MASTER:
        origin = 'master'
        destination = 's3'
    else:
        origin = 's3'
        destination = 'slave'

    objects = xmap.get('files')
    if not objects: 
        objects = ls_master(xmap[origin])
    copy(xmap[origin], xmap[destination], objects)


def httpd_restart():
    """Riavvia il servizio HTTPD"""
    cmd = "sudo service httpd restart"
    subprocess.check_call(cmd.split())


def switch_mode():
    config['MAIN']['exe_mode'] = str(abs(MODE-1))
    save_config()
    main()

def select_mode():
    while True:
        clear_screen()
        print( """
SELECT RUN MODE:

    {} = MASTER: AWS S3 files will be replaced with local files
    {} = SLAVE: Local files will be replaced with files stored on AWS S3

""".format( MASTER, SLAVE ))

        option = [MASTER, SLAVE]
        i = input( "Enter input {}: ".format(option))
        try:
            i = int(i)
        except:
            continue
        else:
            if i not in option:
                continue
            else:
                config['MAIN']['exe_mode'] = str(i)
                save_config()
            break
    return i

def show_maps():

    for n, m in enumerate( MAPS ):
        if MODE == SLAVE:
            print("""\
{} - '{}'
    FROM ORIGIN (S3)             : {}
    TO DESTINATION (LOCAL SLAVE) : {}
""".format( m.get('name'), m.get('filename'), m.get('s3'), m.get('slave') ) )

        else:
            print("""\
{} - '{}'
    FROM ORIGIN (LOCAL MASTER) : {}
    TO DESTINATION  (S3)       : {}
""".format( m.get('name'), m.get('filename'), m.get('master'), m.get('s3') ) )
    input(STR_CONTINUE)

def menu():
    global MAPS
    str_action = "REPLACE S3 OBJECT WITH LOCAL ONES" if MODE == MASTER else "REPLACE LOCAL OBJECTS WITH THOSE STORED IN S3"

    while True:

        clear_screen()

        print(" *** MODE: {} | S3 MAPS PATH: {} ***".format(
            MODE_NAME[MODE],
            config[MODE_NAME[MODE]].get("s3_path_mapfiles")
            )
        )

        print("\n OPTIONS:\n")
        print(" ms = Show maps details")
        print(" mr = Reload current maps")
        print(" mc = Change {} maps".format("SLAVE" if MODE == SLAVE else "MASTER"))
        print(" sw = Switch to {} Mode".format("SLAVE" if MODE == MASTER else "MASTER" ))
        if config['MAIN'].get('url_script_update', None):
            print(" us = Update Script")
        print("  x = Exit")

        print("\n {}:\n".format(str_action))
        for n, m in enumerate( MAPS ):
            print(" {:>3} = {}".format( n , m['name'] ) )

        print(" all = REPLACE ALL")


        i = input("\n > Enter input: ").lower()

        clear_screen()

        if i == "x":
            break

        elif i == "sw":
            switch_mode()
            break

        elif i == "mr":
            maps = get_maps()
            if maps:
                MAPS = maps

        elif i == "mc":
            maps = input_s3path_maps()
            if maps:
                MAPS = maps

        elif i == "ms":
            show_maps()


        elif config['MAIN'].get('url_script_update', False) and i == "us":
            update_script()
            print("DONE. Restart script.")
            break

        elif i == "rh":
            httpd_restart()
            input(STR_CONTINUE)

        else:
            if i == "all":
                lista_aggiorna = [ x for x in range(len(MAPS))]
            else:
                try:
                    i = int(i)
                except:
                    # invalid choice
                    continue
                else:
                    if i >= 0 and i < len(MAPS):
                        lista_aggiorna = [ i ]
                    else:
                        # invalid choice
                        continue

            for aggiorna in lista_aggiorna:
                syncronize(MAPS[aggiorna])

            input( STR_CONTINUE )

    print("\nBye\n")


def load_config():
    global config
    if not config.read(FILENAME_CONFIG):
        load_default_config()
        save_config()

def s3_path_mapfiles(mode, s3path):
    config[MODE_NAME[mode]]['s3_path_mapfiles'] = s3path
    save_config()

def load_default_config():
    global config
    config['MAIN'] = {
        'url_script_update': "https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py",
        'reorder_map_elements': False,
        'skip_delete_alert': False,
        'exe_mode': ''
        }
    config[MODE_NAME[MASTER]] = {
        's3_path_mapfiles': ''
        }
    config[MODE_NAME[SLAVE]] = {
        's3_path_mapfiles': ''
        }


def save_config():
    with open(FILENAME_CONFIG, 'w') as configfile:
      config.write(configfile)


def get_maps():
    s3path = config[MODE_NAME[MODE]].get("s3_path_mapfiles")
    if s3path:
        maps = load_maps_from_s3path(s3path)
        if maps:
            return maps

    # se non è presente una mappa valida nel file di configurazione
    return input_s3path_maps()


def main(mode=None):
    global MODE
    global MAPS

    clear_screen()
    load_config()
    try:
        MODE = int( config['MAIN'].get('exe_mode') )
    except:
        MODE = None 

    if MODE is None:
        MODE = select_mode()

    print("Loading maps...")
    maps = get_maps()
    if maps:
        MAPS = maps
        menu()
    else:
        print("COnfiguration fails, restart the script.")

if __name__ == "__main__":
    main()

