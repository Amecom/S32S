#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import sys
import configparser
import shutil
import json
import subprocess
import urllib.request
import errno
import botocore.exceptions
from time import sleep
import boto3

__version__ = "1.5"
os.sep = "/"
S3RESOURCE = boto3.resource('s3')
CONFIG = configparser.ConfigParser()
CONFIG_FILENAME = 's32s.ini'
URL_SCRIPT = "https://raw.githubusercontent.com/Amecom/S32S/master/s32s.py"
URL_GET_VERSION = "https://raw.githubusercontent.com/Amecom/S32S/master/VERSION"
URL_DOC = "https://github.com/Amecom/S32S"
ISMASTER = None
VALID_BUCKETS = {}

"""
LABELS
"""

TXT_TRANSFER_INFO = """
 \033[4m{map[name]} - from file: {map[filename]}\033[0m
 {map[description]}
    \033[94m
    TRANSFER INFORMATION
    * FROM {origin[name]} : '{origin[path]}'
   >> TO {destination[name]} : '{destination[path]}'
    \033[0m
    Files  : {map[files]}
    Ignore : {map[ignore]}
"""
TXT_LABEl_CONFIGURATION = "Configuration"
TXT_SORT_MAPS_ALPHABETICALLY = "Sort the maps alphabetically"
TXT_HIDE_DEL_ALERT = "Slert delete"
TXT_HIDE_TRANSFER_DETAIL = "Show transfer details"
TXT_DEFAULT_VALUE = "DEFAULT VALUE"
TXT_CURRENT_STATUS = "Current status is {status}"
TXT_SWITH_CONFIRM = "You have moved to {mode_name} mode"
TXT_TRANFER_ALL_HEADER = "Execute transfert {current} of {total}"
TXT_ALL_TRANSFER_COMPLETE = "{count} transfers complete"
TXT_MAPS_HELP_INFO = "Information on creating a maps is available at {link}"
TXT_MAPS_RELOAD_OK = "Maps Reloaded"
TXT_MAPS_DETAILS = "Maps Details '{path}'"
TXT_LABEL_SELECT_MODE = "Select mode"
TXT_LABEL_CMD_MD = "Maps Details"
TXT_LABEL_CMD_MR = "Maps Reload"
TXT_LABEL_CMD_MO = "Maps Open"
TXT_LABEL_CMD_SM = "Switch Mode"
TXT_LABEL_CMD_X = "Exit"
TXT_LABEL_CMD_ALL = "Transfer all"
TXT_LABEL_MAIN_COMMAND = "Main command"
TXT_LABEL_CUSTOM_COMMAND = "Custom command"
TXT_LABEL_TRANFER_LIST = "Transfer command"
TXT_NEW_SCRIPT_VERSION_AVAILABLE = "New version of programm is available"
TXT_SCRIPT_UPDATED = "New programm has been downloaded. Old files still exists renamed {old_name}"
TXT_RESTART = "Restart script."
TXT_MODE_INFO = "*** {mode} MODE *** S3 Maps Path loaded: '{mapspath}'"
TXT_EXECUTE_CMD = "EXECUTE: {cmd}"
TXT_ACTION_MASTER = "Replace s3 object with local ones"
TXT_ACTION_SLAVE = "Replace local objects with those stored in S3"
TXT_TRANSFER_COMPLETE = "TRANSFER COMPLETE"
TXT_LOADING = "Loading '{what}'... "
TXT_DELETE_OBJECT = "{storage} DELETE: {object}"
TXT_CREATE_OBJECT = "{storage} CREATE: {object}"
TXT_SAVE_OBJECT = "{storage} SAVE IN '{root}' OBJECT: '{object}'"
TXT_TRANSFER_IGNORE = "{storage} IGNORE: {object}"

TXT_INPUT = "Enter command"
TXT_INPUT_OPTION = "Enter input {option}"
TXT_INPUT_ENTER = "Press ENTER to continue..."
TXT_INPUT_INSERT_MAPS_PATH = "Insert S3 path contains maps files for '{mode}'"
TXT_INPUT_INSERT_MAPS_PATH_EXIT = "Insert S3 path contains maps files for '{mode}' [x to Exit]"
TXT_INPUT_CONFIRM = "Enter 'y' to confirm, anything else to skip task" 

TXT_WARNING_EXIT_TASK_WITH_ERROR = "Task not completed"
TXT_WARNING_MAPS_NOT_LOADED = "'{mode}' MAPS  not loaded, use 'mo' command to open maps"
TXT_WARNING_TRANSFER = "'{files}' in {storage} : '{path}' Will be DELETE and REPLACED"

