#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import boto3
import shutil
import json
import subprocess
import urllib.request
from time import sleep

MASTER = 0
SLAVE = 1

# CONFIGURAZIONE
# ############################################
# NON MODIFICARE IL FILE DI CONFIGURAZIONE QUI.
# Creare un file config.json con la propria configurazione
# I valori che seguono sono le proprietà di default
# ############################################
START_CONFIG = {
    # Url di aggiornamento script
    "S3PScript" : "https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py",

    # Percorsi delle directory S3 nelle quali sono memorizzate le
    # definizioni di sincronizzazione e che è possibile caricare 
    "S3PDef" : None,

    # Specifica se riordinare alfabeticamente i percorsi
    "ReorderPath": True,

    # Includere il comando service HTTPD restart
    "AddRH" : False,

    # Se True non viene mostarto l'avviso di cancellazione dei file locali
    "SkipDeleteAlert": False
}

# creazione del client S3, utilizzando le credenziali
# salvate in ~/.aws/credentials
S3CLIENT = boto3.client('s3', config = boto3.session.Config(signature_version = 's3v4'))
S3RESOURCE =  boto3.resource('s3', config=boto3.session.Config(signature_version='s3v4'))

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
MAPS_PATH = os.path.join( CURRENT_PATH, "s32s_maps")
STR_CONTINUE = "\nDone. Press ENTER to continue... "
CONFIG = None

def clear_screen():
    """Pulisce lo schermo"""
    os.system('cls' if os.name=='nt' else 'clear')

def filter_files(data:list):
    """Regole di esclusione
    dalla sincronizzazione file.
    In questo esempio escludo sempre i file della cache di Python
    """
    return [ d for d in data if d.find("__pycache__") == -1 ]

def build_dir(path, chiedi=False):
    # Non deve eliminare niente, ma creare solo le directory 
    # che eventualmente mancano per 'path'
    tree = path.split("/")
    p = []
    for a in tree:
        p.append(a)
        # controllo che il primo percorso non sia vuoto (in linux succede)
        if len(a) > 0:
            dir = "/".join(p)
            if not os.path.isdir( dir ):
                if chiedi:
                    z = input("Create '{}' y/n? ".format(dir) ).lower()
                else:
                    z = "y"

                if z != "y":
                    raise "impossibile continuare senza creare la directory"
                print("MKDIR: {}".format( dir ) )
                os.mkdir( dir )

def split_bucket_prefix(path):
    s3_part = path.split("/")
    bucket = s3_part[0]
    prefix = "/".join( s3_part[1:] )
    return bucket, prefix


def s3_ls(path):
    """
    Restituisce la lista dei percorsi relativi
    dei file presenti nel path S3 specificato.
    """
    bucket, prefix = split_bucket_prefix(path)
    objects = S3CLIENT.list_objects_v2( Bucket=bucket, Prefix=prefix)
    files = []
    for object in objects["Contents"]:
        k = object["Key"]
        # escludo le directory
        if k[-1] != "/":
            # rendo il percorso relativo al prefix
            #  (+1 per rimuovere la '/' )
            files.append( object["Key"][len(prefix)+1:] )
    return files

def s3_del(path):
    print("S3 DEL: {} ... ".format(path), end="")

    bucket, prefix = split_bucket_prefix(path)
    b = S3RESOURCE.Bucket(bucket)
    try:
        request = b.objects.filter(Prefix=prefix).delete()
    except Exception as e:
        print( "ERROR" )
        print(e)
        return False
    else:
        print( "OK" )
        return True

def s3_create(path, data=None):
    bucket, prefix = split_bucket_prefix(path)

    print("S3 CREATE: {} ... ".format( prefix ) , end="")
    object = S3RESOURCE.Object( bucket, prefix )


    if data is None:
        # crea directory
        assert path[-1] == "/", "If data is None, path must be a directory. Directory end with /"
        request = object.put()
    else:
        request = object.put(Body=data)
    
    result = request['ResponseMetadata']['HTTPStatusCode'] == 200
    print( result )
    return result


