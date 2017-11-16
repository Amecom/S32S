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
    TRANSFER INFORMATION:

    * FROM {origin[name]} : '{origin[path]}'
   >> TO {destination[name]} : '{destination[path]}'

    Files  : {map[files]}
    Ignore : {map[ignore]}
"""
TXT_DELETE_WARNING = """
  ********* WARNING  ********* 

  ALL OBJECTS stored in

  {info}: '{path}'

  Will be PERMANENTLY DELETE.

 ***************************** 
"""
TXT_MENU_MODE = """
Select mode:

    {inp_master} = MASTER - {info_master}
    {inp_slave} = SLAVE - {info_slave}
"""
TXT_LABEL_CMD_MD = "Maps Details"
TXT_LABEL_CMD_MR = "Maps Reload"
TXT_LABEL_CMD_MO = "Maps Open"
TXT_LABEL_CMD_SM = "Switch Mode"
TXT_LABEL_CMD_X = "Exit"
TXT_LABEL_CMD_ALL = "Transfer all"
TXT_LABEL_MAIN_COMMAND = "Main Command"
TXT_LABEL_CUSTOM_COMMAND = "Custom Command"
TXT_LABEL_TRANFER_LIST = "Transfer Command"
TXT_NEW_SCRIPT_VERSION_AVAILABLE = " New version of script is available.\n Enter 'y' to upgrade, anything else to skip."
TXT_SCRIPT_UPDATED = " New Script has been downloaded. Old script still exists renamed {old_name}."
TXT_RESTART = " Restart script."
TXT_MODE_INFO = "*** {mode} MODE *** Loaded S3 Maps Path: '{mapspath}'"
TXT_EXECUTE_CMD = " EXCUTE: {cmd}"
TXT_ACTION_MASTER = "Replace s3 object with local ones"
TXT_ACTION_SLAVE = "Replace local objects with those stored in S3"
TXT_NOTDO = " Nothing done!"
TXT_DO = " Done!"
TXT_LOADING = " Loading '{what}'... "
TXT_DELETE_OBJECT = " {storage} DELETE: {object}"
TXT_CREATE_OBJECT = " {storage} CREATE: {object}"
TXT_SAVE_OBJECT = " {storage} SAVE IN '{root}' OBJECT: '{object}'"
TXT_TRANSFER_IGNORE = " \t{storage} IGNORE: {object}"
TXT_INPUT = "\n > Enter command: "
TXT_INPUT_OPTION = "\n > Enter input {option}: "
TXT_INPUT_ENTER = "\n > Press ENTER to continue..."
TXT_INPUT_INSERT_MAPS_PATH = "\n > Insert S3 path contains mapping files for '{mode}' [x to Exit]: "
TXT_INPUT_DELETE_CONFIRM = "\n > Enter 'y' to confirm delete, anything else to cancel transfer: " 
TXT_WARNING_EXIT_TASK_WITH_ERROR = "\n !! WARNING Task not completed."
TXT_ERROR_MASTER_PATH_NOT_ERROR = "\n !! ERROR Master directory {dir_name} not found or empty."
TXT_ERR_S3_CONNECTION_ERROR = "\n !! ERROR S3 Could not connect. Verify your internet connection and try again."
TXT_ERR_S3_BUCKET_LOAD = "\n !! ERROR S3 Bucket '{bucket_name}' NOT FOUND"
TXT_ERR_S3_LIST_CONNECTION = "\n !! ERROR S3 PATH '{path}': bucket not found or access denied or no internet access."
TXT_ERR_S3_LIST_CONTENTS = "\n !! ERROR S3 PATH '{path}': path does not have a contents or not exists."
TXT_ERR_SCRIPT_UPDATE_CONFIG = "\n !! ERROR not found 'url_script_update' property in configuration file."
TXT_ERR_MAPS_NOT_FOUND = "\n !! ERROR MAPS NOT FOUND IN '{path}'"
TXT_ERR_MAP_EMPTY = "\n !! ERROR EMPTY MAPS"
TXT_ERR_MAP = "!! ERROR MAP filename:'{filename}' element:'{element_id}': {error}"
TXT_ERR_MAP_SUB_USERHOME = " Path can't start with ~"
TXT_ERR_MAP_SUB_EMPTY_PROPERTY = "in this configuration property '{}' is mandatory'" 

def mode_name(ismaster):
    """Return string name used, for examples, in config."""
    return "MASTER" if ismaster else "SLAVE"

def str_action(ismaster=None):
    """Return string that describes transfert mode."""
    if not ismaster : ismaster = ISMASTER
    return  TXT_ACTION_MASTER if ismaster else TXT_ACTION_SLAVE

def enter_to_continue():
    """Create a break to allow the user to read output."""
    input(TXT_INPUT_ENTER)

def clear():
    """Clear Screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def validate_config():
    save = 0
    for var in ("skip_order_maps", "skip_delete_alert", "skip_tranfer_detail"):
        try:
            CONFIG['MAIN'].getboolean(var)
        except:
            CONFIG['MAIN'][var] = 0
            save = 1
    try:
        int(CONFIG['MAIN']['time_sleep_after_rm'])
    except:
        CONFIG['MAIN']['time_sleep_after_rm'] = 3
        save = 1
    if save: save_config()

