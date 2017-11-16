# S32S

Script Python3 per gestire trasferimenti di dati tra computer utilizzando AWS S3
come middleware e mappature di percorsi.

Il computer MASTER trasferisce i file locali su AWS S3
mentre il computer SLAVE recupera e salva localmente i file presenti su AWS S3.
La sincronizzazione dei dati non è automatica ma a comando.

## Flusso dati

```
MASTER >> S3 >> SLAVE

ORIGINALE >> REPOSITORY >> COPIA
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
In questo conteso quando ci si riferisce a un **percorso S3 intende 
una stringa unica composta dal nome del bucket e dal prefix
uniti dal carattere '/'** esempio `NOMEBUCKET/PREFIX`. 


# Installazione

È necessario installare il programma sia sul computer MASTER che sul computer SLAVE
anche se è possibile utilizzare lo script anche solo in una modalità.

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

Il programma richiede almeno un file con informazioni dei percorsi master, S3, e slave.

Un file di mappatura è un file in formato JSON che contiene una lista di oggetti/dizionari.
Ciascun oggetto descrive un percorso di mappatura indipendente ed è formato dalle seguenti proprietà

| Property | Mandatory | Description |
| --- | --- | --- |
| `name` | YES | Map name |
| `description` | NO  | Map description |
| `s3` | YES | Percorso S3 dove verranno conservati i dati. |
| `master` | YES IF MASTER | Directory dei files sul computer MASTER che verranno trasferiti su S3. |
| `slave` | YES IF SLAVE | Directory del computer SLAVE in cui verranno copiati i file recuperati da S3. |
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

- 'PROJECT 1' sincronizza tutti i file e le directory presenti nella directory MASTER
sul percorso S3 e dal percorso S3 sula directory SLAVE. Contiene inoltre delle direttive 'ignore'
per escludere degli oggetti durante il trasferimento.

- 'PROJECT 2' tramite la proprietà 'files' specifica i file che si vuole copiare.

IMPORTANTE:

- Quando viene specificato solo il percorso della directory allora
la directory di destinazione se non esiste verrà creata; se esiste verrà cancellata e ricreata
perdendo quindi tutti i files precedentemente contenuti.

- Quando viene specificata una lista di files allora la directory di destinazione deve esistere,
non verrà creata; altri files contenuti nella directory verranno conservati.

### Salvare il file di mappatura

Il file di mappatura deve essere condiviso tra computer MASTER e SLAVE per questo motivo
viene salvato in un percorso S3.

Quindi creo un percorso in:

`bucketname/spam/foo/maps`

sul quale carico il file `mainmap.json`.

Quando il programma chiede di inserire il percorso dei file di mappatura
è possibile inserire il percorso S3 del singolo file o di una directory,
nel secondo caso è possibile inserire più file di mappatura nella directory.


## Direttiva ignore

Ogni oggetto mappatura può contenere la proprietà ignore.
Se espressa questa proprietà deve essere una lista.

È possibile utilizzare il carattere jolly '*' in questo modo:

| Examples | Description |
| --- | --- |
| `string*` | esclude i percorsi che iniziano con 'string' |
| `*string*`| esclude i percorsi che contengono 'string' |
| `*string` | esclude i percorsi che finiscono con 'string' |


NOTA. Il carattere jolly non agisce sul nome del file ma sul percorso relativo
alla directory principale. Esempio se la direcotry 'master' nel file di mappatura è `/data/foo`
ed esiste un file `/data/foo/spam/dir/picure.jpg`, la direttiva ignore viene applicata
alla stringa `spam/dir/picture.jpg` e NON a `picture.jpg` o `/spam/dir/picture.jpg`.

## Esecuzione contemporanea della modalità MASTER e SLAVE

Il programma può essere utilizzato in uno stesso computer sia in modalità
MASTER che SLAVE. In questo caso è possibile (e necessario) 
specificare un file di mappatura per la modalità MASTER e uno per la modalità SLAVE.

Utilizzare una stessa mappatura nelle due modalità
non solo non ha senso ma anche pericoloso per i proprio dati.


## File 's32s.ini'

La modifica del file s32s.ini, facoltativa, permette di disattivare
alcune funzionalità che permettono ad esempio di velocizzare l'esecuzione dei task di upload e download.

Nel nodo [MAIN] del file s32s.ini troviamo:

| Var | Type | Descrizione |
| --- | --- | --- |
| `skip_order_maps` | bool | True evita l'ordinamento alfabetico dei percorsi di mappatura per proprietà 'name'. |
| `skip_delete_alert` | bool | True nasconde gli alert di cancellazione dei dati. |
| `skip_tranfer_detail` | bool | True nasconde il riepilogo del trasfemento. |
| `time_sleep_after_rm` | int | Numero di secondi di attesa tra un comando di eliminazione e un operazione di scrittura. Questo dipende in parte dal tempo che il sistema necessita per completare il task di elminazione di una directory. Se si riscontrano problemi nella gestione dei file locali in modalità slave si può aumentare questo valore. |


