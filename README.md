# S32S

Script Python3 per gestire trasferimenti di dati tra computer utilizzando AWS S3
come middleware e mappature di percorsi.

Il computer MASTER trasferisce i file locali su AWS S3
mentre il computer SLAVE recupera e salva localmente i file presenti su AWS S3.
Il trasferimento dei dati tra repository è manuale.

## Flusso dati

```
MASTER		>> S3			>> SLAVE

ORIGINALE	>> REPOSITORY	>> COPIA
```

## ATTENZIONE

Il programma include **routine che eliminano intere directory** dal computer SLAVE
e dal bucket AWS S3 di cui si fornisce l'accesso. 
L'autore non è responsabile di eventuali perdite di dati causati
dall'uso, dalla modifica o da errori del programma.

- Eseguire sempre delle copie di backup dei dati importanti. 
- Prestare molta attenzione ai messaggi di alert che il programma fornisce.
- Avere chiaro cosa si sta facendo e quali sono le conseguenze.

## Nota sui percosi S3

Nelle librerie che utilizzano AWS S3 solitamente ci si riferisce 
a un oggetto specificando separatamente
il nome del 'bucket' e un 'prefix'. 
In questo programma nei file di configurazione e negli input utente
quando ci si riferisce a un **percorso S3 intende 
una stringa composta dal nome del bucket e dal prefix
uniti dal carattere '/'** esempio `NOMEBUCKET/PREFIX`. 


# Installazione

È necessario installare il programma sia sul computer MASTER che sul computer SLAVE
anche se dato che il computer MASTER e SLAVE non comunicano direttamente tra loro
è possibile utilizzare lo script anche solo in una modalità.

Scaricare il file

```
$ wget https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py
```

ed eseguire il programma

```
$ python s32s.py
```

Al primo avvio verrà creato un file di configurazione 's32s.ini' 
e verrà chiesto di:

1) Selezionare la modalità di esecuzione: MASTER o SLAVE.
2) Inserire il percorso S3 del file o della directory di mappatura.


## Requisiti

- Python 3.x
- SDK [Boto3](https://github.com/boto/boto3)
- File 'credentials' per l'accesso a S3
- File di mappatura dei percorsi

## Installare Sdk Boto3

```
$ pip install boto3
```

## Creare file credentials

È necessario configurare le credenziali di accesso allo storage S3 
per il corretto funzionamento della libreria BOTO3 inclusa nel codice .

Occorre quindi creare un file ```~/.aws/credentials```
di contenuto è simile a questo:

```
[default]
aws_access_key_id = MY_ACCESS_KEY
aws_secret_access_key = MY_SECRET_KEY
```

Per maggiori informazioni, compresa la configurazione su altri SO,
consultare le [guida BOTO3](https://github.com/boto/boto3).


## Creare un file di mappatura

Il programma richiede almeno un file con estensione .json 
per mappare i percorsi tra master, s3, e slave.

Un file di mappatura è un file in formato JSON che contiene una lista di oggetti/dizionari.
Ciascun oggetto descrive un percorso di mappatura indipendente ed è formato dalle seguenti proprietà

| Property | Mandatory | Description |
| --- | --- | --- |
| `name` | YES | Map name |
| `description` | NO  | Map description |
| `s3` | YES | Percorso S3 dove verranno conservati i dati. |
| `master` | IF MASTER | Directory che contiene i file originali del computer MASTER. |
| `slave` | IF SLAVE | Directory in cui verranno copiati i file recuperati dal percorso S3. |
| `ignore` | NO | Regole di esclusione dei percorsi. |

Esempio file 'mainmap.json':
```
[
    {
      "name": "PROJECT 1",
      "description": "OPTIONAL PROJECT DESCRIPTION",
      "master": "c:/path/dir/master/1",
      "s3": "bucketname/backup/dir1",
      "slave": "/path/slave/dir1",
      "ignore": ["*__pycache__*", ".*", "*.bmp" ]
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

- 'PROJECT 1' sincronizza tutti i file e le directory presenti nel percorso MASTER
sul percorso S3 e dal percorso S3 su SLAVE. Contiene inoltre delle direttive 'ignore'
per escludere degli oggetti durante il trasferimento.

- 'PROJECT 2' tramite la proprietà 'files' specifica i file che si vuole copiare.

IMPORTANTE:

1) Quando viene specificato solo il percorso della directory allora
la directory di destinazione se non esiste verrà creata; se esiste verrà cancellata e ricreata
perdendo quindi tutti i files precedentemente contenuti.

2) Quando viene specificata una lista di files allora la directory di destinazione deve esistere,
non verrà creata; altri files contenuti nella directory verranno conservati.

### Salvare il file di mappatura

Il file di mappatura deve essere condiviso tra computer master e slave per questo motivo
dovrà essere salvato in un percorso S3.

Quindi creo un percorso in:

`bucketname/spam/foo/maps`

sul quale carico il file `mainmap.json`.

Quando il programma chiede di inserire il percorso dei file di mappatura
è possibile inserire il percorso S3 di un singolo file, o il percorso S3 di una directory
nella quale è possibile inserire più file di mappatura.


## Direttiva ignore

Ogni oggetto mappatura può contenere la proprietà ignore.
Se espressa questa proprietà deve essere una lista.

È possibile utilizzare il carattere jolly '*' in questo modo:

| Examples | Description |
| --- | --- |
| `string*` | esclude i percorsi che iniziano con 'string |
| `*string*`| esclude i percorsi che contengono 'string |
| `*string` | esclude i percorsi che finiscono con 'string |


NOTA. Il carattere jolly non agisce sul nome del file ma sul percorso relativo
alla directory di principale dell'oggetto che si vuole trasferire.
Esempio se il pecorso master nel file di mappatura è `/DATA/FOO`
ed esiste un file `**/DATA/FOO/SPAM/**DIR/picure.jpg`, la direttiva ignore viene applicata
alla stringa `DIR/picture.jpg` e NON a `picture.jpg` o `/DIR/picture.jpg`.

## Esecuzione contemporanea della modalità MASTER e SLAVE

Il programma può essere utilizzato in uno stesso computer sia in modalità
MASTER che SLAVE. In questo caso è possibile specificare due differenti percorsi S3
dei file di mappatura, uno per la modalità MASTER e uno per la modalità SLAVE.

Utilizzare una stessa mappatura nelle due modalità
non solo non ha senso ma anche pericoloso per i proprio dati.


## File 's32s.ini'

La modifica del file s32s.ini, facoltativa, permette di disattivare
alcune funzionalità che permettono ad esempio di velocizzare l'esecuzione dei task di upload e download.

Nel nodo [MAIN] del file s32s.ini troviamo:

| Var | Type | Descrizione |
| --- | --- | --- |
| `skip_order_maps` | bool | Evita l'ordinamento automatico della mappe. |
| `skip_delete_alert` | bool | True nasconde gli avvisi di cancellazione dei dati. |
| `skip_tranfer_detail` | bool | True permette di nascondere i dettagli del trasfemento. |
| `time_sleep_after_rm` | int | Numero di secondi di attesa tra un comando di eliminazione e un operazione di scrittura. Questo dipende in parte dal tempo che il sistema necessita per completare il task di elminazione di una directory. Se si riscontrano problemi nella gestione dei file locali in modalità slave si può aumentare questo valore. |


