# S32S

S32S è un programma multipiattaforma ad interfaccia a riga di comando (CLI) scritto in Python3
per automatizzare, attraverso una mappatura dei percorsi,
i trasferimenti di directory tra computers utilizzando AWS S3
come middleware e repository a lungo termine.

## Screeshot

![S32S Screenshot](https://raw.githubusercontent.com/Amecom/S32S/master/screenshot.png)

## Flusso dati

```
COMPUTER MASTER >> MIDDLEWARE S3 >> COMPUTERS SLAVE
```

- **Master**:
Il computer master contiene i file originali. Quando un progetto è pronto per essere 
distribuito si ordina al programma di caricare i dati sul middleware S3.

- **Middleware S3**:
Riceve i dati dal computer master e crea un repository a lungo termine, sicuro e ad alta affidabilità
da cui i computers slave possono prelevare i dati.

- **Slave**:
I computers slave, su ordine del programma, prelevano i dati desiderati dal middleware S3.
È possibile ricreare o aggiornare una macchina tramite un solo comando.

## ATTENZIONE

Il programma include **routine che eliminano intere directory** dal computer SLAVE
e dal bucket AWS S3 di cui si fornisce l'accesso. 
L'autore non è responsabile di eventuali perdite di dati causati
dall'uso, dalla modifica o da errori del programma.

## Nota sui percosi S3

Le librerie che utilizzano AWS S3 come Boto3 solitamente si riferiscono 
ad un oggetto specificando separatamente il nome del 'bucket' e un 'prefix'. 
In questo contesto un **percorso S3 intende 
un'unica stringa composta da 'nomebucket' + '/' + 'prefix'**
esempio `nomebucket/prefix/file.ext`. 


# Installazione

Il programma non deve essere installato è sufficiente scaricalo ed eseguirlo come script python3.

```
$ wget https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py
$ python3 s32s.py
```

## Requisiti

- Python 3.x
- Package [Boto3](https://github.com/boto/boto3)
- File di mappatura percorsi

## Installare Boto3

```
$ pip install boto3
```

L'utilizzo della libreria BOTO3 da parte del programma
richiede la creazione di un file ```~/.aws/credentials``` simile a questo:

```
[default]
aws_access_key_id = MY_ACCESS_KEY
aws_secret_access_key = MY_SECRET_KEY
```

Maggiori informazioni su [guida BOTO3](https://github.com/boto/boto3).

## Creare un file di mappatura

Il file di mappatura è un file JSON che contiene una lista di oggetti mappa.
Una oggetto mappa descrive percorsi indipendente ed è formato dalle seguenti proprietà:

| Property | Mandatory | Description |
| --- | --- | --- |
| `name` | YES | Map name |
| `description` | NO  | Map description |
| `s3` | YES | Percorso S3 dove verranno conservati i dati. |
| `master` | YES IF MASTER | Directory dei files sul computer MASTER che verranno trasferiti su S3. |
| `slave` | YES IF SLAVE | Directory del computer SLAVE in cui verranno copiati i file recuperati da S3. |
| `ignore` | NO | Regole di esclusione dei percorsi. |

Esempio file 'mapping.json':
```
[
    {
      "name": "MAP 1",
      "description": "OPTIONAL MAP 1 DESCRIPTION",
      "master": "c:/path/dir/master/1",
      "s3": "bucketname/backup/dir1",
      "slave": "/path/slave/dir1",
      "ignore": ["*__pycache__*", ".*", "*.bmp" ]
    },
    {
      "name": "MAP 2",
      "description": "OPTIONAL MAP 2 DESCRIPTION",
      "master": "c:/path/dir/master/2",
      "s3": "bucketname/dir/dir/dir",
      "slave": "/path/slave/dir2",
	  "files": ["filename_1", "filename_2"]
    }
]
```

Il file "mapping.json" contiene due mappe.

- 'MAP 1' sincronizza tutti gli oggetti presenti in "c:/path/dir/master/1"
sul percorso S3 "bucketname/backup/dir1" e dal percorso S3 sulla directory SLAVE "/path/slave/dir1".
Contiene delle direttive 'ignore' per escludere degli oggetti durante il trasferimento.

- 'MAP 2' tramite la proprietà 'files' specifica i singoli file
che si vuole copiare dalla directory master "c:/path/dir/master/2".

IMPORTANTE:

- Quando è specificato solo il percorso della directory (MAP 1) allora:
	- Se la directory di destinazione non esiste verrà creata.
	- Se esiste verrà cancellata, e con essa tutti i files contenuti, e ricreata con i nuovi files.

- Quando è specificata una lista di files (MAP 2) allora:
	- La directory di destinazione deve esistere. Non verrà creata.
	- I files contenuti nella directory destinazione, se non sono inclusi nella lista 'files', sono conservati.

### Salvare il file di mappatura

Il file di mappatura è condiviso tra MASTER e SLAVE per questo motivo
deve essere salvato in un percorso S3 esempio `bucketname/spam/foo/maps/mapping.json`.

Alla richiesta di inerimento di una mappa di percorsi
è possibile inserire il percorso S3 di un file o di una directory.
Nel secondo caso verranno caricati tutti i file mappatura presenti nella directory.


## Proprietà ignore

La proprietà ignore, se espressa, è una lista di regole di filtro degli oggetti da non trasferire.

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


## File 's32s.ini'

Alla prima esecuzione del programma viene creato un file s32s.ini.

La maggior parte delle opzioni presenti nel file s32s.ini sono configurabili
dall'interfaccia. Tuttavia è possibile aggiungere comandi personalizzati 
inserendo instruzioni nel file .ini

### Custom command

È possibile aggiungere nell'interfaccia del programma dei comandi 
personalizzati da richiamare senza uscire dal programma stesso.

Esempio: il computer SLAVE è un web server APACHE
su cui vengono caricati dal middleware S3 i file aggiornati di un sito web. 
In questo esempio potrebbe essere utile inserire nell'interfaccia
un comando per riavviare il servizio httpd.
Per fare questo basta aggiungere nel file s32s.ini sotto il blocco [CUSTOMCOMMAND]
la seguente riga:

```
[CUSTOMCOMMAND]
http_restart = sudo service httpd restart
```
È possibile inserire un numero illimitato di comandi su righe diverse.