TXT_ERR_MASTER_OBJECT_NOT_EXISTS = "Path object '{path}' not exists in '{storage}'"
TXT_ERR_S3_CONNECTION_ERROR = "Could not connect to S3. Verify your internet connection and try again"
TXT_ERR_S3_BUCKET_LOAD = "S3 Bucket '{bucket_name}' NOT FOUND"
TXT_ERR_S3_LIST_CONNECTION = "S3 PATH '{path}': bucket not found or access denied or no internet access"
TXT_ERR_S3_LIST_CONTENTS = "S3 PATH '{path}': path does not have a contents or not exists"
TXT_ERR_SCRIPT_UPDATE_CONFIG = "not found 'url_script_update' property in configuration file"
TXT_ERR_MAPS_RELOAD_KO = "Erron on reload Maps"
TXT_ERR_MAPS_NOT_FOUND = "MAPS NOT FOUND OR INVALID"
TXT_ERR_MAP_EMPTY = "EMPTY MAPS"
TXT_ERR_MAP = "Filename: '{filename}' Maps Element: '{element_id}': {error}"
TXT_ERR_MAP_SUB_USERHOME = "Path can't start with ~"
TXT_ERR_MAP_SUB_EMPTY_PROPERTY = "'{property}' property is mandatory'" 

CONFIG_SECTION = ("MAIN", "MASTER", "SLAVE", "CUSTOMCOMMAND" )
CONFIG_MAIN_OPTIONS = (
    # option name, label, default value 
    ("ismaster", TXT_SORT_MAPS_ALPHABETICALLY, 1),
    ("order_maps", TXT_SORT_MAPS_ALPHABETICALLY, 1),
    ("show_delete_alert", TXT_HIDE_DEL_ALERT, 1),
    ("show_transfer_detail", TXT_HIDE_TRANSFER_DETAIL, 1),    
    ("time_sleep_after_rm", TXT_HIDE_TRANSFER_DETAIL, 3)    
)
CONFIG_MAIN_BOOLEAN = ["ismaster", "order_maps", "show_delete_alert", "show_transfer_detail" ]
CONFIG_MAIN_NUMERIC = ["time_sleep_after_rm"]

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def disable():
        bcolors.HEADER = ''
        bcolors.OKBLUE = ''
        bcolors.OKGREEN = ''
        bcolors.WARNING = ''
        bcolors.FAIL = ''
        bcolors.ENDC = ''
        bcolors.BOLD = ''
        bcolors.UNDERLINE = ''

def print_header(txt):
    print(bcolors.HEADER + " " + txt + bcolors.ENDC)

def print_title(txt):
    print(bcolors.UNDERLINE + "\n " + txt + bcolors.ENDC)

def print_error(txt):
    print("")
    print(bcolors.FAIL + " *** ERROR ***\n " + txt + bcolors.ENDC)
    enter_to_continue()

def print_warning(txt):
    print(bcolors.WARNING + "\n *** WARNING ***\n " + txt + bcolors.ENDC)

def print_text(txt):
    print(" " + txt)

def print_success(txt):
    print(bcolors.OKGREEN + "\n " + txt + bcolors.ENDC)

def print_blue(txt):
    print(bcolors.OKBLUE + " " + txt + bcolors.ENDC)

def input_text(txt):
    return input( bcolors.BOLD + "\n > " + txt  + " :" + bcolors.ENDC)

def enter_to_continue():
    """Create a break to allow the user to read output."""
    input_text(TXT_INPUT_ENTER)

def mode_name(ismaster=None):
    """Return string that describes mode used in config."""
    if not ismaster : ismaster = ISMASTER
    return "MASTER" if ismaster else "SLAVE"

def mode_action(ismaster=None):
    """Return string that describes transfert mode."""
    if not ismaster : ismaster = ISMASTER
    return TXT_ACTION_MASTER if ismaster else TXT_ACTION_SLAVE

