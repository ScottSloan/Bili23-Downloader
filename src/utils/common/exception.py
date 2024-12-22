import sys
import time
import inspect
import threading

from functools import wraps
from utils.common.data_type import ExceptionInfo

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

class RequestCode:
    SSLERROR = 200                          # SSLERROR
    TimeOut = 201                           # TimeOut
    TooManyRedirects = 202                  # TooManyRedirects
    ConnectionError = 203                   # ConnectionError

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

class VIPError(Exception):
    # 大会员认证异常类
    pass

class URLError(Exception):
    pass

class ErrorUtils:
    def __init__(self):
        pass

    def getErrorInfo(self, error_code):
        # 根据错误码获取错误信息
        match error_code:
            case RequestCode.SSLERROR:
                return "SSL 证书错误"
            
            case RequestCode.TimeOut:
                return "连接超时"
            
            case RequestCode.TooManyRedirects:
                return "重定向次数过多"
            
            case RequestCode.ConnectionError:
                return "无法连接到服务器或 DNS 解析失败"

    def getStatusInfo(self, status_code):
        # 根据状态码获取错误信息
        match status_code:
            case StatusCode.CODE_1:
                return "未找到该房间"
            
            case StatusCode.CODE_400:
                return "请求错误"
            
            case StatusCode.CODE_403:
                return "权限不足"
            
            case StatusCode.CODE_404:
                return "视频不存在"
            
            case StatusCode.CODE_10403:
                return "根据版权方要求，您所在的地区无法观看本片"
        
            case StatusCode.CODE_62002:
                return "稿件不可见"
            
            case StatusCode.CODE_62004:
                return "稿件审核中"
            
            case StatusCode.CODE_62012:
                return "仅 UP 主自己可见"
            
            case StatusCode.CODE_19002003:
                return "房间信息不存在"
            
            case _:
                return "未知错误"
            
def process_read_config_exception(f):
    @wraps(f)
    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        
        except Exception:
            ErrorCallback.onReadConfigError()

    return func