import re
import sys
import time
import inspect
import threading

from functools import wraps
from utils.common.data_type import ExceptionInfo
from utils.common.map import status_code_map

class ErrorCode:
    Invalid_URL = 100                       # URL 无效
    Parse_Error = 101                       # 解析异常
    VIP_Required = 102                      # 需要大会员或付费内容
    Request_Error = 103                     # 请求异常
    Unknown_Error = 104                     # 其他未知错误

class StatusCode:
    CODE_0 = 0                              # 请求成功
    CODE_1 = 1                              # 未找到该房间
    CODE_400 = -400                         # 请求错误
    CODE_403 = -403                         # 权限不足
    CODE_404 = -404                         # 视频不存在
    CODE_10403 = -10403                     # 地区限制
    CODE_62002 = 62002                      # 稿件不可见
    CODE_62004 = 62004                      # 稿件审核中
    CODE_62012 = 62012                      # 仅 UP 主自己可见
    CODE_19002003 = 19002003                # 房间信息不存在

class ErrorCallback:
    parse_thread_stop_flag: bool = False
    onError = None
    onReadConfigError = None

    onRedirect = None

class GlobalExceptionInfo:
    info: ExceptionInfo = None

class GlobalException(Exception):
    def __init__(self, log = "", return_code = "", callback = None, message = ""):
        super().__init__(message)

        self.log = log
        self.return_code = return_code
        self.callback = callback

def exception_handler(exc_type, exc_value, exc_tb):
    _frame = exc_tb.tb_frame

    if isinstance(exc_value, GlobalException):
        log = exc_value.log
        return_code = exc_value.return_code
        callback = exc_value.callback
    else:
        log = exc_value
        return_code = ""
        callback = None

    if re.findall(r'^[-+]?[0-9]+$', str(log)):
        _code = int(str(log))
        log = "{} ({})".format(status_code_map.get(_code, "未知错误"), _code)

    _info = ExceptionInfo()
    _info.timestamp = round(time.time())
    _info.log = log
    _info.exception_type = exc_type.__name__
    _info.id = "150"
    _info.source = "{} -> {}, Line {}".format(inspect.getmodule(_frame).__name__, _frame.f_code.co_name, _frame.f_lineno)
    _info.return_code = return_code

    GlobalExceptionInfo.info = _info

    if callback:
        callback()

def thread_exception_handler(args):
    exception_handler(args.exc_type, args.exc_value, args.exc_traceback)

sys.excepthook = exception_handler
threading.excepthook = thread_exception_handler

def process_read_config_exception(f):
    @wraps(f)
    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        
        except Exception:
            ErrorCallback.onReadConfigError()

    return func