def clear():
    """Clear Screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def config_validate():
    save = 0
    for c in CONFIG_SECTION:
        if c not in CONFIG:
            config_load_default()
            return

    for name, label, default in CONFIG_MAIN_OPTIONS:
        if CONFIG['MAIN'].get(name) is None:
            CONFIG['MAIN'][name] = str(default)
            save = 1
        elif name in CONFIG_MAIN_BOOLEAN:
            try:
                CONFIG['MAIN'].getboolean(name)
            except ValueError:
                CONFIG['MAIN'][name] = str(default)
                save = 1
        elif name in CONFIG_MAIN_NUMERIC:
            try:
                CONFIG['MAIN'].getint(name)
            except ValueError:
                CONFIG['MAIN'][name] = str(default)
                save = 1
    if save:
        config_save()

def config_load_default():
    """return default configuration."""
    mode_conf = {
        'maps_s3_path': ''
        }
    CONFIG['MAIN'] = {}
    for name, label, default in CONFIG_MAIN_OPTIONS:
        CONFIG['MAIN'][name] = str(default)

    CONFIG[mode_name(1)] = mode_conf
    CONFIG[mode_name(0)] = mode_conf
    CONFIG['CUSTOMCOMMAND'] = {}
    config_save()


def config_save():
    """Save configuration change."""
    with open(CONFIG_FILENAME, 'w') as configfile:
        CONFIG.write(configfile)

def config_switch_main_bool(name):
    sw = not CONFIG['MAIN'].getboolean(name)
    CONFIG['MAIN'][name] = str(sw)
    config_save()

def new_version_available():
    """Check if exists new version of script."""
    try:
        f = urllib.request.urlopen(URL_GET_VERSION,timeout=3)
    except:
        pass
    else:
        data = f.read().decode('utf-8')
        t = [ int(i) for i in __version__.split(".") ]
        s = [ int(i) for i in data.split(".") ]
        return s[0] > t[0] or (s[0] == t[0] and s[1] > t[1])

def update_routine():
    """Retrive last version of script."""
    rename_old = "s32s.old.V{}.py".format(__version__)
    current_path = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.join(current_path, "s32s.py")
    script_path_old = os.path.join(current_path, rename_old)
    os.replace(script_path, script_path_old)
    sleep(2)
    urllib.request.urlretrieve(URL_SCRIPT, script_path)
    print_success(TXT_SCRIPT_UPDATED.format(old_name=rename_old))
    print_blue(TXT_RESTART)

def normalize_external_path(path):
    """Remove '/' at ends of path replace sep '\' with '/'

    Return normalized version of 'path'.    
    MUST BE USED ONLY FOR EXTERNAL PATH
    as .ini, user input, maps.
    """
    r = path.replace("\\","/")
    if r.endswith("/"):
        r = r[:-1]
    return r

def slipt_s3path(path):
    """Split path into bucket and prefix.

    Return a tuple with bucket name and prefix.
    Prefix can be a empty string.
    """
    p = path.split("/")
    bucket = p[0]
    prefix = "/".join(p[1:]) if len(p) > 1 else ""
    return bucket, prefix

"""
_get_NAME function must be used only inside ls_ mk_ rm_ function
"""

def _get_bucket(bucket_name):
    """Validate and return bucket object"""
    # err = None
    bucket = VALID_BUCKETS.get(bucket_name)
    if not bucket:

        if S3RESOURCE.Bucket(bucket_name) in S3RESOURCE.buckets.all():
            bucket = S3RESOURCE.Bucket(bucket_name)
            VALID_BUCKETS[bucket_name] = bucket
        else:
            print_error( TXT_ERR_S3_BUCKET_LOAD.format(bucket_name=bucket_name) )
            return
    return bucket
                #try:
                #    bucket.load()
                #except botocore.exceptions.EndpointConnectionError:
                #    err = TXT_ERR_S3_CONNECTION_ERROR
                #except botocore.exceptions.ClientError:
                #    err = TXT_ERR_S3_BUCKET_LOAD.format(bucket_name=bucket_name)
                #else:
                #    VALID_BUCKETS[bucket_name] = bucket
    #if err:
    #    print_error(err)
    #else:
    #    return bucket

def _get_bucket_object(s3_path):
    bucket, prefix = slipt_s3path(s3_path)
    if _get_bucket(bucket):
        # this method is used to create new object too
        # so it doesn't return explict .get() method
        return S3RESOURCE.Object(bucket, prefix)

def exists_master_path(path):
    """Return bool cheak if 'path' exists in master repository."""
    f = exists_pc_path if ISMASTER else exists_s3_path
    return f(path)

def exists_slave_path(path):
    """Return bool cheak if 'path' exists in slave repository."""
    f = exists_s3_path if ISMASTER else exists_pc_path
    return f(path)

def exists_pc_path(path):
    return os.path.isdir(path)

def exists_s3_path(path):
    bucket_name, prefix = slipt_s3path(path)
    bucket = _get_bucket(bucket_name)
    if bucket:
        # cheak if prefix exists
        try:
            objects = list(bucket.objects.filter(Prefix=prefix).limit(count=1))
        except:
            pass
        else:
            # cheak if prefix is a 'folder'..
            # use first element of objects list and test name
            name_a = path + "/"
            name_b = "/".join([bucket_name, objects[0].key])
            return name_a == name_b

def exists_master_file(filepath):
    """Return bool cheak if 'path' exists in master repository."""
    f = exists_pc_file if ISMASTER else exists_s3_file
    return f(filepath)

def exists_slave_file(filepath):
    """Return bool cheak if 'path' exists in slave repository."""
    f = exists_s3_file if ISMASTER else exists_pc_file
    return f(path)

def exists_pc_file(filepath):
    return os.path.isfile(filepath)

def exists_s3_file(filepath):
    object = _get_bucket_object(filepath)
    if object:
        try:
            object.load()
        except:
            pass
        else:
            return 1

def get_master_file(filepath):
    """Return binary data from 'filepath' in master repository."""
    f = get_pc_file if ISMASTER else get_s3_file
    return f(filepath)

def get_slave_file(filepath):
    """Return binary data from 'filepath' in slave repository."""
    f = get_s3_file if ISMASTER else get_pc_file
    return f(filepath)

def get_pc_file(filepath):
    """Return binary data from 'filepath' in local files."""
    with open(filepath, "rb") as file:
        return file.read()

def get_s3_file(filepath):
    """Return binary data from 'filepath' in S3 files."""
    object = _get_bucket_object(filepath)
    if object:
        file = object.get()
        return file['Body'].read()

def ls_master_path(path):
    """Return a generator with list of objectsstored in master repository.

    If current run mode is master the master repository is local repository
    otherwise is S3 repository
    """
    return ls_pc_path(path) if ISMASTER else ls_s3_path(path)

def ls_slave_path(path):
    """Return a generator with list of objects stored in slave repository

    If current run mode is master the slave repository is local repository
    otherwise is S3 repository.
    """
    return ls_s3_path(path) if ISMASTER else ls_pc_path(path)

def ls_pc_path(path):
    """Return generator of list of objects stored in local 'path'.

    Objects's Path is relative to given 'path'
    and directories ends with "/" char.
    """
        # norm function with os.sep = "/" can be unnecessary
    norm = lambda p: p.replace("\\","/")
    base = norm(path)
    make_relative = lambda p: norm(p).replace(base, "")[1:]
    if not os.path.exists(base):
        yield from ()
    else:
        for root, dirs, files in os.walk(base):
            for name in files:
                yield make_relative(os.path.join(root, name))
            for name in dirs:
                yield make_relative(os.path.join(root, name) + "/") 

def ls_s3_path(path):
    """Return a generator of list objects stored in S3 'path'.

    Objects Path are relative to 'path'
    and directories ends with "/" char.
    """
    bucket_name, prefix = slipt_s3path(path)
    bucket = _get_bucket(bucket_name)
    if not bucket:
        yield from ()
    else:
        objname_start_at = len(prefix) + 1
        for object in bucket.objects.filter(Prefix=prefix):
            name = object.key[objname_start_at:]
            if name != "":
                yield name

def rm_slave_object(object_path, ignore_error=0):
    """Drop all contents from slave repository 'object_path'."""
    f = rm_s3_object if ISMASTER else rm_pc_object
    return f(object_path, ignore_error)

def rm_master_object(object_path, ignore_error=0):
    """Remove all contents from 'object_path' in master repository."""
    # UNUSED FUNCTION DISABLED FOR SECURITY
    # rm_pc_object(path) if ISMASTER else return rm_s3_object(path)
    raise "DEF DISABLED"

def rm_pc_object(object_path, ignore_error=0):
    """Drop all contents from local 'object_path'."""
    if os.path.isdir(object_path):
        shutil.rmtree(object_path)
    elif os.path.isfile(object_path):
        os.remove(object_path)
    # waiting for system complete task
    sleep(int(CONFIG['MAIN'].get('time_sleep_after_rm')))
    return 1

def rm_s3_object(object_path, ignore_error=0):
    """Drop all contents from S3 'object_path'."""
    bucket_name, prefix = slipt_s3path(object_path)
    bucket = _get_bucket(bucket_name)
    if bucket:
        try:
            request = bucket.objects.filter(Prefix=prefix).delete()
        except Exception as e:
            if ignore_error:
                return 1
            else:
                print_error(str(e))
                print_error("[RM_S3_OBJECT]")
        else:
            return 1

def mk_master_object(object_path, data=None):
    """Create object in master repository 'object_path'."""
    # UNUSED FUNCTION DISABLED FOR SECURITY
    #f = mk_pc_object if ISMASTER else mk_s3_object
    #return f(object_path, data)
    raise "DISABLED"

def mk_slave_object(object_path, data=None):
    """Create object in slave repository 'object_path'."""
    f = mk_s3_object if ISMASTER else mk_pc_object
    return f(object_path, data)

def mk_pc_object(object_path, data=None):
    """Create object on local 'object_path'."""
    if data:
        # PATH IN THE SCRIPT ALWAYS MUST ENDS WITH "/"
        directory = "/".join(object_path.split("/")[:-1]) + "/"
    else:
        directory = object_path
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            print_error(str(e))
            if e.errno != errno.EEXIST:
                raise
            return
    if data:
        with open(object_path, "wb") as file:
            file.write(data)
    return 1

def mk_s3_object(object_path, data=None):
    """Create object on S3 'object_path'."""
    object = _get_bucket_object(object_path)
    if object:
        try:
            if data: # file
                request = object.put(Body=data)
            else: # directory
                request = object.put()    
        except Exception as e:
            print_error(str(e))
            print_error("[MK_S3_OBJECT]")
        else:
            return request['ResponseMetadata']['HTTPStatusCode'] == 200

def maps_load_from_ini():
    """load maps from path in configuration file."""
    s3_path = CONFIG[mode_name()].get("maps_s3_path")
    if s3_path:
        maps = maps_load_from_s3_path(s3_path)
        return maps

def maps_load_from_s3_path(s3_path):
    """Load maps from 's3_path' and Return list of xmap."""
    maps = []
    # support for single files
    if s3_path.endswith(".json"):
        s3_path, objects = slipt_s3path(s3_path)
        objects = (objects,)
    else:
        objects = ( obj for obj in ls_s3_path(s3_path) if obj.endswith(".json") )
    for object in objects:
        file = get_s3_file("/".join([s3_path, object]))
        if file:
            xmap = json.loads(file.decode('utf8'))
            for m in xmap:
                m['filename'] = object
                for prop in ["master","s3", "slave"]:
                    if m.get(prop):
                        m[prop] = normalize_external_path(m[prop])

            try:
                maps_validate(xmap)
            except Exception as e:
                print_error(str(e))
                print_error("[MAPS_LOAD_FROM_S3_PATH]")
            else:
                maps += xmap

    # sort must be after validate to keep user debug most efficent.
    if maps and CONFIG['MAIN'].getboolean('order_maps'):
        maps = sorted(maps, key=lambda k:k['name'])
    return maps

def maps_path_validate(path):
    """check common error of map 'path"""
    if path[0] == "~":
        return TXT_ERR_MAP_SUB_USERHOME

