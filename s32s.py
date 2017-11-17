#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import configparser
import shutil
import json
import subprocess
import urllib.request
import errno
import botocore.exceptions
from time import sleep
import boto3

__version__ = "1.3"
os.sep = "/"
S3RESOURCE = boto3.resource('s3')
CONFIG = configparser.ConfigParser()
CONFIG_FILENAME = 's32s.ini'
URL_SCRIPT = "https://raw.githubusercontent.com/Amecom/S32S/master/s32s.py"
URL_GET_VERSION = "https://raw.githubusercontent.com/Amecom/S32S/master/VERSION"
ISMASTER = None
MAPS = None

"""
LABEL
"""

TXT_TRANSFER_INFO = """
 {map[name]} - from file: {map[filename]}
 {map[description]}

    TRANSFER INFORMATION
    * FROM {origin[name]} : '{origin[path]}'
   >> TO {destination[name]} : '{destination[path]}'

    Files  : {map[files]}
    Ignore : {map[ignore]}
"""
TXT_DELETE_WARNING = """
  ********* WARNING  ********* 

  ALL OBJECTS stored in

  {storage}: '{path}'

  Will be PERMANENTLY DELETE.

 ***************************** 
"""
TXT_TRANSFER_FILES_WARNING = """
  ********* WARNING  ********* 

  THIS FILES '{files}' stored in

  {storage}: '{path}'

  Will be REPLACED.

 ***************************** 
"""

TXT_MAPS_RELOAD_OK = " Maps Reloaded."
TXT_MAPS_RELOAD_KO = " Erron on Maps Reloaded."

TXT_MAPS_DETAILS = " Maps Details '{path}':"
TXT_LABEL_SELECT_MODE = " Select mode"
TXT_LABEL_CMD_MD = "Maps Details"
TXT_LABEL_CMD_MR = "Maps Reload"
TXT_LABEL_CMD_MO = "Maps Open"
TXT_LABEL_CMD_SM = "Switch Mode"
TXT_LABEL_CMD_X = "Exit"
TXT_LABEL_CMD_ALL = "Transfer all"
TXT_LABEL_MAIN_COMMAND = "Main command"
TXT_LABEL_CUSTOM_COMMAND = "Custom command"
TXT_LABEL_TRANFER_LIST = "Transfer command"
TXT_NEW_SCRIPT_VERSION_AVAILABLE = " New version of script is available.\n Enter 'y' to upgrade, anything else to skip."
TXT_SCRIPT_UPDATED = " New Script has been downloaded. Old script still exists renamed {old_name}."
TXT_RESTART = " Restart script."
TXT_MODE_INFO = "*** {mode} MODE *** S3 Maps Path loaded: '{mapspath}'"
TXT_EXECUTE_CMD = " EXECUTE: {cmd}"
TXT_ACTION_MASTER = "Replace s3 object with local ones"
TXT_ACTION_SLAVE = "Replace local objects with those stored in S3"
TXT_TRANSFER_COMPLETE = "* TRANSFER COMPLETE"
TXT_LOADING = " Loading '{what}'... "
TXT_DELETE_OBJECT = " {storage} DELETE: {object}"
TXT_CREATE_OBJECT = " {storage} CREATE: {object}"
TXT_SAVE_OBJECT = " {storage} SAVE IN '{root}' OBJECT: '{object}'"
TXT_TRANSFER_IGNORE = " \t{storage} IGNORE: {object}"
TXT_INPUT = "\n > Enter command: "
TXT_INPUT_OPTION = "\n > Enter input {option}: "
TXT_INPUT_ENTER = "\n > Press ENTER to continue..."
TXT_INPUT_INSERT_MAPS_PATH = "\n > Insert S3 path contains maps files for '{mode}': "
TXT_INPUT_INSERT_MAPS_PATH_EXIT = "\n > Insert S3 path contains maps files for '{mode}' [x to Exit]: "
TXT_INPUT_TRANSFER_CONFIRM = "\n > Enter 'y' to confirm, anything else to cancel transfer: " 
TXT_WARNING_EXIT_TASK_WITH_ERROR = "!! WARNING Task not completed."
TXT_ERR_MASTER_OBJECT_NOT_EXISTS = " !! ERROR Path object '{path}' not exists in '{storage}'."
TXT_ERR_S3_CONNECTION_ERROR = "\n !! ERROR S3 Could not connect. Verify your internet connection and try again."
TXT_ERR_S3_BUCKET_LOAD = "\n !! ERROR S3 Bucket '{bucket_name}' NOT FOUND"
TXT_ERR_S3_LIST_CONNECTION = "\n !! ERROR S3 PATH '{path}': bucket not found or access denied or no internet access."
TXT_ERR_S3_LIST_CONTENTS = "\n !! ERROR S3 PATH '{path}': path does not have a contents or not exists."
TXT_ERR_SCRIPT_UPDATE_CONFIG = "\n !! ERROR not found 'url_script_update' property in configuration file."
TXT_ERR_MAPS_NOT_FOUND = "\n !! ERROR MAPS NOT FOUND OR INVALID"
TXT_ERR_MAP_EMPTY = "\n !! ERROR EMPTY MAPS"
TXT_ERR_MAP = "!! ERROR Filename: '{filename}' Maps Element: '{element_id}': {error}"
TXT_ERR_MAP_SUB_USERHOME = " Path can't start with ~"
TXT_ERR_MAP_SUB_EMPTY_PROPERTY = "'{property}' property is mandatory.'" 

