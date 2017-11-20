# S32S

S32S è un programma ad interfaccia a riga di comando (CLI) scritto in Python3
per automatizzare, attraverso una mappatura dei percorsi,
i trasferimenti di directory tra computers utilizzando AWS S3
come middleware e repository a lungo termine.

Il computer MASTER trasferisce i file locali su AWS S3
mentre il computer SLAVE recupera e salva localmente i file presenti su AWS S3.
La sincronizzazione dei dati non è automatica ma a comando.

## Screeshot

![S32S Screenshot](screenshot.png?raw=true)

## Flusso dati

```
MASTER >> MIDDLEWARE S3 >> SLAVE

ORIGINALE >> REPOSITORY >> COPIA
```
- **Master**
Contiene i file originali e ed è il repository di sviluppo. Quando un progetto è pronto per essere 
distribuito il programma carica i dati sul middleware S3.

- **Middleware S3**
Riceve i dati dal computer master e crea un repository a lungo termine, sicuro e
sempre online da cui i computers slave possono attingere.

- **Slave**
Prelevano dati dal middleware. Il
caricamento dei dati sulle macchine slave è fatto manualmente tuttavia è possibile ricreare o aggiornare
la macchina tramite un solo comando del programma.

## ATTENZIONE

Il programma include **routine che eliminano intere directory** dal computer SLAVE
e dal bucket AWS S3 di cui si fornisce l'accesso. 
L'autore non è responsabile di eventuali perdite di dati causati
dall'uso, dalla modifica o da errori del programma.

- Eseguire sempre delle copie di backup dei dati importanti. 
- Prestare molta attenzione ai messaggi di alert che il programma fornisce.
- Avere chiaro cosa si sta facendo e quali sono le conseguenze.

## Nota sui percosi S3

Le librerie che utilizzano AWS S3 come Boto3 solitamente si riferiscono 
ad un oggetto specificando separatamente il nome del 'bucket' e un 'prefix'. 
In questo contesto un **percorso S3 intende 
una unica stringa composta da 'nomebucket' + '/' + 'prefix'**
esempio `nomebucket/prefix/file.ext`. 


# Installazione

Il programma può essere installato su un computer MASTER e su uno o più computer SLAVE.

Scaricare ed eseguire il programma

```
$ wget https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py
$ python s32s.py
```

Al primo avvio verrà creato un file 's32s.ini' e verrà chiesto di inserire:

1) la modalità di esecuzione del computer: MASTER o SLAVE.
2) il percorso S3 del file o directory di mappatura.


## Requisiti

