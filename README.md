# S32S


S32S semplifica i trasferimenti di dati 
tra computer attraverso AWS S3 come middleware e percorsi mappati.

Il programma può essere utilizzato in modalità 'master' o 'slave'.
Il computer 'master' copia i file locali su AWS S3
mentre il computer 'slave' utilizza AWS S3 per recuperare/aggiornare i file.

Flusso degli oggetti:

	MASTER >> S3 >> SLAVE

Dato che i computer MASTER e SLAVE non cominucano direttamente tra loro
è possibile utilizzare lo script solo in modalità MASTER per effeture una copia dei dati
o solo in modalità SLAVE per caricare o aggiornare i dati di un server.

# ATTENZIONE
L'autore non è responsabile di eventuali perdite di dati causati
dall'uso, dalla modifica o da errori del programma.

Il programma include routine che eliminano intere directory dal computer su cui viene eseguito
e su bucket AWS S3 di cui si fornisce l'accesso. 

Si prega di:

1) Tenere presente che il programma è una BETA e potrebbe contenere dei bug.
2) Prestare molta attenzione ai messaggi di alert che il programma fornisce.
3) Avere ben chiaro cosa si sta facendo e quali sono le conseguenze.

Si consiglia di eseguire delle copie di backup dei dati su cui si lavora. 

# Requisiti

Il programma è stato testato con Python 3.6.

È necessario disporre di credenziali di accesso allo storage AWS S3
e configurare il computer per l'utilizzo della libreria BOTO3
tramite la creazione del file:

~/.aws/credentials

Il cui contenuto è simile questo:

```
[default]
aws_access_key_id = MY_ACCESS_KEY
aws_secret_access_key = MY_SECRET_KEY
```

Per maggiori informazioni a riguardo consultare la guida a BOTO3 offerta da AWS.

# Nota sui percosi AWS S3

In AWS S3 solitamente ci si riferisce 
a un oggetto o un percorso specificando separatamente
il nome del 'bucket' e un 'prefix' o 'key'.

Per semplificare in questo programma, nei file di configurazione, e nella documentazione
quando ci si riferisce a un percorso su AWS S3 si intende 
un stringa unica composta da NOMEBUCKET/PREFIX. 

# Installazione dello script

Per installare sul server lo script è sufficiente scaricare il file:

```
$ wget https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py
```

Al primo avvio lo script crea un file di configurazione chiamato 's32s.cf'.

Nota: il fatto che il percorso del file contenga la parola master è una coincidenza che nulla
ha a che vedere con il concetto di 'master' e 'slave' discusso fino ad ora. :)

# Creazione dei percorsi di mappatura

Perchè lo script possa essere utilizzato è necessario creare uno, o più file,
contenenti le informazioni di mappatura dei percorsi e dare a queste 'mappature'
un nome. Un file di mappatura è un file JSON che contiene una lista di mappature.

Ogni mappatura è un dizionario con i percorsi di mappatura.

I PERCORSI DI MAPPATURA SONO DIRECTORY NON DEI FILE.

Una mappatura contiene una percorso 'master' ovvero la directory che contiene
i file originali, un percorso 's3' ovvero dove il bucket/prefix dove verranno 
trasferiti i file e un percorso 'slave' ovvero la directory in cui i file 
verranno copiati recuperandoli dal percorso S3.

In dizionario di mappatura:
la proprietà 'name' è obbligatoria. 
la proprietà 'description' è facoltativa. 
la proprietà 's3' è obbligatoria. 
la proprietà 'master' è necessaria solo quando lo script viene eseguito in modalità master.
la proprietà 'slave' è necessaria solo quando lo script viene eseguito in modalità slave.
la proprietà 'object' è facoltativa.


Dovrebbe essere evidente che il percorso su AWS S3 è condiviso sia dal computer master che slave
mentre i percorsi locali possono cambiare.


Esempio file 'mainmap.json':
```
[
    {
      "name": "PROJECT 1",
      "description": "OPTIONAL PROJECT DESCRIPTION",
      "master": "c:/path/dir/master/1",
      "s3": "bucketname/backup/dir1",
      "slave": "/path/slave/dir1"
    },
    {
      "name": "PROJECT 2",
      "description": "OPTIONAL PROJECT DESCRIPTION",
      "master": "c:/path/dir/master/2",
      "s3": "bucketname/dir/dir/dir",
      "slave": "/path/slave/dir2",
	  "objects": ["filename_1", "filename_2"]
    }
]
```

In questo esempio ho creato un file chiamato "mainmap.json" che contiene due mappature chiamate
'PROJECT 1' e 'PROJECT 2'.

In 'PROJECT 2' tramite la proprietà 'objects'
sono specificati i file che si vuole copiare, mentre in 'PROJECT 1'
verranno sincronizzati tutti i file e le directory presenti nel percorso master su S3
e tutti i file presenti nel percorso S3 su slave.

ATTENZIONE: 
Durante la copia dei dati da un repository a un altro
se la directory di destinazione esiste verrà cancellata
e ricreata quindi i vecchi file verranno cancellati.

# Utilizzo dei percorsi di mappatura

I file di mappatura devono essere condivisi tra computer master e slave per questo motivo
dovranno essere salvati in un percorso AWS S3.

Quindi creo un percorso in:

`bucketname/s32s/foo/maps`

sul quale carico il file 'mainmap.json'.

Quando il programma mi chiede di inserire il percorso dei file di mappatura
devo inserire il percorso della directory ovvero `bucketname/s32s/foo/maps`
e non il percorso del file `bucketname/s32s/foo/maps/mainmap.json`

È possibile inserire più file di mappature in un percorso S3.



# Esecuzione dello script

La prima volta che lo script viene eseguito verrà chiesto di:

1) configurare il computer come master o slave.
2) inserire il percorso S3 dei files di mappatura

In caso di errore verificare che sia abbia accesso a AWS S3 tramite BOTO3
e di avere le autorizzazioni di accesso sulle directory locali su cui si vuole lavorare.


# Esecuzione contemporanea della modalità MASTER e SLAVE

Il programma può essere utilizzato in uno stesso computer sia in modalità
MASTER che SLAVE. In questo caso è possibile specificare due differenti percorsi S3
dei file di mappatura uno per la modalità MASTER e uno per la modalità SLAVE.

Utilizzare una stessa mappatura nelle due modalità
non solo non avrebbe senso e sarebbe sbagliato
ma anche potenzialmente pericoloso per i proprio dati.


# File 's32s.cf'
