def s3_to_local(s3path, local_path, listobjects):

    bucket, prefix = split_bucket_prefix(s3path)

    print("\nEXECUTE COPY...\n * From S3\t\t: {}\n * To Local Path\t: {}\n".format(
                s3path,
                local_path
            )
          )

    confirm = "y" if CONFIG["SkipDeleteAlert"] else input("*** ATTENTION ***\nALL FILES in '{}' WILL BE PERMANENTLY DELETE.\n\nType 'y' end press ENTER to confirm: ".format(local_path)).lower()

    if confirm == "y":
        # elimino il vecchio contenuto
        if os.path.isdir(local_path):
            print("DEL: {}".format( local_path ))
            shutil.rmtree(local_path)
            # e' utile fare una pausa prima di ricreare una directory appena eliminata
            # per permettere al sistema di rilasciare i files
            sleep(3)

        build_dir(local_path)

        for file in listobjects:
            file_local_path = os.path.join( local_path, file )
            # COSTRUISCO DIRECTORY LOCALE
            file_tree = file_local_path.split("/")
            # in linux il primo percosro è lungezza 0
            # quindi evito con un controllo sulla lunghezza
            if len(file_tree) > 1:
                p = "/".join( file_tree[0:-1] )
                build_dir(p)
            # DOWNLOAD
            try:
                print("COPY: {}".format( file_local_path ) )
                S3CLIENT.download_file( bucket, prefix + "/" + file, file_local_path )
            except Exception as e:
                print(e)
                break
    else:
        print("NOTHING DO")

def master_to_s3(s3path, local_path, listobject):
    bucket, prefix = split_bucket_prefix(s3path)

    print("\nEXECUTE COPY...\n * From Local Path\t: {}\n * To S3\t\t: {}\n".format(
                local_path,
                s3path
            )
          )

    confirm = "y" if CONFIG["SkipDeleteAlert"] else input("*** ATTENTION ***\nALL FILES in AWS S3 '{}' WILL BE PERMANENTLY DELETE.\n\nType 'y' end press ENTER to confirm: ".format(s3path)).lower()
    if confirm == "y":

        if s3_del(s3path):
            if s3_create(s3path + "/"):
                for f in listobject:
                    data = None
                    print(f , "is", end= " ")
                    if f[-1] != "/":
                        print( "FILE")
                        with open( os.path.join( local_path, f), "rb" ) as bin:
                            data = bin.read()
                    else:
                        print( "DIR")
                    s3_create("/".join( [bucket, prefix, f]), data )

    else:
        print("NOTHING DO")

    pass


def update_script():
    script_path = os.path.join( CURRENT_PATH, "s323.py" )
    os.remove(script_path)
    sleep(2)
    urllib.request.urlretrieve(CONFIG['S3PScript'], script_path )

def update_maps():
    while True:

        if CONFIG['S3PDef']:
            print( "\nUPDATE MAPS\n")
            for n, percorso in enumerate( CONFIG['S3PDef']):
                print( " {} = {}".format(n, percorso['name']) )
            print("")
            print("."*50)
            print("")
            print( " m = Insert manual S3 Path")
            print( " x = Exit")

            s = input( "\nSelect: ").lower()

            if s == "x":
                return
        else:
            s = "m"


        if s == "m":
            s3input = input("Insert S3 Path folder with json maps files (x to Exit): ")
            if s3input.lower() == "x":
                return

        else:
            try:
                s = int(s)
            except:
                continue
            else:

                if s >= 0 and s < len( CONFIG['S3PDef'] ):
                    s3input = CONFIG['S3PDef'][s]['s3']
                else:
                    continue

        files = filter_files( s3_ls(s3input) )
        s3_to_local(s3input, MAPS_PATH, files)
        return

def load_configuration():
    p = os.path.join( CURRENT_PATH, "config.json")
    if os.path.exists(p):
        with open( p, "r") as f:
            data = json.load(f)
    else:
        data = {}

    for k , v in START_CONFIG.items():
        if not data.get(k):
            data[k] = v
    return data


def load_maps():
    json_data = []
    for file in os.listdir(MAPS_PATH):
        if file.endswith(".json"):
            with open( os.path.join(MAPS_PATH, file), "r") as f:
                jsd = json.load(f)
                if CONFIG['ReorderPath']:
                    jsd = sorted(jsd, key=lambda k:k['name'])

                for data in jsd:
                    data['filename'] = file[:-5]
                    json_data.append(data)
    return json_data


