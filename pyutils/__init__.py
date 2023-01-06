import os
import urllib.request
from urllib.error import HTTPError
from urllib.parse import urlparse, parse_qs
from collections import namedtuple
import shutil
import bz2
import time
import sys
import hashlib
import threading
from enum import auto, IntFlag, Enum
import string
import random
from typing import Union


class CharacterSet(IntFlag):
    NUMBERS = auto()
    LOWERCASE = auto()
    UPPERCASE = auto()
    HEXCHARS = auto()
    ALL = NUMBERS | LOWERCASE | UPPERCASE
    HEXUPPER = NUMBERS | UPPERCASE | HEXCHARS
    HEXLOWER = NUMBERS | LOWERCASE | HEXCHARS

class LogType(Enum):
    INFO = 0            # general log
    ADD = 1             # indicate resoure add 
    REMOVE = 2          # indicate resource removal
    WARNING = 3         # warnings
    ERROR = 4           # general warnings
    DEBUG = 5           # debug logs


def error_exit(message: str):
    log(message, 4)
    raise Exception(message)


URLInfo = namedtuple(
    "URLInfo", ['url', 'domain', 'components', 'scheme', 'query', 'fragment'],
    defaults=(None,) * 5)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sha1_string(string: str):
    string = string.encode('utf-8')
    hash = hashlib.sha1(string)
    hash = hash.hexdigest()
    return hash


def random_string(length: int, characters: CharacterSet):
    charset = []
    if isinstance(characters, CharacterSet):
        characters
    # slice alphabets to a-f if HEXCHARS is chosen
    # the slicing shouldn't happen if ALL is chosen since
    # ALL must take precedence
    if CharacterSet.HEXCHARS in characters and CharacterSet.ALL not in characters:
        alphabets = string.ascii_lowercase[:6]
    else:
        alphabets = string.ascii_lowercase

    if CharacterSet.LOWERCASE in characters:
        charset += list(alphabets)
    if CharacterSet.UPPERCASE in characters:
        charset += list(alphabets.upper())

    # if no alphabets flags are given but hexchars is chosen, add lowercase
    # chars a-f (sliced in previous HEXCHARS check) explicity
    if CharacterSet.HEXCHARS in characters and not charset:
        charset = list(alphabets)

    if CharacterSet.NUMBERS in characters:
        charset += list(string.digits)

    charset_unique = []
    [charset_unique.append(c) for c in charset if c not in charset_unique]
    rand_string = []
    for _ in range(length):
        rand_string.append(random.choice(charset_unique))
    return ''.join(rand_string)


def intervalcheck(key: str, duration: int, use_key_as_path: bool = False,
                  retouch: bool = True) -> bool:
    '''
    Checks if the given duration has passed for the given key.
    If the duration has passed, reset the duration
    '''
    expired = False
    if use_key_as_path:
        path = key
        dir = os.path.dirname(path)
    else:
        dir = 'intervalcheck'
        path = f"{dir}/{key}"
    os.makedirs(dir, exist_ok=True)
    if os.path.exists(path):
        last_modified = os.path.getmtime(path)
        current_time = time.time()
        delta = current_time - last_modified
        if delta > duration:
            expired = True
    else:
        expired = True

    # update the last_modified if needed
    if expired and retouch:
        with open(path, 'w+') as f:
            f.write('')
        return True
    return expired


def get_redirect_url(url):
    # urllib.request follows  rediects automatically
    # build a custom opener that neuters this behavior
    # so we'll get the redirect url from header without
    # going to the redirect url
    redirect_url = None
    try:
        opener = urllib.request.build_opener(NoRedirect)
        urllib.request.install_opener(opener)
        urllib.request.urlopen(url)
    except HTTPError as e:
        header_info = e.info()
        redirect_url = header_info.get('location')
    except Exception as e:
        print(e)

    # restore original behavior
    urllib.request.install_opener(
        urllib.request.build_opener(urllib.request.HTTPRedirectHandler))
    return redirect_url


def bz2decompress(in_file_path, out_file_path) -> bool:
    if not os.path.exists(in_file_path):
        return False
    in_file = bz2.open(in_file_path)
    out_file = open(out_file_path, 'wb')
    shutil.copyfileobj(in_file, out_file)
    return True


def get_remote_filesize(url):
    if not url:
        return None
    try:
        r = urllib.request.urlopen(url)
        header_info = r.info()
        if (size := header_info.get('content-length')):
            return int(size)
    except Exception as e:
        print(e)
    return None


def url_filename(url):
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


def download_file(url, local_path, headers=[]):
    opener = urllib.request.build_opener()
    opener.addheaders = headers
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, local_path)
    if os.path.exists(local_path):
        return True
    return False


def url_split(url):
    url_split = urlparse(url, allow_fragments=True)
    if not url_split.netloc:
        return ()
    components = [c for c in url_split.path.split('/') if c]
    query = parse_qs(url_split.query)
    pathinfo = URLInfo(url, url_split.netloc, components,
                       url_split.scheme, query, url_split.fragment)
    return pathinfo


def replace_extension(path, extension=None):
    if not path:
        return None
    path_split = os.path.splitext(path)
    # if no extension is given, remove extension
    if not extension:
        return path_split[0]
    if not path_split:
        return None
    new_path = f"{path_split[0]}.{extension}"
    return new_path


def log(entry: str, logtype: Union[LogType, int] = LogType.INFO, show_caller=False, show_thread=False):
    symbols = ['*', '+', '-', '!', '#', '>', '<']
    if isinstance(logtype, LogType):
        logtype = logtype.value
    try:
        symbol = symbols[logtype]
    except Exception:
        symbol = '*'
    thread_name = f" [{threading.current_thread().name}]" if show_thread else ''

    func = f" [{sys._getframe(1).f_code.co_name}] -->" if show_caller else ''
    line = f"[{symbol}]{thread_name}{func} {entry}"
    print(line)


def human_readable_size(size: int, ib_unit: bool = False):
    units = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB']
    selected_unit = 'bytes'
    unit_size = 1024 if ib_unit else 1000
    result = 0
    for index, unit in enumerate(units):
        divider = pow(unit_size, index)
        if divider > size:
            break
        result = size / divider
        selected_unit = unit
    if ib_unit:
        selected_unit = selected_unit.replace('B', 'iB')
    result = round(result, 2)
    format_string = "%d" if int(result) == result else "%.2f"
    return f"{format_string} %s" % (result, selected_unit)


def cleanup_errors():
    dir_list = os.listdir("errors")
    for dir in dir_list:
        path = f"errors/{dir}"
        error_file_list = os.listdir(path)
        if not error_file_list:
            os.rmdir(path)


def cleanup():
    cleanup_errors()
    # other cleanup subroutines
    pass