def load_default_config():
    """return default configuration."""
    CONFIG['MAIN'] = {
        'skip_order_maps': 0,
        'skip_delete_alert': 0,
        'skip_tranfer_detail' : 0,
        'time_sleep_after_rm': 3,
        'ismaster': ''
        }
    CONFIG[mode_name(1)] = {
        'maps_s3_path': ''
        }
    CONFIG[mode_name(0)] = {
        'maps_s3_path': ''
        }
    CONFIG['CUSTOMCOMMAND'] = {}

def save_config():
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
    
    REMOVE '/' AT ENDS OF PATH
    REPLACE SEP '\' WITH '/'
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
        err = TXT_ERR_S3_BUCKET_LOAD.format(bucket_name=bucket)
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
        # NON CI SONO ECCEZIONI FIO A QUI,
        # MA CI SONO DOPO SE IL BUCKET NON ESISTE
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
            print(e)
            enter_to_continue()
        else:
            return request['ResponseMetadata']['HTTPStatusCode'] == 200

def load_maps_from_s3_path(s3_path):
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
            validate_maps(xmap)
        except Exception as e:
            print(e, "load_maps_from_s3_path")
            enter_to_continue()
        else:
            maps += xmap
    # sort must be after validate to keep user debug most efficent.
    if maps and not CONFIG['MAIN'].getboolean('skip_order_maps'):
        maps = sorted(maps, key=lambda k:k['name'])
    return maps

def validate_maps(maps):
    """raise excepition if maps error."""

    def _check_path_error(path):
        """check common error of 'path"""
        if path[0] == "~":
            return TXT_ERR_MAP_SUB_USERHOME

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
            err = _check_path_error(master_path)
            if err:
               raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=name, error=err))
        else:
            if not slave_path :
                err = TXT_ERR_MAP_SUB_EMPTY_PROPERTY.format(property='slave')
                raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=name, error=err))
            err = _check_path_error(slave_path)
            if err :
                if err: raise Exception(TXT_ERR_MAP.format(filename=e['filename'],element_id=name, error=err))

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
    save_config()
    main()
    # return 0 to force exit to previous form_menu()

def config_ISMASTER():
    global ISMASTER
    ISMASTER = None
    while ISMASTER is None:
        ISMASTER = input_form_ismaster()
    CONFIG['MAIN']['ismaster'] = str(ISMASTER)
    save_config()

def config_MAPS():
    global MAPS
    map_s3_path = input_form_maps_s3_path()
    if map_s3_path:
        maps = load_maps_from_s3_path(map_s3_path)
        if maps:
            MAPS = maps
            CONFIG[mode_name(ISMASTER)]['maps_s3_path'] = map_s3_path
            save_config()
        else:
            print(TXT_ERR_MAPS_NOT_FOUND.format(path=map_s3_path))
            enter_to_continue()
    return 1 # to reopen form_menu

def get_ISMASTER():
    """Set global var ISMASTER from configuration file."""
    global ISMASTER
    try:
        # can return None in ismaster not Exists
        # can return error if th value is not valid boolena string
        ISMASTER = CONFIG['MAIN'].getboolean('ismaster')
    except:
        ISMASTER = None

def get_MAPS():
    """Set global var MAPS from configuration file."""
    global MAPS
    s3_path = CONFIG[mode_name(ISMASTER)].get("maps_s3_path")
    if s3_path:
        MAPS = load_maps_from_s3_path(s3_path)

def reload_MAPS():
    maps = get_MAPS()
    if maps :
        MAPS = maps
    return 1

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
        test = ((c , lambda obj, rules: obj.find(rules) > -1),
            (s , lambda obj, rules: obj.startswith(rules)),
            (e , lambda obj, rules: obj.endswith(rules)),
            (m , lambda obj, rules: obj == rules))

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
        'ignore' : xmap.get('ignore', "None"),
        'files' : xmap.get('files', "ALL"),
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
      ("mr", TXT_LABEL_CMD_MR, reload_MAPS),
      ("mo", TXT_LABEL_CMD_MO, config_MAPS),
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
        i = input(TXT_INPUT_INSERT_MAPS_PATH.format(mode=mode_name(ISMASTER)))
        if i.lower() == "x":
            return
        i = normalize_external_path(i)
    clear()
    return i