def maps_validate(maps):
    """raise excepition if maps error."""
    if len(maps) == 0:
        raise Exception(TXT_ERR_MAP_EMPTY) 
    for n, e in enumerate(maps):
        name = e.get("name")
        s3_path = e.get("s3")
        master_path = e.get("master")
        slave_path = e.get("slave")
        if not name:
            err = TXT_ERR_MAP_SUB_EMPTY_PROPERTY.format(property='name')
            raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=n, error=err))
        if not s3_path:
            err = TXT_ERR_MAP_SUB_EMPTY_PROPERTY.format(property='s3')
            raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=name, error=err))
        if ISMASTER:
            if not master_path:
                err = TXT_ERR_MAP_SUB_EMPTY_PROPERTY.format(property='master')
                raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=name, error=err))
            err = maps_path_validate(master_path)
            if err:
               raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=name, error=err))
        else:
            if not slave_path :
                err = TXT_ERR_MAP_SUB_EMPTY_PROPERTY.format(property='slave')
                raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=name, error=err))
            err = maps_path_validate(slave_path)
            if err :
                if err: raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=name, error=err))

def ismaster_load_from_ini():
    """Set global var ISMASTER from configuration file."""
    try:
        # can return None in ismaster not Exists
        # can return error if th value is not valid boolena string
        ismaster = CONFIG['MAIN'].getboolean('ismaster')
    except:
        ismaster = None
    return ismaster

