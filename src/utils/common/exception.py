import os
import wx
import sys
import json
import gettext
import threading
import traceback
from typing import Callable

from utils.common.map import status_code_map
from utils.common.datetime_util import DateTime

_ = gettext.gettext

class GlobalExceptionInfo:
    lock = threading.Lock()
    info = {}

class GlobalException(Exception):
    def __init__(self, message: str = None, code: int = None, stack_trace: str = None, callback: Callable = None, args: tuple = (), json_data: dict = None, parse_url: str = None):
        self.message = message
        self.code = code
        self.stack_trace = stack_trace
        self.callback = callback
        self.custom_args = args
        self.json_data = json_data
        self.parse_url = parse_url

        self.get_message()

        super().__init__(self.message)

    def get_message(self):
        if self.code:
            if not self.message:
                self.message = status_code_map.get(self.code, self.message)
        else:
            self.code = 500

def exception_handler(exc_type, exc_value: GlobalException, exc_tb):
    def get_exception_info(exception, exc_type, exc_value, exc_tb):
        stack_trace = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        with GlobalExceptionInfo.lock:
            with open(os.path.join(os.getcwd(), "error_log.txt"), "a", encoding = "utf-8") as f:
                header = f"{'=' * 80}\n>>> Caused Time: {DateTime.time_str()}\n{'='*80}\n"
                f.write(header)
                f.write(stack_trace)
                f.write(f"{'=' * 80}\n\n")

            print(stack_trace)

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
    parse_url = getattr(exception, "parse_url", None)
    
    message = exception.message if isinstance(exception, GlobalException) else str(exception)
    stack_trace = exception.stack_trace if hasattr(exception, "stack_trace") and exception.stack_trace else stack_trace

    if json_data:
        stack_trace += f"\n\nJSON Data:\n{json.dumps(json_data, ensure_ascii = False, indent = 4)}"

    if parse_url:
        stack_trace += f"\n\nParse URL:\n{parse_url}"
    
    update_exception_info()

    if callback:
        callback(*args)

def thread_exception_handler(args):
    exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

def show_error_message_dialog(caption: str, message: str = None, parent: wx.Window = None):
    def worker():
        info = GlobalExceptionInfo.info.copy()

        if message:
            msg = "%s\n\n%s" % (caption, message)
        else:
            msg = _("%s\n\n描述：%s") % (caption, info.get("message", ""))

        dlg = wx.MessageDialog(parent, msg, _("错误"), wx.ICON_ERROR | wx.YES_NO)
        dlg.SetYesNoLabels(_("详细信息"), _("确定"))

        if dlg.ShowModal() == wx.ID_YES:
            from gui.dialog.error import ErrorInfoDialog

            err_dlg = ErrorInfoDialog(parent, info)
            err_dlg.ShowModal()

    wx.CallAfter(worker)

sys.excepthook = exception_handler
threading.excepthook = thread_exception_handler