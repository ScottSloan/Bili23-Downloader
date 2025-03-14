import sys
import threading
import traceback
from typing import Callable
from datetime import datetime

from utils.common.map import status_code_map

class GlobalExceptionInfo:
    info = {}

class GlobalException(Exception):
    def __init__(self, message: str = None, code: int = None, stack_trace: str = None, callback: Callable = None, url: str = None):
        if not message and code:
            message = status_code_map.get(code)

        super().__init__(message)

        self.message = message
        self.code = code
        self.stack_trace = stack_trace
        self.callback = callback
        self.url = url

def exception_handler(exc_type, exc_value: Exception, exc_tb):
    if exc_value.__cause__:
        exception = exc_value.__cause__
        stack_trace = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

        traceback.print_exception(type(exception), exception, exception.__traceback__)
    else:
        exception = exc_value
        stack_trace = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        traceback.print_exception(exc_type, exc_value, exc_tb)

    if isinstance(exception, GlobalException):
        if exception.stack_trace:
            stack_trace = exception.stack_trace

        message = exception.message
        code = exception.code
    else:
        message = str(exception)
        code = 500

    exception_name = exception.__class__.__name__

    GlobalExceptionInfo.info = {
        "timestamp": int(datetime.now().timestamp()),
        "exception_name": exception_name,
        "message": message,
        "stack_trace": stack_trace,
        "code": code
    }

    if hasattr(exception, "callback") and exception.callback:
        url = exception.url
        callback = exception.callback

    elif hasattr(exc_value, "callback") and exc_value.callback:
        url = exc_value.url
        callback = exc_value.callback
    
    else:
        url = None
        callback = None
    
    if callback:
        if url:
            callback(url)
        else:
            callback()

def thread_exception_handler(args):
    exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

sys.excepthook = exception_handler
threading.excepthook = thread_exception_handler