def ignore_rules(rules, jolly="*"):
    """ Load rules and create test function to verify
    if a string match a rule of exclusion.

    Return a function that check if string match 'rules'

    Parameters:
        rules
            List of string with jolly char
            Examples: ["*.bmp", ".*", "*__pychache__*", "filename.ext"]

        jolly
            jolly char    
    """
    if rules:
        s = []
        e = []
        c = []
        m = []
        for rule in rules:
            r = rule.strip()
            endsw = r[0] == jolly
            startsw = r[-1] == jolly
            if startsw and endsw:
                c.append(r[1:-1])
            elif startsw:
                s.append(r[:-1])
            elif endsw:
                e.append(r[1:])
            else:
                m.append(r)
        test = ((c , lambda s1, s2: s1.find(s2) > -1),
            (s , lambda s1, s2: s1.startswith(s2)),
            (e , lambda s1, s2: s1.endswith(s2)),
            (m , lambda s1, s2: s1 == s2))

    def _ignore(string):
        """Return true if 'string' match with test rules."""
        nonlocal test, rules, s, e, c, m
        if not rules : return
        for t in test:
            for r in t[0]:
                if t[1](string,r):
                    return 1
    return _ignore

def create_obj_xmap_mode(xmap):
    """Return dict with information 
    about master and slave / origin and destination
    """
    datamap = {
        'name' : xmap.get('name'),
        'filename' : xmap.get('filename'),
        'description' : xmap.get('description', ""),
        'ignore' : xmap.get('ignore', "Any"),
        'files' : xmap.get('files', "All"),
    }
    s3 = {
        'name' : 'REMOTE S3',
        'path' : xmap.get('s3')
    }
    if ISMASTER:
        origin = {
            'name' : 'LOCAL (master)',
            'path' : xmap.get('master')
            }
        destination = s3
    else:
        origin = s3
        destination = {
            'name' : 'LOCAL (slave)',
            'path' : xmap.get('slave')
            }
    return {
        'map' : datamap,
        'origin': origin,
        'destination' :destination
        }

