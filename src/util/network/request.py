from PySide6.QtCore import Signal, QObject, Slot

from util.network.proxy import Proxy
from util.common import config

from enum import Enum

import httpx
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)

cookies = httpx.Cookies()

limits = httpx.Limits(max_connections = 15, max_keepalive_connections = 10)
transport = httpx.HTTPTransport(retries = 3)

client = httpx.Client(
    limits = limits,
    timeout = 10,
    transport = transport,
    headers = {
        "Referer": "https://www.bilibili.com/",
        "User-Agent": config.get(config.user_agent)
    }
)

class RequestType(Enum):
    GET = 0
    POST = 1
    HEAD = 2

class ResponseType(Enum):
    TEXT = 0
    JSON = 1
    BYTES = 2
    HEADERS = 3
    REDIRECT_URL = 4

class NetworkRequestWorker(QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True, json_data: dict = None):
        super().__init__()

        self.url = url
        self.params = params
        self.request_type = request_type
        self.response_type = response_type
        self.raise_for_status = raise_for_status
        self.json_data = json_data

        self.proxies = Proxy().get_proxies()

    @Slot()
    def run(self):
        try:
            match self.request_type:
                case RequestType.GET:
                    func = client.get
                
                case RequestType.POST:
                    func = client.post
                
                case RequestType.HEAD:
                    func = client.head

            mounts = None

            if self.proxies and ('http' in self.proxies or 'https' in self.proxies):
                proxy_url = self.proxies.get('http') or self.proxies.get('https')
                mounts = {"http://": httpx.HTTPTransport(proxy = proxy_url, retries = 3), "https://": httpx.HTTPTransport(proxy = proxy_url, retries = 3)}
                
                with httpx.Client(mounts = mounts, follow_redirects = True) as temp_client:
                    res = temp_client.request(
                        method = self.request_type.name,
                        url = self.url,
                        params = self.params,
                        json = self.json_data,
                        headers = client.headers,
                        cookies = client.cookies
                    )
            else:
                if self.json_data:
                    res = func(url = self.url, params = self.params, follow_redirects = True, json = self.json_data)
                else:
                    res = func(url = self.url, params = self.params, follow_redirects = True)

            if self.raise_for_status:
                res.raise_for_status()

            match self.response_type:
                case ResponseType.TEXT:
                    resp = res.text

                case ResponseType.JSON:
                    resp = res.json()

                case ResponseType.BYTES:
                    resp = res.content

                case ResponseType.HEADERS:
                    resp = res.headers

                case ResponseType.REDIRECT_URL:
                    resp = str(res.url)

            self.success.emit(resp)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.proxies = None

            self.finished.emit()

    def set_proxies(self, proxies: dict):
        self.proxies = proxies

class SyncNetWorkRequest:
    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True):
        self.url = url
        self.params = params
        self.request_type = request_type
        self.response_type = response_type
        self.raise_for_status = raise_for_status

    def run(self):
        try:
            match self.request_type:
                case RequestType.GET:
                    func = client.get
                
                case RequestType.POST:
                    func = client.post
                
                case RequestType.HEAD:
                    func = client.head

            res = func(url = self.url, params = self.params, follow_redirects = True)

            if self.raise_for_status:
                res.raise_for_status()

            match self.response_type:
                case ResponseType.TEXT:
                    return res.text

                case ResponseType.JSON:
                    return res.json()

                case ResponseType.BYTES:
                    return res.content

                case ResponseType.HEADERS:
                    return res.headers

                case ResponseType.REDIRECT_URL:
                    return str(res.url)

        except Exception as e:
            raise e

def get_cookies():
    cookies = {
        "_uuid": config.get(config.uuid),
        "b_lsid": config.get(config.b_lsid),
        "b_nut": str(config.get(config.b_nut)),
        "bili_ticket": config.get(config.bili_ticket),
        "bili_ticket_expires": str(config.get(config.bili_ticket_expires)),
        "buvid_fp": config.get(config.buvid_fp),
        "buvid3": config.get(config.buvid3),
        "buvid4": config.get(config.buvid4),
        "CURRENT_FNVAL": "4048",
        "CURRENT_QUALITY": "0"
    }

    if config.get(config.is_login):
        cookies["bili_jct"] = config.get(config.bili_jct)
        cookies["DedeUserID"] = config.get(config.DedeUserID)
        cookies["DedeUserID__ckMd5"] = config.get(config.DedeUserID__ckMd5)
        cookies["SESSDATA"] = config.get(config.SESSDATA)

    return cookies

def update_cookies():
    cookies = get_cookies()

    for key, value in cookies.items():
        client.cookies.set(
            name = key,
            value = value,
            domain = ".bilibili.com",
            path = "/"
        )

update_cookies()