def mode_name(ismaster):
    """Return string that describes mode used in config."""
    return "MASTER" if ismaster else "SLAVE"

def mode_action(ismaster=None):
    """Return string that describes transfert mode."""
    if not ismaster : ismaster = ISMASTER
    return  TXT_ACTION_MASTER if ismaster else TXT_ACTION_SLAVE

def enter_to_continue():
    """Create a break to allow the user to read output."""
    input(TXT_INPUT_ENTER)

def clear():
    """Clear Screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def ini_validate():
    save = 0
    if 'MAIN' not in CONFIG:
        ini_load_default()

    # test_bool use element position to set default option
    # element in test_bool[0] have false default 
    # element in test_bool[1] have true default 
    test_bool = (
        ("skip_order_maps", "skip_delete_alert", "skip_tranfer_detail"), # DEFAULT FALSE
        ("ismaster",)  # DEFAULT TRUE
        ) 
    for v, block in enumerate(test_bool):
        for var in block:
            try:
                CONFIG['MAIN'].getboolean(var)
            except ValueError:
                CONFIG['MAIN'][var] = str(v)
                save = 1

    try:
        CONFIG['MAIN'].getint('time_sleep_after_rm')
    except ValueError:
        CONFIG['MAIN']['time_sleep_after_rm'] = "3"
        save = 1
    if save:
        config_save()

def ini_load_default():
    """return default configuration."""
    mode_conf = {
        'maps_s3_path': ''
        }
    CONFIG['MAIN'] = {
        'ismaster': '',
        'skip_delete_alert': 0,
        'skip_order_maps': 0,
        'skip_tranfer_detail' : 0,
        'time_sleep_after_rm': 3
        }
    CONFIG[mode_name(1)] = mode_conf
    CONFIG[mode_name(0)] = mode_conf
    CONFIG['CUSTOMCOMMAND'] = {}

def config_save():
    """Save configuration change."""
    with open(CONFIG_FILENAME, 'w') as configfile:
        CONFIG.write(configfile)

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
    print(TXT_SCRIPT_UPDATED.format(old_name=rename_old))
    print(TXT_RESTART)
    enter_to_continue()
    return 1

def normalize_external_path(path):
    """Return normalized version of 'path'.
    
    MUST be used only for external path
    as .ini, user input, maps.

    Remove '/' at ends of path
    replace sep '\' with '/'
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
    bucket = S3RESOURCE.Bucket(bucket_name)
    err = None
    try:
        bucket.load()
    except botocore.exceptions.EndpointConnectionError:
        err = TXT_ERR_S3_CONNECTION_ERROR
    except botocore.exceptions.ClientError:
        err = TXT_ERR_S3_BUCKET_LOAD.format(bucket_name=bucket_name)
    if not err:
        return bucket
    else:
        print(err)
        enter_to_continue()

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
            name_b = "/".join( [bucket_name, objects[0].key ] )
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
    if bucket == None:
        return
    try:
        request = bucket.objects.filter(Prefix=prefix).delete()
    except Exception as e:
        if not ignore_error:
            print(e)
            return
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
            print(e)
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
            print(e, "[mk_s3_object]")
            enter_to_continue()
        else:
            return request['ResponseMetadata']['HTTPStatusCode'] == 200