def _init_path_transfer(info):
    """Remove and create main slave path"""
    if CONFIG['MAIN'].getboolean('show_delete_alert'):
        print_warning(TXT_WARNING_TRANSFER.format( storage=info['destination']['name'], path=info['destination']['path'], files="ALL FILES" ))
        confirm = input_text(TXT_INPUT_CONFIRM).lower() == "y"
    else:
        confirm = 1

    if confirm:
        print_title("INITIALIZE ENVIRONMENT")
        print_text(TXT_DELETE_OBJECT.format(storage=info['destination']['name'], object=info['destination']['path']))
        if not rm_slave_object(info['destination']['path'], ignore_error=1):
            # error only if slave is S3 and bucket not exixts
            # if prefix not exists ignore error; it will be created later.
            # user error message came from rm_slave_object, nothing to show
            # here!
            return
        print_text(TXT_CREATE_OBJECT.format(storage=info['destination']['name'], object=info['destination']['path']))
        # need add '/' to 'mk_slave_object' destination because external
        # path don't have
        if not mk_slave_object(info['destination']['path'] + "/"):
            print_warning(TXT_WARNING_EXIT_TASK_WITH_ERROR) # POSSIBILE DUPLICATO 
            return
        return 1

def _init_files_transfer(info):
    if CONFIG['MAIN'].getboolean('show_delete_alert'):
        print_warning(TXT_WARNING_TRANSFER.format(storage=info['destination']['name'], path=info['destination']['path'], files=info['map']['files']))
        return input_text(TXT_INPUT_CONFIRM).lower() == "y"
    else:
        return 1
    
"""
command_NAME function are list of tuple
with ( command_char, label, function to execute )
used to create form_menu.
"""

def command_main(maps):
    if maps:
        map_opt = [
        ("md", TXT_LABEL_CMD_MD, lambda maps=maps: form_maps_details(maps)),
        ("mr", TXT_LABEL_CMD_MR, input_form_maps_reload)            
        ]
    else:
        map_opt = []

    ever_opt = [
      ("mo", TXT_LABEL_CMD_MO, input_form_maps),
      ("sm", TXT_LABEL_CMD_SM, form_switch_mode),
      ("ad", "Advanced", form_advanced),
      ("x", TXT_LABEL_CMD_X, lambda: "x")
      ]
    return map_opt + ever_opt

def command_custom():
    if 'CUSTOMCOMMAND' in CONFIG and len(CONFIG['CUSTOMCOMMAND']) > 0  :
        d = list(CONFIG['CUSTOMCOMMAND'].items())
        return [ ("c" + str(n), c[0], lambda v=c[1]: form_execute_cmd(v)) for n, c in enumerate(d) ]
    return []

def command_transfer(maps): 
    if maps:
        main = [
            (str(n) ,
               str(m['name']).replace("_", " "),
               lambda v=m: form_transfer(v))        
                for n, m in enumerate(maps)
            ]        
        main.append(("all" ,
               TXT_LABEL_CMD_ALL,
               lambda maps=maps: form_transfer_all(maps)))    
        return main
    return []

def command_advanced():
    cmd = []
    hide_option_name = ["ismaster", "time_sleep_after_rm" ]
    list_option = [ x for x in CONFIG_MAIN_OPTIONS if x[0] not in hide_option_name ]

    print_title(TXT_LABEl_CONFIGURATION)
    for n, v in enumerate( list_option ) :
        option, label, default = v
        current_value = CONFIG['MAIN'].getboolean(option)
        execmd = lambda n=option: config_switch_main_bool(n)
        is_default = default == current_value
        if is_default:
            str_status = bcolors.OKGREEN + "[" + str(current_value) + "] [" + TXT_DEFAULT_VALUE + "]"
        else:
            str_status = bcolors.WARNING + "[" + str(current_value) + "]"
        str_status += bcolors.ENDC

        label += " * " + TXT_CURRENT_STATUS.format(status=str_status)

        cmd.append(("s" + str(n), label, execmd))

    cmd.append(("x", "Exit", lambda: "x"))
    return cmd

