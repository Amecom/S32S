# S32Server

S32Server (S3 To Server) è uno script per sincronizzare il contenuto di
uno o più percorsì direcory di un computer su 
un altro computer utilizzando come middleware il servizio AWS S3.

Il programma può essere utilizzato in modalità 'master' o 'slave'.
Il computer 'master' contiene i file originali che vengono copiati su AWS S3
mentre il computer 'slave' copia localmente i file memorizzati su AWS S3.

Percorso files:

	MASTER >> S3 >> SLAVE

Dato che i computer master e slave non cominucano direttamente tra loro
non è necessario che esista uno script master su di un computer affichè
un slave possa funzioanare. Ad esempio io utilizzo questo script solo
im modalità salve sui server che voglio aggiornare mentre utilizzo
un altro applicativo che mi mantiene sincronizzato in tempo reale
i dati tra il mio pc e il percorso su AWS S3.

# Requisiti

Lo script è stato testato con Python3.6

È necessario disporre di credenziali di di accesso allo storage AWS S3
e configurare il computer per l'utilizzo della libreria BOTO3
tramite la creazione del file:

~/.aws/credentials

Il cui contenuto è simile questo:

```
[default]
aws_access_key_id = MY_ACCESS_KEY
aws_secret_access_key = MY_SECRET_KEY
```

Per maggiori informazioni a riguardo consultare la guida a BOTO3 offerta da AWS


# Installazione dello script

Per installare sul server lo script 
è sufficiente scaricare il file:

```
$ wget https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py
```

NOTA: lo script quando viene eseguito crea altri file e directory per cui potrebbe essere comodo salvarlo all'interno di una directory dedicata.

Nello specifico verranno creati:
1) una directory `s32s_data` che conterra i file di mappatura dei percorsi
2) un file `s32s.slave` o un file `s32s.master` a seconda del tipo di configurazione scelta.

(Nota: il fatto che il percorso del file contenga la parola master è una coincidenza che nulla
ha a che vedere con il concetto di 'master' e 'slave' discusso fino ad ora)



# Creazione del file di mappatura

Perchè lo script funzioni è necessario creare uno, o più file,
contenenti le informazioni di sincronizzazione. 
Le informazioni mappano i percorsi tra master > s3 > slave
che possono esseri diversi.

Esempio file 'syncro.json':
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
	  "files": ["filename_1", "filename_2"]
    }
]
```

In questo esempio ho creato una mappa chiamta "syncro.json" che contiene due percorsi chiamati 
'PROJECT 1' e 'PROJECT 2'.

Il computer master è OS Windows, mentre il computer slave è Linux.

La proprietà 'master' è necessaria solo se lo script viene eseguito in modalità master
e contiene il percorso della directory di origine dei file della macchina master.
Se non viene utilizzato lo script in modalità master è possibile omettere questa proprietà.

La proprietà 's3' contiene il percorso su AWS S3 e deve essere sempre presente. 
In questo percorso vengono caricati i file dal computer master e prelevati dal computer slave. 

La proprietà 'slave' è necessaria solo se lo script viene eseguito in modalità slave
e contiene il percorso locale dove verranno copiati i file.
Se non viene utilizzato lo script in modalità slave è possibile omettere questa proprietà.

In 'PROJECT 2' tramite la proprietà 'files'
sono specificati i file che si vuole copiare, mentre in 'PROJECT 1'
verranno sincronizzati tutti i file presenti nel percorso master su S3 e tutti i file presenti nel percorso S3 su slave.

ATTENZIONE: se la directory specificata in 'slave' non esiste verrà creata, mentre se esiste cancellata
e ricreata quindi i vecchi file verranno cancellati.
In 'PROJECT 2' ad esempio dopo la sinctronizzazione la directory "/path/server/dir2" conterrà solo
i file "filename_1", "filename_2" come specificato in 'files';
eventuali file presenti in precedenza nella directory verranno cancellati.


# Salvataggio dei file mappatura

Il file creato nel paragrafo precedente dovrà essere salvato in una directory su AWS S3
per essere accessibile sia dal computer master che slave.
Creo bucket e una cartella nella quale inserisco il file.

Quindi nel percorso:

`bucketname/S32SMAP/foo/data`

carico il file 'syncro.json'.

È possibile inserire più mappe all'interno della directory.


# Esecuzione dello script

La prima volta che lo script viene eseguito verrà chiesto:

1) Come configurare il computer: master o slave.

2) Di inserire il percorso S3 dove sono
state salvate le definizioni di sincronizzazione per seguire l'esempio
come riportato fino ad ora dovrò inserire: 

`bucketname/S32SMAP/nomeserver/data`


Se tutti i passaggi sono stati eseguiti correttamente (credenziali BOTO3 corrette, presenza delle definizioni, etc)
lo script mi fornisce l'interfaccia pr eseguire la sincronizzazione dei dati.


# Aggiornare i file di mappatura

È possibile che nel tempo si effettuino delle modifiche nei percorsi di mappatura 
tuttavia le mappe vengono copiate localmente e nel caso si modifichi il file 'syncro.json' su AWS S3
è necessario aggiornare esplicitamente la copia locale.
Questa operazione è fornita dall'interfaccia dello script.


# File 'config.json'














