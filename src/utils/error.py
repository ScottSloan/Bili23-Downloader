import requests

from functools import wraps

from utils.config import Config

class ErrorCode:
    Invalid_URL = 100         # URL 无效
    Parse_Error = 101         # 解析异常
    VIP_Required = 102        # 需要大会员或付费内容
    Area_Limit = 103          # 区域限制
    Request_Error = 104       # 请求异常
    Unknown_Error = 105       # 其他未知错误

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
            case Config.Type.REQUEST_CODE_SSLERROR:
                return "SSL 证书错误"
            
            case Config.Type.REQUEST_CODE_TimeOut:
                return "连接超时"
            
            case Config.Type.REQUEST_CODE_TooManyRedirects:
                return "重定向次数过多"
            
            case Config.Type.REQUEST_CODE_ConnectionError:
                return "无法连接到服务器或 DNS 解析失败"

    def getStatusInfo(self, status_code):
        # 根据状态码获取错误信息
        match status_code:
            case Config.Type.STATUS_CODE_400:
                return "请求错误"
            
            case Config.Type.STATUS_CODE_403:
                return "权限不足"
            
            case Config.Type.STATUS_CODE_404:
                return "视频不存在"
            
            case Config.Type.STATUS_CODE_62002:
                return "稿件不可见"
            
            case Config.Type.STATUS_CODE_62004:
                return "稿件审核中"
            
            case Config.Type.STATUS_CODE_62012:
                return "仅 UP 主自己可见"

def process_exception(f):
    @wraps(f)
    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except requests.exceptions.SSLError:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_RequestError, Config.Type.REQUEST_CODE_SSLERROR)

        except requests.exceptions.Timeout:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_RequestError, Config.Type.REQUEST_CODE_TimeOut)

        except requests.exceptions.TooManyRedirects:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_RequestError, Config.Type.REQUEST_CODE_TooManyRedirects)

        except requests.exceptions.ConnectionError:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_RequestError, Config.Type.REQUEST_CODE_ConnectionError)

        except ParseError as e:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_ParseError, e)

        except VIPError:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_VIP_Required)

        except Exception:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_UnknownError)
            
    return func