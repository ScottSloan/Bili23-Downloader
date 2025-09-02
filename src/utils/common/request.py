import requests
import requests.auth
from typing import Optional, List

from utils.common.enums import ProxyMode

from utils.config import Config

class RequestUtils:
    session = requests.Session()

    @classmethod
    def request_get(cls, url: str, headers = None, proxies = None, auth = None, stream = False):
        headers, proxies, auth = cls.get_params(headers, proxies, auth)
        
        return cls.session.get(cls.get_protocol(url), headers = headers, proxies = proxies, auth = auth, stream = stream, timeout = 5)
    
    @classmethod
    def request_post(cls, url: str, headers = None, proxies = None, auth = None, params = None, json = None):
        headers, proxies, auth = cls.get_params(headers, proxies, auth)
        
        return cls.session.post(cls.get_protocol(url), headers = headers, params = params, json = json, proxies = proxies, auth = auth, timeout = 5)

    @classmethod
    def request_head(cls, url: str, headers = None, proxies = None, auth = None):
        headers, proxies, auth = cls.get_params(headers, proxies, auth)
        
        return cls.session.head(cls.get_protocol(url), headers = headers, proxies = proxies, auth = auth, timeout = 5)
    
    @classmethod
    def get_params(cls, headers = None, proxies = None, auth = None):
        if not headers:
            headers = cls.get_headers()

        if not proxies:
            proxies = cls.get_proxies()

        if not auth:
            auth = cls.get_auth()

        return headers, proxies, auth

    @staticmethod
    def get_headers(referer_url: Optional[str] = None, sessdata: Optional[str] = None, range: Optional[List[int]] = None):
        def cookie():
            if Config.Auth.buvid3:
                cookies["buvid3"] = Config.Auth.buvid3
                cookies["b_nut"] = Config.Auth.b_nut
            
            if Config.Auth.bili_ticket:
                cookies["bili_ticket"] = Config.Auth.bili_ticket

            if Config.Auth.buvid4:
                cookies["buvid4"] = Config.Auth.buvid4

        headers = {
            "User-Agent": Config.Advanced.user_agent,
        }

        cookies = {
            "CURRENT_FNVAL": "4048",
            "b_lsid": Config.Auth.b_lsid,
            "_uuid": Config.Auth.uuid,
            "buvid_fp": Config.Auth.buvid_fp
        }

        if referer_url:
            headers["Referer"] = referer_url

        if sessdata:
            cookies["SESSDATA"] = Config.User.SESSDATA
            cookies["DedeUserID"] = Config.User.DedeUserID
            cookies["DedeUserID__ckMd5"] = Config.User.DedeUserID__ckMd5
            cookies["bili_jct"] = Config.User.bili_jct

        if range:
            headers["Range"] = f"bytes={range[0]}-{range[1]}"

        cookie()

        headers["Cookie"] = ";".join([f"{key}={value}" for key, value in cookies.items()])

        return headers

    @staticmethod
    def get_proxies():
        match ProxyMode(Config.Proxy.proxy_mode):
            case ProxyMode.Disable:
                return {}
            
            case ProxyMode.Follow:
                return None
            
            case ProxyMode.Custom:
                return {
                    "http": f"{Config.Proxy.proxy_ip}:{Config.Proxy.proxy_port}",
                    "https": f"{Config.Proxy.proxy_ip}:{Config.Proxy.proxy_port}"
                }
    
    @staticmethod
    def get_auth():
        if Config.Proxy.enable_auth:
            return requests.auth.HTTPProxyAuth(Config.Proxy.auth_username, Config.Proxy.auth_password)
        else:
            return None
    
    @staticmethod
    def get_protocol(url: str):
        if not Config.Advanced.always_use_https_protocol:
            return url.replace("https://", "http://")
        
        return url