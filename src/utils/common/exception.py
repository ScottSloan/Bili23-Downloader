import sys
import json
import threading
import traceback
from typing import Callable

from utils.common.map import status_code_map
from utils.common.datetime_util import DateTime

class GlobalExceptionInfo:
    info = {}

class GlobalException(Exception):
    def __init__(self, message: str = None, code: int = None, stack_trace: str = None, callback: Callable = None, args: tuple = (), json_data: dict = None):
        self.message = message
        self.code = code
        self.stack_trace = stack_trace
        self.callback = callback
        self.custom_args = args
        self.json_data = json_data

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
            "timestamp": DateTime.get_timestamp(),
            "exception_name": exception.__class__.__name__,
            "message": message,
            "stack_trace": stack_trace,
            "code": getattr(exc_value, "code", 500)
        }

    callback = getattr(exc_value, "callback", None)
    args = getattr(exc_value, "custom_args", ())

    if exc_value.__cause__:
        exception, stack_trace = get_exception_info(exc_value.__cause__, type(exc_value.__cause__), exc_value.__cause__, exc_value.__cause__.__traceback__)

        if hasattr(exception, "callback") and exception.callback:
            callback = exception.callback
            args = exception.custom_args
    else:
        exception, stack_trace = get_exception_info(exc_value, exc_type, exc_value, exc_tb)

    json_data = getattr(exception, "json_data", None)
    
    message = exception.message if isinstance(exception, GlobalException) else str(exception)
    stack_trace = exception.stack_trace if hasattr(exception, "stack_trace") and exception.stack_trace else stack_trace

    if json_data:
        stack_trace += f"\n\nJSON Data:\n{json.dumps(json_data, ensure_ascii = False, indent = 4)}"
    
    update_exception_info()

    if callback:
        callback(*args)

def thread_exception_handler(args):
    exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

sys.excepthook = exception_handler
threading.excepthook = thread_exception_handler