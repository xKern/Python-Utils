from typing import Union
import os
from enum import Enum
import threading
import sys

class LogType(Enum):
    INFO = 0            # general log
    ADD = 1             # indicate resoure add
    REMOVE = 2          # indicate resource removal
    WARNING = 3         # warnings
    ERROR = 4           # general warnings
    DEBUG = 5           # debug logs

class Logger:
    def __init__(self) -> None:
        self.__log_path = None 
        self.__file = None
        self.write_file = False

    @property
    def log_file(self) -> str:
        return self.__log_path

    @log_file.setter
    def log_file(self, path: str):
        # if path doesn't exist, check if it's possible to create a file at the path
        if not os.path.exists(path):
            # check if the path has a parent dir in it
            # if yes, check if it actually exists
            if (dir_path := os.path.dirname(path)):
                if not os.path.exists(dir_path):
                    raise FileNotFoundError(f"The path {dir_path} doesn't exist")
        # if the file exists, open it and append
        file_exists = os.path.exists(path)
        file = open(path, 'a')
        # if file existed before the call to open(), append this line
        if file_exists:
            file.write("\n---appending log---\n")
        # if the old log file is open, close it
        if self.__file and not self.__file.closed:
            self.__file.close()
            # and replace the file
        self.__file = file
        self.__log_path = path

    def log(self, entry: str, logtype: Union[LogType, int] = LogType.INFO, 
            show_caller=False, show_thread=False):
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
        line = f"[{symbol}]{thread_name}{func} {entry}\n"
        sys.stdout.write(line)
        if self.__file:
            self.__file.write(line)




        
    