"""
input_NAME are user forms that return a value
"""

def input_form_maps_s3_path():
    """Ask user the s3 path of mapping files

    Return string or None
    """
    i = ""
    while i == "":
        clear()
        msg = TXT_INPUT_INSERT_MAPS_PATH_EXIT
        #msg = TXT_INPUT_INSERT_MAPS_PATH
        i = input_text(msg.format(mode=mode_name()))
        if i.lower() == "x":
            return
        i = normalize_external_path(i)
    return i

def input_form_mode():
    """Form to ask user the programm mode (MASTER/SLAVE).

    Return String
        - "1"
            if usere selected MASTER
        - "0"
            if usere selected SLAVE

    """
    option = ("1", "0")
    i = None
    while i not in option:
        clear()
        print_title(TXT_LABEL_SELECT_MODE)
        for op in option:
            n = int(op)
            print_text("{i} = {name} : {desc}", i=n, name=mode_name(n), desc=mode_action(n))
        i = input_text(TXT_INPUT_OPTION.format(option=option))
    return i

def input_form_maps():
    maps = []
    map_s3_path = input_form_maps_s3_path()
    if map_s3_path:
        maps = maps_load_from_s3_path(map_s3_path)
        if maps:
            CONFIG[mode_name()]['maps_s3_path'] = map_s3_path
            config_save()
            form_maps_details(maps)
        else:
            print_error(TXT_ERR_MAPS_NOT_FOUND)
    return maps

def input_form_maps_reload():
    maps = maps_load_from_ini()
    if maps:
        print_success(TXT_MAPS_RELOAD_OK)
        form_maps_details(maps)
    else:
        print_error(TXT_ERR_MAPS_RELOAD_KO)
    return maps

"""
form_NAME functions are user form show and/or execute task.
Must be return 0 to continue without reload main()'.
Must be return 1 to reload main().
"""
def form_advanced():
    i = None
    while i != "x":
        clear()
        cmd_adv = command_advanced()
        for cmd, label, fun in cmd_adv:
            print_text("{cmd:>3} = {label}".format(cmd=cmd , label=label))

        i = input_text(TXT_INPUT).lower()
        for cmd, label, fun in cmd_adv:
            if i == cmd:
                fun()

def form_execute_cmd(cmd):
    """Execute custom command"""
    try:
        subprocess.check_call(cmd.split())
    except Exception as e:
        print_error(str(e))
        print_error("[FORM_EXECUTE_CMD]")

def form_switch_mode():
    """Switch program mode from MASTER and SLAVE and restart."""
    global ISMASTER
    ISMASTER = not ISMASTER
    CONFIG['MAIN']['ismaster'] = str(ISMASTER)
    print_success(TXT_SWITH_CONFIRM.format(mode_name=mode_name()))
    config_save()
    return 1 # return 1 to force reload main()

def form_transfer_all(maps):
    count_xmap = len(maps)
    x = 0
    valid_tranfer = 0
    for xmap in range(count_xmap):
        x+=1
        clear()
        print_header(TXT_TRANFER_ALL_HEADER.format(current=x,total=count_xmap))
        valid_tranfer += form_transfer(maps[xmap], as_subform=1)
        if CONFIG['MAIN'].getboolean('show_transfer_detail'):
            enter_to_continue()
    else:
        clear()
        if valid_tranfer == count_xmap:
            print_success(TXT_ALL_TRANSFER_COMPLETE.format(count="ALL"))
        else:
            str_count = "{}/{}".format(valid_tranfer,count_xmap)
            print_warning(TXT_ALL_TRANSFER_COMPLETE.format(count=str_count))

