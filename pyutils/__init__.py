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
from typing import Optional, Union


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


def log_and_error(message: str):
    """Log error and raise an exception

    Args:
        message (str): the string to be logged and used in the exception

    Raises:
        Exception
    """
    log(message, LogType.ERROR)
    raise Exception(message)


URLInfo = namedtuple(
    "URLInfo", ['url', 'domain', 'components', 'scheme', 'query', 'fragment'],
    defaults=(None,) * 5)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sha1_string(string: str) -> str:
    """Create hex sha1 from supplied utf-8 string

    Args:
        string (str): 

    Returns:
        str: hex representation of the hash
    """
    string = string.encode('utf-8')
    hash = hashlib.sha1(string)
    hash = hash.hexdigest()
    return hash


def random_string(length: int, characters: CharacterSet) -> str:
    """Generate a random string with a given length and character set.

    Args:
        length (int): The length of the string to generate.
        characters (CharacterSet): The set of characters to use in generating the string.

    Returns:
        str: The generated string.
    """
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


def intervalcheck(key: str, duration: int, use_key_as_path: bool = False, retouch: bool = True) -> bool:
    """Check if a specified interval (seconds) has passed since the last time a given `key` was checked.

    Args:
        key (`str`): The key to check. The key is created if it doesn't exist.
        duration (`int`): The duration of the interval (in seconds) to check.
        use_key_as_path (`bool`, optional): Allows you to use `key` argument as a file path. This file's modified time is 
        used for comparison.
        retouch (`bool`, optional): Whether to update the `key`'s last modified time after checking. Defaults to `True`.

    Returns:
        `bool`: True if the interval has passed, False otherwise.
    """
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
    """Follows a single redirect for a given URL and returns the final redirect URL.

    Args:
        `url` (`str`): The URL to follow the redirect for.

    Returns:
        `str`: The final redirect URL or None if no redirect occurred.
    """
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
    """Decompresses a bz2-compressed file.

    Args:
        in_file_path (`str`): The path of the input file to decompress.
        out_file_path (`str`): The path of the output file to write the decompressed data to.

    Returns:
        `bool`: True if the decompression was successful, False otherwise.
    """
    if not os.path.exists(in_file_path):
        return False
    in_file = bz2.open(in_file_path)
    out_file = open(out_file_path, 'wb')
    shutil.copyfileobj(in_file, out_file)
    return True


def get_remote_filesize(url) -> Optional[int]:
    """Retrieve the size of a file at a given URL.

    Args:
        url (`str`): The URL of the file to retrieve the size of.

    Returns:
        `int`: The size of the file in bytes. If the size cannot be retrieved, returns None.
    """
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
    """Extract the file name from a given URL.

    Args:
        url (`str`): The URL to extract the file name from.

    Returns:
        `str`: The extracted file name.
    """
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


def download_file(url, local_path, headers=[]):
    """Download a file from a given URL and save it to a specified local path.

    Args:
        url (`str`): The URL of the file to download.
        local_path (`str`): The local file path to save the downloaded file to.
        headers (`list`, optional): A list of HTTP headers to include in the request. Defaults to an empty list.

    Returns:
        `bool`: True if the file was successfully downloaded and saved, False otherwise.
    """
    opener = urllib.request.build_opener()
    opener.addheaders = headers
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, local_path)
    if os.path.exists(local_path):
        return True
    return False


def url_split(url: str) -> URLInfo:
    """Split a URL into its component parts.

    Args:
        url (`str`): The URL to split.

    Returns:
        `URLInfo`: A named tuple containing the following fields:
            url (str): The original URL.
            domain (str): The domain of the URL.
            components (list): A list of path components in the URL.
            scheme (str): The scheme (e.g. 'http') of the URL.
            query (dict): A dictionary of query parameters and their values.
            fragment (str): The fragment identifier (e.g. '#section-1') of the URL.
    """
    url_split = urlparse(url, allow_fragments=True)
    if not url_split.netloc:
        return ()
    components = [c for c in url_split.path.split('/') if c]
    query = parse_qs(url_split.query)
    pathinfo = URLInfo(url, url_split.netloc, components,
                       url_split.scheme, query, url_split.fragment)
    return pathinfo


def replace_extension(path, extension=None):
    """Replace the extension of a file path with a new extension.

    Args:
        path (`str`): The file path to modify.
        extension (`str`, optional): The new extension to use. 
        If not specified, the extension will be removed.

    Returns:
        `str`: The modified file path with the new extension. 
        If the file path is invalid or no extension was specified, returns None.
    """
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
    """Print a log message with a specified type and optional caller and thread information.

    Args:
        entry (`str`): The log message to print.
        logtype (Union[`LogType`, `int`], optional): The type of the log message. Defaults to LogType.INFO.
        show_caller (`bool`, optional): Include the caller function's name in the log message. Defaults to False.
        show_thread (`bool`, optional): Include the current thread's name in the log message. Defaults to False.
    """
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
    """Convert a size in bytes to a human-readable format.

    Args:
        size (`int`): The size in bytes to convert.
        ib_unit (`bool`, optional): Whether to use binary units (e.g. KiB, MiB) 
        instead of decimal prefixes (e.g. KB, MB). Defaults to False.

    Returns:
        `str`: The size in a human-readable format, e.g. '5.67 MB'.
    """
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

