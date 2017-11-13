# S32S


S32S è uno script per gestire il trasferimento di dati
tra computer che utilizza AWS S3 come middleware e permette differenti 
mappature dei percosri.

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
contenenti le informazioni di mappatura dei percorsi e dare a queste 'mappe'
un nome.

I percorsi di mappatura sono delle directory non dei file.

Una mappa contiene una percorso 'master' ovvero la directory che contiene
i file originali, un percorso 's3' ovvero dove il bucket/prefix dove verranno 
trasferiti i file e un percorso 'slave' ovvero la directory in cui i file 
verranno copiati recuperandoli dal percorso S3.

Dovrebbe essere evidente che il percorso su AWS S3 è condiviso sia dal computer master che slave
mentre i percorsi locali possono cambiare.


Esempio file 'mappatura.json':
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

In questo esempio ho creato una mappa chiamta "mappatura.json" che contiene due percorsi chiamati 
'PROJECT 1' e 'PROJECT 2'.

Il computer master è Windows, mentre il computer slave è Linux.

Mentre la proprietà 'master' è necessaria solo quando lo script viene eseguito in modalità master
e la proprietà 'slave' è necessaria solo quando lo script viene eseguito in modalità slave,
la proprietà 's3' deve essere sempre presente. 

In 'PROJECT 2' tramite la proprietà 'objects'
sono specificati i file o directory (vuote) che si vuole copiare, mentre in 'PROJECT 1'
verranno sincronizzati tutti i file e le directory presenti nel percorso master su S3
e tutti i file presenti nel percorso S3 su slave.

ATTENZIONE: SE LA DIRECTORY SPECIFICATA IN 'SLAVE' ESISTE VERRÀ CANCELLATA
E RICREATA QUINDI I VECCHI FILE VERRANNO CANCELLATI.


# Salvataggio dei file mappatura

I file di mappatura devono essere condivisi tra computer master e slave per questo motivo
dovranno essere salvati in un percorso su AWS S3.

Quindi creo un percorso su AWS S3:

`bucketname/S32SMAP/foo/data`

carico il file 'mappatura.json'.

Il percorso di mappatura NON è il singolo file ma il percorso quindi
quando lo script mi chiederà di inserire il percorso dei file di mappatura
si dovrà inserire `bucketname/S32SMAP/foo/data` e non `bucketname/S32SMAP/foo/data/mappatura.json`

Da questo si può dedurre che in `bucketname/S32SMAP/foo/data` è possibile inserire
più file di mappature.


# Esecuzione dello script

La prima volta che lo script viene eseguito verrà chiesto:

1) Come configurare il computer: master o slave.

2) Di inserire il percorso S3 dove sono
state salvate le definizioni di sincronizzazione per seguire l'esempio
come riportato fino ad ora dovrò inserire: 

`bucketname/S32SMAP/nomeserver/data`

Se tutti i passaggi sono stati eseguiti correttamente (credenziali BOTO3 corrette, presenza delle definizioni, etc)
lo script mi fornisce l'interfaccia per eseguire la sincronizzazione dei dati.


# Esecuzione contemporanea della modalità MASTER e SLAVE

Il programma può essere utilizzato in uno stesso computer sia in modalità
MASTER che SLAVE. In questo caso si dovranno inserire due differenti percorsi con i file di mappatura
uno per la modalità MASTER e uno per la modalità SLAVE dato che utilizzare una stessa
mappatura nelle due modalità non solo non avrebbe senso e sarebbe sbagliato
ma anche potenzialmente pericoloso per i proprio dati.


# File 's32s.cf'
