def syncronize(data, mode):

    files = data.get('files')

    if mode == SLAVE:
        # se nella definizione è presente un lista di files
        # sincronizzo solo quelli
        # ATTENZIONE eventuali altri file presenti localmenti nella directory verranno comunque rimossi!
        # Altrimenti sincronizzo tutti i file presenti nel percorso S3 specificato
        if not files:
            files = filter_files( s3_ls(data['s3']) )
        s3_to_local(data['s3'], data['slave'], files)

    elif mode == MASTER:
        local_path = data['master'].replace("\\","/")
        if not files:
            print("WALK", data['master'])
            files = []
            for root, dirs, xfiles in os.walk(local_path):
                for name in xfiles:
                    files.append(os.path.join( root, name ) )
                for name in dirs:
                    files.append(os.path.join( root, name ) + "/" ) 
            
            # NORMALIZZO I PERCORSI E LI RENDO RELATIVI
            files = [ 
                (f.replace("\\","/")).replace(local_path, "")[1:]
                for f in files ]

        master_to_s3(data['s3'], data['master'], files )




def httpd_restart():
    """Riavvia il servizio HTTPD"""
    cmd = "sudo service httpd restart"
    subprocess.check_call(cmd.split())


def select_pc_type():
    while True:
        clear_screen()
        print( """
FIRST CONFIGURATION

This computer is:

    master = AWS S3 files wil be replaced with local files
    slave  = Local files will be replaced with files stored on AWS S3

""")

        i = input( "Input (master/slave): ").lower()
        if i not in ["slave" ,"master"]:
            continue
        else:
            p = os.path.join(CURRENT_PATH, "s323."+i ) 
            with open( p, "w") as f:
                print( "\n\nFile '{}' is been created!\n\nDelete this file to change configuration.\n".format(p) )
            input( STR_CONTINUE )
            return


def menu(mode):

    if mode == MASTER:
        str_action = "UPLOAD"
    else:
        str_action = "DOWNLOAD"

    while True:

        clear_screen()

        maps = load_maps()

        if maps:
            print("\n{}\n".format(str_action))
            for n, m in enumerate( maps ):
                print(" {:>3} = {}".format( n , m['name'] ) )

            print("")
            print(" all = {} ALL".format(str_action))
            print("")
            print("."*50)
            print("")
            print(" upm = Update Map")

            if CONFIG['S3PScript']:
                print(" ups = Update Script")

            if CONFIG['AddRH']:
                print("")
                print("  rh = $ service HTTPD restart")

            print("")
            print("   x = Exit")

            modulo = input("\nSelect: ").lower()

        else:
            modulo = "upm"


        clear_screen()

        if modulo == "upm":
            update_maps()


        elif CONFIG['S3PScript'] and modulo == "ups":
            update_script()
            print("DONE. Restart script.")
            break

        elif modulo == "x":
            break

        elif CONFIG['AddRH'] and  modulo == "rh":
            httpd_restart()
            input( STR_CONTINUE)

        else:
            if modulo == "all":
                lista_aggiorna = [ x for x in range(1,len(maps))]
            else:
                try:
                    modulo = int(modulo)
                except:
                    # invalid choice
                    continue
                else:
                    if modulo >= 0 and modulo < len(maps):
                        lista_aggiorna = [ modulo ]
                    else:
                        # invalid choice
                        continue

            for aggiorna in lista_aggiorna:
                syncronize(maps[aggiorna], mode)

            input( STR_CONTINUE )

    print("\nBye\n")

############

def start():
    global CONFIG
    build_dir(MAPS_PATH)
    CONFIG = load_configuration()

    clear_screen()
    if os.path.isfile( os.path.join( CURRENT_PATH, "s323.slave" ) ):
        menu(SLAVE)

    elif os.path.isfile( os.path.join( CURRENT_PATH, "s323.master" ) ):
        menu(MASTER)

    else:
        select_pc_type()
        start()


def test_upload():
    b =  boto3.resource('s3', config=boto3.session.Config(signature_version='s3v4'))

    bucket, prefix = split_bucket_prefix( "test.amecom.it/S23SROOT/xdir/" )

    print(bucket, prefix) 
    object = b.Object( bucket, prefix )
#    if object.load():

    with open("C:/diskstation/s3replica/AWS/S32S_DATA/TEST/root/f1.txt", "rb") as data:
        request = object.put(
                Body=data
            )
        return request['ResponseMetadata']['HTTPStatusCode'] == 200



if __name__ == "__main__":
    ### MAPPA >> amedeo.amecom.it/AWS/S32S_DATA/TEST/map

    start()