- Python 3.x
- Package [Boto3](https://github.com/boto/boto3)
- File 'credentials'
- File di mappatura percorsi

## Installare Boto3

```
$ pip install boto3
```

## Creare file credentials


Il corretto funzionamento della libreria BOTO3 inclusa nel codice.
dipende dalla creazione di un file ```~/.aws/credentials```
Il contenuto del file è simile a questo:

```
[default]
aws_access_key_id = MY_ACCESS_KEY
aws_secret_access_key = MY_SECRET_KEY
```

Maggiori informazioni su [guida BOTO3](https://github.com/boto/boto3).

## Creare un file di mappatura

Il file di mappatura è un file JSON che descrive una lista di oggetti/dizionari mappa.
Una mappa descrive un percorso di mappatura indipendente ed è formato dalle seguenti proprietà

| Property | Mandatory | Description |
| --- | --- | --- |
| `name` | YES | Map name |
| `description` | NO  | Map description |
| `s3` | YES | Percorso S3 dove verranno conservati i dati. |
| `master` | YES IF MASTER | Directory dei files sul computer MASTER che verranno trasferiti su S3. |
| `slave` | YES IF SLAVE | Directory del computer SLAVE in cui verranno copiati i file recuperati da S3. |
| `ignore` | NO | Regole di esclusione dei percorsi. |

Esempio 'map.json':
```
[
    {
      "name": "PROJECT 1",
      "description": "OPTIONAL PROJECT 1 DESCRIPTION",
      "master": "c:/path/dir/master/1",
      "s3": "bucketname/backup/dir1",
      "slave": "/path/slave/dir1",
      "ignore": ["*__pycache__*", ".*", "*.bmp" ]
    },
    {
      "name": "PROJECT 2",
      "description": "OPTIONAL PROJECT 2 DESCRIPTION",
      "master": "c:/path/dir/master/2",
      "s3": "bucketname/dir/dir/dir",
      "slave": "/path/slave/dir2",
	  "files": ["filename_1", "filename_2"]
    }
]
```

Il file "map.json" contiene due mappe chiamate 'PROJECT 1' e 'PROJECT 2'.

- 'PROJECT 1' sincronizza tutti gli oggetti presenti in "c:/path/dir/master/1"
sul percorso S3 "bucketname/backup/dir1" e dal percorso S3 sulla directory SLAVE "/path/slave/dir1".
Contiene delle direttive 'ignore' per escludere degli oggetti durante il trasferimento.

- 'PROJECT 2' tramite la proprietà 'files' specifica i file che si vuole copiare dalla directory master "c:/path/dir/master/2".

IMPORTANTE:

- Quando viene specificato solo il percorso della directory come in 'PROJECT 1' allora:
	- Se la directory di destinazione non esiste verrà creata.
	- Se esiste verrà cancellata, e con essa tutti i files contenuti, e ricreata con i nuovi files.

- Quando viene specificata una lista di files allora:
	- La directory di destinazione deve esistere. Non verrà creata.
	- I files contenuti nella directory destinazione, se non sono inclusi nella lista 'files', sono conservati.

### Salvare il file di mappatura

Il file di mappatura deve essere condiviso tra MASTER e SLAVE per questo motivo
deve essere salvato in un percorso S3.

Quindi creo un percorso S3 `bucketname/spam/foo/maps` sul quale carico il file `map.json`.

Quando il programma chiede di inserire il percorso dei file di mappatura
è possibile inserire il percorso S3 di un file o di una directory.
In una directory è possibile inserire più file di mappatura.


## Direttiva ignore

Ogni mappa può avere una proprietà ignore che, se espressa, deve essere una lista.

È possibile utilizzare il carattere jolly '*' in questo modo:

| Examples | Description |
| --- | --- |
| `string*` | esclude i percorsi che iniziano con 'string' |
| `*string*`| esclude i percorsi che contengono 'string' |
| `*string` | esclude i percorsi che finiscono con 'string' |


ATTENZIONE. Il carattere jolly non agisce sul nome del file ma sul percorso relativo
alla directory principale. Esempio se la direcotry 'master' è `/data/foo`
ed esiste un file `/data/foo/spam/dir/picure.jpg`, la direttiva ignore viene applicata
alla stringa `spam/dir/picture.jpg` e NON a `picture.jpg` o `/spam/dir/picture.jpg`.

## Esecuzione contemporanea della modalità MASTER e SLAVE

Il programma può essere utilizzato in uno stesso computer sia in modalità
MASTER che SLAVE. In questo caso è necessario
specificare un file di mappatura per la modalità MASTER e uno per la modalità SLAVE.

Utilizzare uno stessao file di mappatura nelle due modalità all'interno dello stesso computer
non ha senso ed è pericoloso per i proprio dati.


## File 's32s.ini'

La modifica del file s32s.ini nella maggior parte delle sue opzioni è configurabile
attraverso 'l'interfaccia del programma
alcune funzionalità permettono di velocizzare l'esecuzione dei task di upload e download.

### Custom command

È possibile aggiungere all'interfaccia del programma comandi da richiamare
senza uscire dal programma stesso.

Esempio: il computer SLAVE è un web server APACHE
su cui vengono caricati dal percorso S3 i file aggiornati di un sito web potrebbe
essere utile inserire nell'interfaccia un comando per riavviare il servizio httpd.
In questo caso si può aggiungere nel file s32s.ini sotto il blocco [CUSTOMCOMMAND]
la seguente riga:

```
[CUSTOMCOMMAND]
http_restart = sudo service httpd restart
```

È possibile inserire un numero illimitato di comandi su ighe diverse.
