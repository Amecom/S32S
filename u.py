# -*- coding: utf-8 -*-

import os
import boto3
import shutil
import json
import subprocess
from time import sleep

# CONFIGURAZIONE
# ############################################
# NON MODIFICARE IL FILE DI CONFIGURAZIONE QUI.
# Creare un file config.json con la propria configurazione
# I valori che seguono sono le proprietà di default
# ############################################
START_CONFIG = {
    # Url di aggiornamento script
    "S3PScript" : "https://raw.githubusercontent.com/Amecom/S32S/master/u.py",

    # Percorsi delle directory S3 nelle quali sono memorizzate le
    # definizioni di sincronizzazione e che è possibile caricare 
    "S3PDefaultDefinitions" : None,

    # Specifica se riordinare alfabeticamente i percorsi
    "ReorderPath": True,

    # Includere il comando service HTTPD restart
    "AddRH" : False
}

# creazione del client S3, utilizzando le credenziali
# salvate in ~/.aws/credentials
S3CLIENT = boto3.client('s3', config = boto3.session.Config( signature_version = 's3v4' ))

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join( CURRENT_PATH, "DATA")
STR_CONTINUE = "\nFatto. ENTER per continuare... "

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
                    z = input("Creare '{}' s/n? ".format(dir) )
                else:
                    z = "s"

                if z != "s":
                    raise "impossibile continuare senza creare la directory"
                print("CREO: {}".format( dir ) )
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

def s3_copy_local(s3path, local_path, files):

    bucket, prefix = split_bucket_prefix(s3path)

    print("\nAGGIORNAMENTO IN CORSO\n * Origine S3\t\t: {}\n * Destinazione\t\t: {}\n".format(
                s3path,
                local_path
            )
          )

    # elimino il vecchio contenuto
    if os.path.isdir(local_path):
        print("ELIMINO: {}".format( local_path ))
        shutil.rmtree(local_path)
        # e' utile fare una pausa prima di ricreare una directory appena eliminata
        # per permettere al sistema di rilasciare i files
        sleep(3)

    build_dir(local_path)

    for file in files:
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
            print("COPIO: {}".format( file_local_path ) )
            S3CLIENT.download_file( bucket, prefix + "/" + file, file_local_path )
        except Exception as e:
            print(e)
            break


def update_script():
    bucket, prefix = split_bucket_prefix( CONFIG['S3PScript'] )
    S3CLIENT.download_file( bucket, prefix, CURRENT_PATH + "/u.py" )

def update_definitions():

    print( "\nAGGIRNAMENTO DEFINIZIONI\n")
    if CONFIG['S3PDefaultDefinitions']:
        for n, percorso in enumerate( CONFIG['S3PDefaultDefinitions']):
            print( " {} = {}".format(n, percorso['name']) )
        print("")
        print("."*50)
        print("")

    print( " m = Inserisci URL Manuale")
    print( " x = Annulla")

    s = input( "\nSeleziona: ")
    if s == "x":
        return

    elif s == "m":
        s3input = input("Inserisci PERCORSO S3 (bucket/prefix) che contiene le definizioni: ")
    else:
        s3input = CONFIG['S3PDefaultDefinitions'][int(s)]['url']

    files = filter_files( s3_ls(s3input) )
    s3_copy_local(s3input, DATA_PATH, files)

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


def load_definitions():
    json_data = []
    for file in os.listdir(DATA_PATH):
        if file.endswith(".json"):
            with open( os.path.join(DATA_PATH, file), "r") as f:
                jsd = json.load(f)
                print(jsd)
                if CONFIG['ReorderPath']:
                    jsd = sorted(jsd, key=lambda k:k['name'])

                for data in jsd:
                    data['filename'] = file[:-5]
                    json_data.append(data)
    return json_data


def syncronize(data):
    # se nella definizione è presente un lista di files
    # sincronizzo solo quelli
    # ATTENZIONE eventuali altri file presenti localmenti nella directory verranno comunque rimossi!
    files = data.get('files')
    # Altrimenti sincronizzo tutti i file presenti nel percorso S3 specificato
    if not files:
        files = filter_files( s3_ls(data['s3']) )

    s3_copy_local(data['s3'], data['local'], files)


def httpd_restart():
    """Riavvia il servizio HTTPD"""
    cmd = "sudo service httpd restart"
    subprocess.check_call(cmd.split())


############

if not os.path.isfile(CURRENT_PATH + "/u.slave"):
    raise "Per eseguire la sincronizzazione creare in questa directory un file nominato 'u.slave"

build_dir(DATA_PATH)

CONFIG = load_configuration()

while True:

    clear_screen()

    json_data = load_definitions()

    if json_data:
        print( "\nPERCORSI:\n" )
        for n, data in enumerate( json_data ):
            print(" {:>3} = {}".format( n , data['name'] ) )

        print("")
        print("."*50)
        print("")
        print("   a = Aggiorna tutti i percorsi")

        print("   d = Aggiorna definizioni percorsi")

        if CONFIG['S3PScript']:
            print("   u = Aggiorna script update")

        if CONFIG['AddRH']:
            print("")
            print("  rh = $ service HTTPD restart")

        print("")
        print("   x = Esci")

        modulo = input("\nSeleziona: ")

    else:
        print( "\n*** Nessuna definizione presente ***\n")
        modulo = "d"


    clear_screen()

    if modulo == "d":
        update_definitions()

    elif CONFIG['AddRH'] and  modulo == "rh":
        httpd_restart()
        input( STR_CONTINUE)

    elif CONFIG['S3PScript'] and modulo == "u":
        update_script()
        print("FATTO. Riavviare lo script.")
        break

    elif modulo == "x":
        break

    else:
        if modulo == "a":
            lista_aggiorna = [ x for x in range(1,len(json_data))]
        else:
            lista_aggiorna = [ int(modulo)]

        for aggiorna in lista_aggiorna:
            syncronize(json_data[aggiorna])
        input( STR_CONTINUE )
print("\nBye\n")


