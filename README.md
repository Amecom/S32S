# S32S

S32S is Python command-line interface (CLI) program to automate
data transfers, through routing paths, between master and slave computers using AWS S3
as middleware and long-term repository.


## Screenshot

![S32S Screenshot](https://raw.githubusercontent.com/Amecom/S32S/master/screenshot.png)

## Data flow

```
COMPUTER MASTER >> MIDDLEWARE S3 >> COMPUTERS SLAVE
```

- **Master**:
The master computer contains the original files. When a project is ready to be
distributed program loads data on S3 middleware.


- **Middleware S3**:
Receive data from the master computer to create a long-term, secure, and high-reliability repository
from which slave computers can retrieve data.

- **Slave**:
The slave computers download the desired data from the middleware S3.
You can recreate or upgrade a machine with just one command.

## CAUTION
The program includes **routines that delete whole directories** from the slave computers
and from the AWS S3 bucket provided with access.
The author is not liable for any loss of data caused
use, modification, or error in the program.


## Note on S3 paths

Libraries, as Boto3, usually relate
to an AWS S3 object specifying the name of the 'bucket' and a 'prefix' separately.
In this context a **path S3 intends
a single string consisting of 'nomebucket' + '/' + 'prefix' **
example `namebucket/prefix/file.ext`.

# Installation

The program should not be installed, just download it and run it as python3 script.
```
$ wget https://raw.githubusercontent.com/Amecom/S32Server/master/s32s.py
$ python3 s32s.py
```

## Requirements

- Python 3.x
- Package [Boto3] (https://github.com/boto/boto3)
- Routing file

## Install Boto3

```
$ pip install boto3
```
The use of BOTO3 in the program
requires the creation of a ```~/.aws/credentials``` file similar to this:
```
[default]
aws_access_key_id = MY_ACCESS_KEY
aws_secret_access_key = MY_SECRET_KEY
```

More info on [guida BOTO3](https://github.com/boto/boto3).

## Create a routing file

The routing JSON file contains a list of map objects.
A map object describes master, slave and S3 paths:

| Property | Mandatory | Description |
| --- | --- | --- |
| `name` | YES | Map name |
| `description` | NO  | Map description |
| `s3` | YES | S3 path where the data will be stored |
| `master` | YES IF MASTER | Files directory on the MASTER computer |
| `slave` | YES IF SLAVE | Files directory on the SLAVE computer |
| `ignore` | NO | Exclusion rules of the paths |

Sample File 'routing.json':
```json
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

The sample file "routing.json" file contains two maps.

- 'MAP 1' synchronizes all objects in (windows) "c:/path/dir/master/1"
on path S3 "bucketname / backup / dir1" and path S3 on the SLAVE directory (unix)
"/path/slave/dir1". It contains the 'ignore' directives to exclude items during transfer.

- 'MAP 2' through the 'files' property specifies the individual files
which you want to copy from the master directory "c:/path/dir/master/2".

IMPORTANT:

- When only the path of the directory (MAP 1) is specified then:
	- If the destination directory does not exist, it will be created.
	- If it exists it will be deleted, with all the files contained, and recreated with the new files.

- When a list of files (MAP 2) is specified then:
	- The destination directory must exist. It will not be created.
	- The files contained in the destination directory, if they are not included in the list 'files', are preserved.

### Save the routing file

The routing file is shared between MASTER and SLAVE for this reason
must be saved in an S3 path example `bucketname/spam/foo/maps/routing.json`.

When requesting a rouing file you can enter the S3 path of a file or directory.
In the second case all routing files in the directory will be loaded.

## Ignore property

The property ignore, if expressed, is a list of filter rules of objects as not to transfer.

You can use the wildcard '*' in this way:

| Examples | Description |
| --- | --- |
| `string*` | Excludes paths that start with 'string' |
| `*string*`| Excludes paths that contain with 'string' |
| `*string` | Excludes paths that ending with 'string' |

NOTE. The wildcard does not work on the file name but on the relative path
to the root directory. Example if the direcotry 'master' is `/date/foo`
and there is a `/data/foo/spam/dir/picure.jpg` file, the ignore directive is applied
to the string `spam/dir/picture.jpg` and NOT to `picture.jpg` or `/spam/dir/picture.jpg`.

## File 's32s.ini'

At the first run of the program, a s32s.ini file is created.

Most options in the s32s.ini file are configurable
from interface. However, you can add custom commands
inserting instructions into the .ini file

### Custom command

You can add it to the program interface
customized command to call without leaving the program itself.

Example: The SLAVE computer is an APACHE web server.
It may be useful to insert into the interface
a command to restart the httpd service.
To do this just add it in the s32s.ini file under the [CUSTOMCOMMAND]
the following line:

```ini
[CUSTOMCOMMAND]
http_restart = sudo service httpd restart
```
You can enter different commands on different rows.