def form_transfer(xmap, as_subform=0):
    """Transfer data from master to slave
    using information path stored in 'xmap'.
    """
    initialize = 0
    info = create_obj_xmap_mode(xmap)

    print_text(TXT_TRANSFER_INFO.format(**info))

     # not use info[] for 'ignore' and 'files' becasuse in info[] are string
    origin = info['origin']['path'] 
    destination = info['destination']['path']
    ignore_test = ignore_rules(xmap.get("ignore"))
    objects = xmap.get('files')
    is_path_transfer = not objects
    if not exists_master_path(info['origin']['path']):
        print_error(TXT_ERR_MASTER_OBJECT_NOT_EXISTS.format(storage=info['origin']['name'],path = info['origin']['path']))
        objects = ()

    elif is_path_transfer: 
        # get all objects in master path
        objects = ls_master_path(origin)
    else:
        # if not 'is_master_path'
        # check existence of all files specified in xmap['files']
        all_exists = True
        for file in ( "/".join([info['origin']['path'], obj]) for obj in objects):
            if not exists_master_file(file):
                print_error(TXT_ERR_MASTER_OBJECT_NOT_EXISTS.format(storage=info['origin']['name'], path=file))
                all_exists = False
        if not all_exists:
            # remove all objects, stop transfer
            objects = iter(())

    for obj in objects:
        # Objects for cicle on s3 master return error message and iter(())
        # if bucket name is wrong!
        #
        # Objects is generator, don't give error until first access
        # for this reason
        # '_init_fun' is inside the loop:
        # is useful to NOT delete local slave folder
        # if bucket objects not exists!
        obj_data = None if obj.endswith("/") else get_master_file("/".join([origin, obj]))
        obj_fullpath = "/".join([destination, obj])
        if not initialize:
            initialize = 1
            _init_fun = _init_path_transfer if is_path_transfer else _init_files_transfer
            if not _init_fun(info):
                break  # objects transfer
        if ignore_test(obj):
            print_blue(TXT_TRANSFER_IGNORE.format(storage=info['destination']['name'], object=obj))
        else:
            print_text(TXT_SAVE_OBJECT.format(storage=info['destination']['name'],root=info['destination']['path'], object=obj))
            if not mk_slave_object(obj_fullpath, obj_data):
                break # objects transfer
    else: # and complete cicle of for obj in objects
        if initialize:
            if CONFIG['MAIN'].getboolean('show_transfer_detail'):
                print_success(TXT_TRANSFER_COMPLETE)
            if as_subform:
                return 1
            else:
                return

        #if initialize == 1 and not CONFIG['MAIN'].getboolean('show_transfer_detail'):

        #    print_success(TXT_TRANSFER_COMPLETE)
        #    input("................")
        #    if as_subform:
        #        return 1
        #    else:
        #        return

    # here if cicle inclomplete or not 'initializate' == 0
    print_warning(TXT_WARNING_EXIT_TASK_WITH_ERROR)
    if as_subform:
        return 0
    # else return None


def form_maps_details(maps):
    """Show to user loaded maps details."""
    print_header(TXT_MAPS_DETAILS.format(path=CONFIG[mode_name()]["maps_s3_path"]))
    for xmap in maps:
        info = create_obj_xmap_mode(xmap)
        print_text(TXT_TRANSFER_INFO.format(**info))

def main():
    """Main function"""
    global ISMASTER

    clear()

    if new_version_available():
        print_blue(TXT_NEW_SCRIPT_VERSION_AVAILABLE)
        if input_text(TXT_INPUT_CONFIRM).lower() == "y":
            clear()
            update_routine()
            enter_to_continue()
            return # exit main ...

    print_blue(TXT_LOADING.format(what='configuration'))

    if not CONFIG.read(CONFIG_FILENAME):
        config_load_default()
    else:
        config_validate()

    print_blue(TXT_LOADING.format(what='mode'))

    ISMASTER = ismaster_load_from_ini()
    if ISMASTER is None:
        # NOTE input_form_mode return always a valid value
        # and values is a string "0"=slave or "1"= master
        ISMASTER = input_form_mode()
        CONFIG['MAIN']['ismaster'] = ISMASTER
        config_save()
        ISMASTER = int(i)


    print_blue(TXT_LOADING.format(what='maps'))

    maps = maps_load_from_ini()

    cmd_m = command_main(maps)
    cmd_t = command_transfer(maps)
    cmd_c = command_custom()
    cmd_all = [ (cmd, label, fun) for cmd, label, fun in cmd_c + cmd_m + cmd_t ]

    exit_form = False
    while not exit_form:
        clear()
        print_header(TXT_MODE_INFO.format(mode=mode_name(),mapspath=CONFIG[mode_name()].get("maps_s3_path")))
        for label, cmds in [(TXT_LABEL_MAIN_COMMAND, cmd_m) ,(TXT_LABEL_CUSTOM_COMMAND, cmd_c), (mode_action(), cmd_t)]:
            if cmds:
                print_title(label)
                for cmd, label, fun in cmds:
                    print_text("{cmd:>3} = {label}".format(cmd=cmd , label=label))
        if len(cmd_t) == 0:
            print_warning(TXT_WARNING_MAPS_NOT_LOADED.format(mode=mode_name()))
            print_blue(TXT_MAPS_HELP_INFO.format(link=URL_DOC))
        i = input_text(TXT_INPUT).lower()

        for cmd, label, fun in cmd_all:
            if i == cmd:
                clear()
                # all fun called must be
                # return False and i != "x" to show form_menu() again
                exit_form = fun()
                enter_to_continue()

    if i != "x": # 'x' is the input to exit from application in menu.
        # reload self
        main()

if __name__ == "__main__":
    main()