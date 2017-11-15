# S32S

S32S gestisce il trasferimento di dati tra computer utilizzando AWS S3
come middleware e una mappatura di percorsi.

Il computer 'master' copia i file locali su AWS S3
mentre il computer 'slave' utilizza AWS S3 per recuperare o aggiornare i file.

Flusso degli oggetti:

	MASTER >> S3 >> SLAVE

Dato che i computer MASTER e SLAVE non cominucano direttamente tra loro
è possibile utilizzare lo script solo in modalità MASTER per effeture una copia dei dati
o solo in modalità SLAVE per caricare o aggiornare i dati di un server.


# ATTENZIONE
Il programma include routine che eliminano intere directory da un computer SLAVE
e dal bucket AWS S3 di cui si fornisce l'accesso. 
L'autore non è responsabile di eventuali perdite di dati causati
dall'uso, dalla modifica o da errori del programma.

Si consiglia:
1) Eseguire sempre delle copie di backup dei dati importanti. 
2) Prestare molta attenzione ai messaggi di alert che il programma fornisce.
3) Avere chiaro cosa si sta facendo e quali sono le conseguenze.

# Requisiti

Il programma è stato testato con Python 3.6.

Affinche il programma funzioni
è necessario fornire alla libreria BOTO3 inclusa nel codice 
le credenziali di accesso allo storage AWS S3 che si sta utilizzando 
come middleware

Occorre quindi creare su Unix un file:

~/.aws/credentials


Il cui contenuto è simile questo:

```
[default]
aws_access_key_id = MY_ACCESS_KEY
aws_secret_access_key = MY_SECRET_KEY
```

Per maggiori informazioni, compresa la configurazione su altri SO,
consultare le guide su BOTO3 disponibili online.

# Nota sui percosi AWS S3

Nelle librerie che utilizzano AWS S3 solitamente ci si riferisce 
a un oggetto specificando separatamente
il nome del 'bucket' e un 'prefix'.

In questo programma nei file di configurazione e negli input utente
quando ci si riferisce a un percorso S3 si intende 
una stringa unica composta dal nome del bucket e dal prefix
uniti dal carattere '/' ovvero NOMEBUCKET/PREFIX. 

# File di mappatura

Il programma richiede almeno un file con estensione .json 
per mappare i percorsi tra master, s3, e slave.

Un file di mappatura è un file in formato JSON che contiene una lista di oggetti/dizionari.
Ciascun oggetto descrive un percorso di mappatura indipendente ed è formato dalle seguenti proprietà
| Property | Mandatory | Description
| --- | --- | --- |
| `name` | YES | Map name |
| `description` | NO  | Map description |
| `s3` | YES | Indica il percorso S3 dove verranno salvati o recuperati i file. |
| `master` | IF MASTER | Directory che contiene i file originali che verranno caricati sul percorso S3. |
| `slave` | IF SLAVE | Directory in cui i file verranno copiati recuperandoli dal percorso S3. |
| `ignore` | NO | Regole di esclusione dei percorsi. |

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
	  "files": ["filename_1", "filename_2"]
    }
]
```

In questo esempio il file chiamato "mainmap.json" contiene due mappature chiamate
'PROJECT 1' e 'PROJECT 2'.

'PROJECT 1' sincronizza tutti i file e le directory presenti nel percorso MASTER
sul percorso S3 e dal percorso S3 su SLAVE.

'PROJECT 2' tramite la proprietà 'files'
specifica i file che si vuole copiare.

IMPORTANTE:

1) Quando viene specificato solo il percorso della directory allora
la directory di destinazione se non esiste verrà creata ma se esiste verrà cancellata e ricreata
perdendo quindi tutti i file precedentemente contenuti.

2) Quando viene specificata una lista di files allora la directory di destinazione deve esistere,
non verrà creata, e gli altri file contenuti nella directory verranno conservati.

# Direttiva ignore
Ogni oggetto mappatura può contentere la proprietà ignore.
Se espressa questa proprietà deve essere una lista.

È possbile utilizzare i caratteri jolly in questo modo

| String | Description |
| --- | --- |
| `string*` | esclude i percorsi che iniziano con 'string |
| `*string*`| esclude i percorsi che contengono 'string |
| `*string` | esclude i percorsi che finiscono con 'string |

Esempio:

```
{
    "name": "python script",
    "description": "OPTIONAL PROJECT DESCRIPTION",
    "master": "c:/spam/foo",
    "s3": "bucketname/foo/spam",
    "slave": "/spam/spam/foo",
	"ignore": ["*__pycache__*", ".*", "*.bmp" ]
}

```

# Utilizzo dei percorsi di mappatura

I file di mappatura devono essere condivisi tra computer master e slave per questo motivo
dovranno essere salvati in un percorso S3.

Quindi creo un percorso in:

`bucketname/spam/foo/maps`

sul quale carico il file 'mainmap.json'.

Quando il programma chiede di inserire il percorso dei file di mappatura
è possibile inserire il percorso S3 di un singolo file, o il percorso S3 di una directory
nella quale posso inserire più file di mappatura.

# Installazione dello script

Per utilizzare il programma è sufficiente scaricare il file:

```
$ wget https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py
```

Al primo avvio verrà creato un file di configurazione chiamato 's32s.ini'.

Il programma deve essere installato in modalità MASTER sul computer master 
e in modalità SLAVE sul computer slave.

La sincronizzazione dei dati è manuale, quindi quando si vuole aggiornare
i dati da master a S3 bisognarà richiederne l'upload dal computer master così come 
quando si vuole scaricare i dati aggiornati bisognerà richiederne
il download dal computer slave .



# Esecuzione dello script

La prima volta che lo script viene eseguito verrà chiesto di:

1) Configurare il computer come master o slave.
2) Inserire il percorso S3 del file di mappatura o della direcory contenente più file di mappatura.


# Esecuzione contemporanea della modalità MASTER e SLAVE

Il programma può essere utilizzato in uno stesso computer sia in modalità
MASTER che SLAVE. In questo caso è possibile specificare due differenti percorsi S3
dei file di mappatura, uno per la modalità MASTER e uno per la modalità SLAVE.

Utilizzare una stessa mappatura nelle due modalità
non solo non ha senso ma anche potenzialmente pericoloso per i proprio dati.


# File 's32s.ini'

Da un utente iniziale il file di configurazione non dovrebbe modificato.
Utenti più esperti possono modificarlo per disattivare
alcune funzionalità di controllo che rallentano l'esecuzione dei task di upload e download.

Tra le opzioni che è possibile modificare manualmente
all'interno del nodo [MAIN] del file cofing.ini troviamo:
```
[MAIN]
skip_order_maps = False
skip_delete_alert = False
skip_tranfer_detail = False
time_sleep_after_rm = 3

```
| Var | Type | Descrizione |
| --- | --- | --- |
| `skip_order_maps` | bool | Permette di evitare l'ordinamento automatico della mappe. |
| `skip_delete_alert` | bool | Permette di nascondere gli avvisi di cancellazione dei dati. |
| `skip_tranfer_detail` | bool | Permette di proseguire senza vedere i dettgali del trasfemento. |
| `time_sleep_after_rm` | int | Rappresenta il numero di secondi di attesa tra un comando di eliminazione e un operazione di scrittura. Questo dipende in parte dal tempo che il sistema necessita per completare il task. Se si riscontrano problemi nella gestione dei file locali in modalità slave si può aumentare questo valore. |
