def maps_load_from_ini():
    """Set global var MAPS from configuration file."""
    s3_path = CONFIG[mode_name(ISMASTER)].get("maps_s3_path")
    if s3_path:
        maps = maps_load_from_s3_path(s3_path)
        return maps

def maps_reload():
    global MAPS
    maps = maps_load_from_ini()
    if maps:
        MAPS = maps
        return 1

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

def maps_load_from_s3_path(s3_path):
    """Load maps from 's3_path'.

    Return list of xmap
    """
    maps = []
    # support for single files
    if s3_path.endswith(".json"):
        s3_path, objects = slipt_s3path(s3_path)
        objects = (objects,)
    else:
        objects = ( obj for obj in ls_s3_path(s3_path) if obj.endswith(".json") )
    for object in objects:
        file = get_s3_file("/".join([s3_path, object]))
        xmap = json.loads(file.decode('utf8'))
        for m in xmap:
            m['filename'] = object
            for prop in ["master","s3", "slave"]:
                if m.get(prop):
                    m[prop] = normalize_external_path(m[prop])

        try:
            maps_validate(xmap)
        except Exception as e:
            print(e, " [maps_load_from_s3_path]")
            enter_to_continue()
        else:
            maps += xmap
    # sort must be after validate to keep user debug most efficent.
    if maps and not CONFIG['MAIN'].getboolean('skip_order_maps'):
        maps = sorted(maps, key=lambda k:k['name'])
    return maps


def execute_cmd(cmd):
    """Execute custom command"""
    try:
        subprocess.check_call(cmd.split())
    except Exception as e:
        print(cmd)
        print(e)
    enter_to_continue()
    return 1 # always need return True
def transfer_all():
    for xmap in range(len(MAPS)):
        form_transfer(MAPS[xmap])
    return 1

