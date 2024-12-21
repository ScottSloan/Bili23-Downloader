import requests

from functools import wraps

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

class VIPError(Exception):
    # 大会员认证异常类
    pass

class URLError(Exception):
    pass

class ParseError(Exception):
    # 解析异常类
    def __init__(self, message, status_code):
        self.message, self.status_code = message, status_code

        super().__init__(self.message, self.status_code)

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

def process_exception(f):
    @wraps(f)
    def func(*args, **kwargs):
        error = ErrorUtils()

        try:
            return f(*args, **kwargs)

        except requests.exceptions.SSLError:
            error_info = error.getErrorInfo(RequestCode.SSLERROR)

            ErrorCallback.onError(ErrorCode.Request_Error, error_info)

        except requests.exceptions.Timeout:
            error_info = error.getErrorInfo(RequestCode.TimeOut)

            ErrorCallback.onError(ErrorCode.Request_Error, error_info)

        except requests.exceptions.TooManyRedirects:
            error_info = error.getErrorInfo(RequestCode.TooManyRedirects)

            ErrorCallback.onError(ErrorCode.Request_Error, error_info)

        except requests.exceptions.ConnectionError:
            error_info = error.getErrorInfo(RequestCode.ConnectionError)

            ErrorCallback.onError(ErrorCode.Request_Error, error_info)

        except URLError:
            ErrorCallback.onError(ErrorCode.Invalid_URL)

        except ParseError as e:
            error_info = f"{e.message} ({e.status_code})"

            ErrorCallback.onError(ErrorCode.Parse_Error, error_info)

        except VIPError:
            ErrorCallback.onError(ErrorCode.VIP_Required)

        except Exception:
            ErrorCallback.onError(ErrorCode.Unknown_Error)
            
    return func