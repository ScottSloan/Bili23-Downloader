import sys
import threading
import traceback
from typing import Callable
from datetime import datetime

from utils.common.map import status_code_map

class GlobalExceptionInfo:
    info = {}

class GlobalException(Exception):
    def __init__(self, message: str = None, code: int = None, stack_trace: str = None, callback: Callable = None, args: tuple = ()):
        self.message = message
        self.code = code
        self.stack_trace = stack_trace
        self.callback = callback
        self.custom_args = args

        self.get_message()

        super().__init__(self.message)

    def get_message(self):
        if self.code:
            self.message = status_code_map.get(self.code, self.message)
        else:
            self.code = 500

def exception_handler(exc_type, exc_value: GlobalException, exc_tb):
    def get_exception_info(exception, exc_type, exc_value, exc_tb):
        stack_trace = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        traceback.print_exception(exc_type, exc_value, exc_tb)

        print()

        return exception, stack_trace

    def update_exception_info():
        GlobalExceptionInfo.info = {
            "timestamp": int(datetime.now().timestamp()),
            "exception_name": exception.__class__.__name__,
            "message": message,
            "stack_trace": stack_trace,
            "code": exc_value.code
        }

    if exc_value.__cause__:
        exception, stack_trace = get_exception_info(exc_value.__cause__, type(exception), exception, exception.__traceback__)

    else:
        exception, stack_trace = get_exception_info(exc_value, exc_type, exc_value, exc_tb)
    
    message = exc_value.message if isinstance(exception, GlobalException) else str(exception)
    stack_trace = exception.stack_trace if hasattr(exception, "stack_trace") and exception.stack_trace else stack_trace
    
    update_exception_info()

    callback = getattr(exception, "callback", None)
    args = getattr(exception, "custom_args", ())

    if callback:
        callback(*args)

def thread_exception_handler(args):
    exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

sys.excepthook = exception_handler
threading.excepthook = thread_exception_handler