def input_form_ismaster():
    """Form to ask user the programm mode (MASTER/SLAVE).

    Return
        - True
            if usere selected MASTER
        - False
            if usere selected SLAVE

    """
    # option value for master mast be "1"!
    clear()
    option = ("1", "0")
    i = None
    while i not in option:
        clear()
        print(TXT_MENU_MODE.format(inp_master=option[0],
                info_master=str_action(1), 
                inp_slave=option[1],
                info_slave=str_action(0)))
        i = input(TXT_INPUT_OPTION.format(option=option))

    clear()
    return bool(int(i))

"""
form_NAME functions are user form show or execute task
This form must be return True to return at form_main
and return False to close form_main.
"""

def form_transfer(xmap):
    """Transfer data from master to slave
    using information path stored in 'xmap'.
    """
    def _create_slave_environment():
        """Remove and create main slave path"""
        nonlocal info
        nonlocal destination
        if not CONFIG['MAIN'].getboolean('skip_delete_alert'):
            print(TXT_DELETE_WARNING.format(info = info['destination']['name'],
                    path = destination))
            confirm = input(TXT_INPUT_DELETE_CONFIRM).lower()
        else:
            confirm = "y"

        if confirm == "y":
            print(" INITIALIZE ENVIRONMENT")
            print(TXT_DELETE_OBJECT.format(storage=info['destination']['name'], object=info['destination']['path']))
            if not rm_slave_object(destination, ignore_error=1):
                # error only if slave is S3 and bucket not exixts
                # if prefix not exists ignore errror; it will be created later.
                print(TXT_ERROR_MASTER_PATH_NOT_ERROR.format(dir_name=origin))
                return

            print(TXT_CREATE_OBJECT.format(storage=info['destination']['name'], object=info['destination']['path']))
            # need add '/' to 'mk_slave_object' destination because external
            # path don't have
            if not mk_slave_object(destination + "/"):
                print(TXT_WARNING_EXIT_TASK_WITH_ERROR)
                return
            return 1

    info = create_obj_xmap_mode(xmap)
     # not use info[] for 'ignore' and 'files' becasuse in info[] are string
    origin = info['origin']['path'] 
    destination = info['destination']['path']
    ignore_test = ignore_rules(xmap.get("ignore"))
    objects = xmap.get('files')


    # if not objects, get all objects in origin path.
    if objects: 
        # specified file
        # ~~~~~~~~~~ ADD CHECK THAT ALL objects ARE FILES AND NOT DIR ######
        # ~~~~~~~~~~ ADD CHECK THAT ALL objects ARE FILES AND NOT DIR ######
        delete_main_dir = 0
    else:
        delete_main_dir = 1
        objects = ls_master_path(origin)

    initialize = 0

    clear()
    print(TXT_TRANSFER_INFO.format(**info))
    for obj in objects:

        obj_data = None if obj.endswith("/") else get_master_file("/".join([origin, obj]))
        obj_fullpath = "/".join([destination, obj])

        # posticipate _create_slave_environment to NOT remove local slave
        # folder if objects really exists:
        # objects is generator, don't give error until first access
        if not initialize:
            initialize = 1
            if delete_main_dir:
                if not _create_slave_environment():
                    break  # objects transfer

                # nella modalita dove sono specificati i singoli file
                # non è permesso sincronizzare il contenuto di una directory
                #if not delete_main_dir and not obj_data:

        if ignore_test(obj):
            print(TXT_TRANSFER_IGNORE.format(storage=info['destination']['name'], object=obj))
        else:
            print(TXT_SAVE_OBJECT.format(storage=info['destination']['name'],root=info['destination']['path'], object=obj))
            if not mk_slave_object(obj_fullpath, obj_data):
                break # objects transfer

    else: # object for else
        if not CONFIG['MAIN'].getboolean('skip_tranfer_detail'):
            enter_to_continue()
            clear()
            return 1

    print(TXT_WARNING_EXIT_TASK_WITH_ERROR)
    enter_to_continue()
    clear()
    return 1

def form_maps_details():
    """Show to user loaded maps details."""
    clear()
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

    clear()

    if new_version_available():
        print(TXT_NEW_SCRIPT_VERSION_AVAILABLE)
        if input(TXT_INPUT).lower() == "y":
            clear()
            update_routine()
            return # EXIT MAIN

    print(TXT_LOADING.format(what='configuration'))
    if not CONFIG.read(CONFIG_FILENAME):
        load_default_config()
        save_config()
    else:
        validate_config()

    print(TXT_LOADING.format(what='mode'))
    get_ISMASTER()
    if ISMASTER is None: config_ISMASTER()

    print(TXT_LOADING.format(what='maps'))
    get_MAPS()
    while MAPS is None:
        config_MAPS()
            
    form_menu()



if __name__ == "__main__":
    main()

