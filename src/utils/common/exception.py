import re
import sys
import time
import inspect
import threading
import traceback
from typing import Callable

from utils.common.data_type import ExceptionInfo
from utils.common.map import status_code_map
from utils.config import Config

class GlobalExceptionInfo:
    info: ExceptionInfo = None

class GlobalException(Exception):
    def __init__(self, log: str = "", return_code: str = "", callback: Callable = None, url: str = None, use_traceback: bool = False, message: str = ""):
        super().__init__(message)

        self.log = log
        self.return_code = return_code
        self.callback = callback
        self.url = url
        self.use_traceback = use_traceback

def exception_handler(exc_type, exc_value, exc_tb):
    def get_last_line(exc_tb):
        while exc_tb:
            _module_name = inspect.getmodule(exc_tb.tb_frame).__name__
            _co_name = exc_tb.tb_frame.f_code.co_name
            _lineno = exc_tb.tb_frame.f_lineno
            exc_tb = exc_tb.tb_next

        return (_module_name, _co_name, _lineno)

    _traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

    if isinstance(exc_value, GlobalException):
        log = exc_value.log
        return_code = exc_value.return_code
        callback = exc_value.callback
        url = exc_value.url
        use_traceback = exc_value.use_traceback
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

    (_module_name, _co_name, _lineno) = get_last_line(exc_tb)

    if use_traceback:
        log = _traceback

    _info = ExceptionInfo()
    _info.timestamp = round(time.time())
    _info.log = log
    _info.traceback = _traceback
    _info.exception_type = exc_type.__name__
    _info.id = str(_code)
    _info.source = "{} -> {}, Line {}".format(_module_name, _co_name, _lineno)
    _info.return_code = return_code

    GlobalExceptionInfo.info = _info

    if callback:
        if url:
            callback(url)
        else:
            callback()

    if Config.Misc.enable_debug:
        traceback.print_exception(exc_type, exc_value, exc_tb)

def thread_exception_handler(args):
    exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

sys.excepthook = exception_handler
threading.excepthook = thread_exception_handler