def switch_mode():
    """Switch program mode from MASTER and SLAVE and restart."""
    CONFIG['MAIN']['ismaster'] = str(not ISMASTER)
    config_save()
    main()
    # return 0 to force exit to previous form_menu()
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
    """Return a object with information 
    about master ans slave origin and destination
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

"""
command_NAME function are list of tuple
with ( command_char, label, function to execute )
used to create form_menu.
"""

def command_main():
    return [("md", TXT_LABEL_CMD_MD, form_maps_details),
      ("mr", TXT_LABEL_CMD_MR, form_maps_reload),
      ("mo", TXT_LABEL_CMD_MO, input_form_global_MAPS),
      ("sm", TXT_LABEL_CMD_SM, switch_mode),
      ("x", TXT_LABEL_CMD_X, lambda: False)]

def command_custom():
    if 'CUSTOMCOMMAND' in CONFIG and len(CONFIG['CUSTOMCOMMAND']) > 0  :
        d = list(CONFIG['CUSTOMCOMMAND'].items())
        return [ ("c" + str(n), c[0], lambda v=c[1]: execute_cmd(v)) for n, c in enumerate(d) ]
    return []

def command_transfer(): 
    if MAPS:
        main = [
            (str(n) ,
               str(m['name']).replace("_", " "),
               lambda v=m: form_transfer(v))        
                for n, m in enumerate(MAPS)
            ]        
        main.append(("all" ,
               TXT_LABEL_CMD_ALL,
               transfer_all))    
        return main
    return []

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
        if MAPS:
            msg = TXT_INPUT_INSERT_MAPS_PATH_EXIT
        else:
            msg = TXT_INPUT_INSERT_MAPS_PATH
        i = input(msg.format(mode=mode_name(ISMASTER)))
        if i.lower() == "x":
            return
        i = normalize_external_path(i)
    clear()
    return i

def input_form_global_ISMASTER():
    """Form to ask user the programm mode (MASTER/SLAVE).

    Return
        - True
            if usere selected MASTER
        - False
            if usere selected SLAVE

    """
    global ISMASTER
    # option value for master mast be "1"!
    clear()
    option = ("1", "0")
    i = None
    while i not in option:
        clear()
        print(TXT_LABEL_SELECT_MODE + ":\n")
        for op in option:
            n = int(op)
            print("\t{i} = {name} : {desc}".format(i=n, name=mode_name(n), desc=mode_action(n)))
        i = input(TXT_INPUT_OPTION.format(option=option))

    ISMASTER = int(i)
    CONFIG['MAIN']['ismaster'] = i
    config_save()
    return 1

def input_form_global_MAPS():
    clear()
    global MAPS
    map_s3_path = input_form_maps_s3_path()
    if map_s3_path:
        maps = maps_load_from_s3_path(map_s3_path)
        if maps:
            MAPS = maps
            CONFIG[mode_name(ISMASTER)]['maps_s3_path'] = map_s3_path
            config_save()
            form_maps_details()
        else:
            print(TXT_ERR_MAPS_NOT_FOUND)
            enter_to_continue()
    return 1

"""
form_NAME functions are user form show and/or execute task.
Must be return 1 to reopen 'form_main'.
Must be return 0 to close 'form_main'.
"""
    
def form_maps_reload():
    clear()
    if maps_reload():
        print(TXT_MAPS_RELOAD_OK)
        enter_to_continue()
        form_maps_details()
        main()
        return 0 # esc to form_menu

    else:
        print(TXT_MAPS_RELOAD_KO)
        enter_to_continue()
        return 1 # return to form_menu

def _init_path_transfer(info):
    """Remove and create main slave path"""

    if not CONFIG['MAIN'].getboolean('skip_delete_alert'):
        print(TXT_DELETE_WARNING.format(
                storage=info['destination']['name'],
                path = info['destination']['path']
                ))
        confirm = input(TXT_INPUT_TRANSFER_CONFIRM).lower()
    else:
        confirm = "y"

    if confirm == "y":
        print(" INITIALIZE ENVIRONMENT")
        print(TXT_DELETE_OBJECT.format(storage=info['destination']['name'], object=info['destination']['path']))
        if not rm_slave_object(info['destination']['path'], ignore_error=1):
            # error only if slave is S3 and bucket not exixts
            # if prefix not exists ignore error; it will be created later.
            # user error message came from rm_slave_object, nothing to show here!
            return

        print(TXT_CREATE_OBJECT.format(storage=info['destination']['name'], object=info['destination']['path']))
        # need add '/' to 'mk_slave_object' destination because external
        # path don't have
        if not mk_slave_object(info['destination']['path'] + "/"):
            print(TXT_WARNING_EXIT_TASK_WITH_ERROR)
            return
        return 1

def _init_files_transfer(info):
    # nella modalita dove sono specificati i singoli file
    # non è permesso sincronizzare il contenuto di una directory
    #if not delete_main_dir and not obj_data:
        # specified file
        # ~~~~~~~~~~ ADD CHECK THAT ALL objects ARE FILES AND NOT DIR ######
        # ~~~~~~~~~~ ADD CHECK THAT ALL objects ARE FILES AND NOT DIR ######

    if not CONFIG['MAIN'].getboolean('skip_delete_alert'):
        print(TXT_TRANSFER_FILES_WARNING.format(
            storage=info['destination']['name'],
            path=info['destination']['path'],
            files=info['map']['files']))
        return input(TXT_INPUT_TRANSFER_CONFIRM).lower() == "y"
    else:
        return True
    
def form_transfer(xmap):
    """Transfer data from master to slave
    using information path stored in 'xmap'.
    """
    clear()
    info = create_obj_xmap_mode(xmap)
    print(TXT_TRANSFER_INFO.format(**info))


     # not use info[] for 'ignore' and 'files' becasuse in info[] are string
    origin = info['origin']['path'] 
    destination = info['destination']['path']
    ignore_test = ignore_rules(xmap.get("ignore"))
    objects = xmap.get('files')
    is_path_transfer = not objects

    if not exists_master_path(info['origin']['path']):
        print(TXT_ERR_MASTER_OBJECT_NOT_EXISTS.format(
                storage=info['origin']['name'],
                path = info['origin']['path']
                ))
        # enter_to_continue()
        objects = iter(())

    elif is_path_transfer: 
        # !!! if not is_path_transfer, get all objects in origin path.
        objects = ls_master_path(origin)
    else:
        # check existence of all files
        all_exists = True
        for file in ( "/".join([info['origin']['path'], obj] ) for obj in objects):
            if not exists_master_file(file):
                print(TXT_ERR_MASTER_OBJECT_NOT_EXISTS.format(
                        storage=info['origin']['name'],
                        path = file
                        ))
                all_exists = False
        if not all_exists:
            # stop transfer
            # enter_to_continue()
            objects = iter(())


    initialize = 0

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
            print(TXT_TRANSFER_IGNORE.format(storage=info['destination']['name'], object=obj))
        else:
            print(TXT_SAVE_OBJECT.format(storage=info['destination']['name'],root=info['destination']['path'], object=obj))
            if not mk_slave_object(obj_fullpath, obj_data):
                break # objects transfer

    else: # object for else
        if initialize == 1 and not CONFIG['MAIN'].getboolean('skip_tranfer_detail'):
            print("\n " + TXT_TRANSFER_COMPLETE)
            enter_to_continue()
            return 1

    print("\n " + TXT_WARNING_EXIT_TASK_WITH_ERROR)
    enter_to_continue()
    return 1

def form_maps_details():
    """Show to user loaded maps details."""
    clear()
    print(TXT_MAPS_DETAILS.format(path=CONFIG[mode_name(ISMASTER)]["maps_s3_path"]))
    for xmap in MAPS:
        info = create_obj_xmap_mode(xmap)
        print(TXT_TRANSFER_INFO.format(**info))

    enter_to_continue()
    return 1

def form_menu():
    cmd_m = command_main()
    cmd_t = command_transfer()
    cmd_c = command_custom()
    glob = [ (cmd, label, fun) for cmd, label, fun in cmd_c + cmd_m + cmd_t ]

    show_form = True
    while show_form:
        clear()
        print(TXT_MODE_INFO.format(mode=mode_name(ISMASTER),mapspath=CONFIG[mode_name(ISMASTER)].get("maps_s3_path")))
        for label, cmds in [(TXT_LABEL_MAIN_COMMAND, cmd_m) ,(TXT_LABEL_CUSTOM_COMMAND, cmd_c), (TXT_LABEL_TRANFER_LIST, cmd_t)]:
            if cmds:
                print(" \n {}:".format(label))
                for cmd, label, fun in cmds:
                    print(" {cmd:>3} = {label}".format(cmd=cmd , label=label))

        i = input(TXT_INPUT).lower()

        for cmd, label, fun in glob:
            if i == cmd:
                # all fun called must be
                # return True to show form_menu() again
                show_form = fun()

def main():
    """Main function"""
    global ISMASTER
    global MAPS

    clear()

    if new_version_available():
        print(TXT_NEW_SCRIPT_VERSION_AVAILABLE)
        if input(TXT_INPUT).lower() == "y":
            clear()
            update_routine()
            return # EXIT MAIN

    print(TXT_LOADING.format(what='configuration'))
    if not CONFIG.read(CONFIG_FILENAME):
        ini_load_default()
        config_save()
    else:
        ini_validate()

    print(TXT_LOADING.format(what='mode'))

    ISMASTER = ismaster_load_from_ini()
    while ISMASTER is None:
        input_form_global_ISMASTER()

    print(TXT_LOADING.format(what='maps'))
    MAPS = maps_load_from_ini()
    while MAPS is None:
        input_form_global_MAPS()
            
    form_menu()


if __name__ == "__main__":
    main()

