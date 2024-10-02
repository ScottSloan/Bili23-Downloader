import requests

from functools import wraps

from utils.config import Config

class ErrorCallback:
    onErrorCallbak = None

class Error:
    def __init__(self):
        pass

    def getERRORInfo(self, error_code):
        # 根据错误马获取错误信息
        match error_code:
            case Config.Type.ERROR_CODE_SSLERROR:
                # SSL 证书错误
                return self.SSLERROR()
            
            case Config.Type.ERROR_CODE_TimeOut:
                # 连接超时
                return self.TimeOut()
            
            case Config.Type.ERROR_CODE_TooManyRedirects:
                # 重定向次数过多
                return self.TooManyRedirects()
            
            case Config.Type.ERROR_CODE_ConnectionError:
                # 无法连接到服务器或 DNS 解析失败
                return self.ConnectionError()
            
            case Config.Type.ERROR_CODE_UnknownError:
                # 未知错误
                return self.UnknownError()

    def SSLERROR(self):
        return "SSL 证书错误"
    
    def TimeOut(self):
        return "连接超时"
    
    def TooManyRedirects(self):
        return "重定向次数过多"
    
    def ConnectionError(self):
        return "无法连接到服务器或 DNS 解析失败"
    
    def UnknownError(self):
        return "未知错误"

def process_exception(f):
    @wraps(f)
    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except requests.exceptions.SSLError:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_SSLERROR)

        except requests.exceptions.Timeout:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_TimeOut)

        except requests.exceptions.TooManyRedirects:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_TooManyRedirects)

        except requests.exceptions.ConnectionError:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_ConnectionError)

        except Exception:
            ErrorCallback.onErrorCallbak(Config.Type.ERROR_CODE_UnknownError)
            
    return func