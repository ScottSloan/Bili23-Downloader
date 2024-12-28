import re
import sys
import time
import inspect
import threading
import traceback
from typing import Callable

from utils.common.data_type import ExceptionInfo
from utils.common.map import status_code_map

class GlobalExceptionInfo:
    info: ExceptionInfo = None

class GlobalException(Exception):
    def __init__(self, log: str = "", return_code: str = "", callback: Callable = None, url: str = None, message: str = ""):
        super().__init__(message)

        self.log = log
        self.return_code = return_code
        self.callback = callback
        self.url = url

def exception_handler(exc_type, exc_value, exc_tb):
    if isinstance(exc_value, GlobalException):
        if exc_value.__cause__:
            exc_tb = exc_value.__cause__.__traceback__
            log = "".join(traceback.format_exception(type(exc_value.__cause__), exc_value.__cause__, exc_tb))
        else:
            log = exc_value.log

        return_code = exc_value.return_code
        callback = exc_value.callback
        url = exc_value.url
    else:
        log = exc_value
        return_code = ""
        callback = None
        url = None

    if re.findall(r'^[-+]?[0-9]+$', str(log)):
        _code = int(str(log))
        log = "{} ({})".format(status_code_map.get(_code, f"未知错误 ({_code})"), _code)
    else:
        _code = "150"
        log = f"{log.__class__.__name__}: {log}"

    _info = ExceptionInfo()
    _info.timestamp = round(time.time())
    _info.log = log
    _info.exception_type = exc_type.__name__
    _info.id = str(_code)
    _info.source = "{} -> {}, Line {}".format(inspect.getmodule(exc_tb.tb_frame).__name__, exc_tb.tb_frame.f_code.co_name, exc_tb.tb_frame.f_lineno)
    _info.return_code = return_code

    GlobalExceptionInfo.info = _info

    if callback:
        if url:
            callback(url)
        else:
            callback()

    traceback.print_exception(exc_type, exc_value, exc_tb)

def thread_exception_handler(args):
    exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

sys.excepthook = exception_handler
threading.excepthook = thread_exception_handler