import re
import sys
import inspect
import threading
import traceback
from typing import Callable
from datetime import datetime

from utils.common.data_type import ExceptionInfo
from utils.common.map import status_code_map

class GlobalExceptionInfo:
    info: ExceptionInfo = None

class GlobalException(Exception):
    def __init__(self, log: str = "", return_code: str = "", callback: Callable = None, url: str = None):
        super().__init__(log)

        self.log = log
        self.return_code = return_code
        self.callback = callback
        self.url = url

def exception_handler(exc_type, exc_value, exc_tb):
    def _global_exception(exc_value: GlobalException):
        return_code = exc_value.return_code
        callback = exc_value.callback
        url = exc_value.url

        if exc_value.__cause__:
            log = _get_traceback_string(exc_value.__cause__)
            _traceback = exc_value.__cause__.__traceback__
            _exception_type = type(exc_value.__cause__).__name__

            id, short_log = _get_error_id_and_short_log(exc_value.__cause__)

        else:
            if return_code:
                log = exc_value.log
            else:
                log = _get_traceback_string(exc_value)
            
            _traceback = exc_tb
            _exception_type = exc_type.__name__

            id, short_log = _get_error_id_and_short_log(exc_value.log)

        GlobalExceptionInfo.info = _get_exception_info(log, return_code, _traceback, id, short_log, _exception_type)

        if callback:
            if url:
                callback(url)
            else:
                callback()
    
    def _other_exception(exc_value):
        return_code = ""

        id, short_log = _get_error_id_and_short_log(exc_value)
        
        GlobalExceptionInfo.info = _get_exception_info(exc_value, return_code, exc_tb, id, short_log, exc_type.__name__)

    def _get_traceback_string(exc_value: BaseException):
        return "".join(traceback.format_exception(type(exc_value), exc_value, exc_value.__traceback__))
    
    def _get_error_id_and_short_log(log: str):
        if re.findall(r'^[-+]?[0-9]+$', str(log)):
            id = int(str(log))
            return str(id), "{} ({})".format(status_code_map.get(id, f"未知错误 ({id})"), id)
        else:
            return "150", f"{log.__class__.__name__}: {log}"
    
    def _get_exception_info(log: str, return_code: str, exc_tb, id: str, short_log: str, exception_type: str):
        info = ExceptionInfo()
        info.timestamp = int(datetime.timestamp(datetime.now()))
        info.log = log
        info.short_log = short_log
        info.exception_type = exception_type
        info.id = id
        info.source = "{} -> {}, Line {}".format(inspect.getmodule(exc_tb.tb_frame).__name__, exc_tb.tb_frame.f_code.co_name, exc_tb.tb_frame.f_lineno)
        info.return_code = return_code

        return info
    
    if isinstance(exc_value, GlobalException):
        _global_exception(exc_value)

    else:
        _other_exception(exc_value)

    traceback.print_exception(exc_type, exc_value, exc_tb)

def thread_exception_handler(args):
    exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

sys.excepthook = exception_handler
threading.excepthook = thread_exception_handler