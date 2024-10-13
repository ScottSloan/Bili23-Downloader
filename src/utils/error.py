import requests

from functools import wraps

class ErrorCode:
    Invalid_URL = 100                       # URL 无效
    Parse_Error = 101                       # 解析异常
    VIP_Required = 102                      # 需要大会员或付费内容
    Area_Limit = 103                        # 区域限制
    Request_Error = 104                     # 请求异常
    Unknown_Error = 105                     # 其他未知错误

class StatusCode:
    CODE_0 = 0                              # 请求成功
    CODE_400 = -400                         # 请求错误
    CODE_403 = -403                         # 权限不足
    CODE_404 = -404                         # 视频不存在
    CODE_62002 = 62002                      # 稿件不可见
    CODE_62004 = 62004                      # 稿件审核中
    CODE_62012 = 62012                      # 仅 UP 主自己可见

class RequestCode:
    SSLERROR = 200                          # SSLERROR
    TimeOut = 201                           # TimeOut
    TooManyRedirects = 202                  # TooManyRedirects
    ConnectionError = 203                   # ConnectionError

class ErrorCallback:
    onErrorCallbak = None

class VIPError(Exception):
    # 大会员认证异常类
    pass

class ParseError(Exception):
    # 解析异常类
    def __init__(self, message, status_code):
        self.message, self.status_code = message, status_code

        super().__init__(self.message, self.status_code)

class Error:
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
            case StatusCode.CODE_400:
                return "请求错误"
            
            case StatusCode.CODE_403:
                return "权限不足"
            
            case StatusCode.CODE_404:
                return "视频不存在"
            
            case StatusCode.CODE_62002:
                return "稿件不可见"
            
            case StatusCode.CODE_62004:
                return "稿件审核中"
            
            case StatusCode.CODE_62012:
                return "仅 UP 主自己可见"

def process_exception(f):
    @wraps(f)
    def func(*args, **kwargs):
        error = Error()

        try:
            return f(*args, **kwargs)

        except requests.exceptions.SSLError:
            error_info = error.getErrorInfo(RequestCode.SSLERROR)

            ErrorCallback.onErrorCallbak(ErrorCode.Request_Error, error_info)

        except requests.exceptions.Timeout:
            error_info = error.getErrorInfo(RequestCode.TimeOut)

            ErrorCallback.onErrorCallbak(ErrorCode.Request_Error, error_info)

        except requests.exceptions.TooManyRedirects:
            error_info = error.getErrorInfo(RequestCode.TooManyRedirects)

            ErrorCallback.onErrorCallbak(ErrorCode.Request_Error, error_info)

        except requests.exceptions.ConnectionError:
            error_info = error.getErrorInfo(RequestCode.ConnectionError)

            ErrorCallback.onErrorCallbak(ErrorCode.Request_Error, error_info)

        except ParseError as e:
            error_info = f"{e.message} ({e.status_code})"

            ErrorCallback.onErrorCallbak(ErrorCode.Parse_Error, error_info)

        except VIPError:
            ErrorCallback.onErrorCallbak(ErrorCode.VIP_Required)

        except Exception:
            ErrorCallback.onErrorCallbak(ErrorCode.Unknown_Error)
            
    return func