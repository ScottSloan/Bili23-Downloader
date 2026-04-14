from PySide6.QtCore import Signal, QObject, Slot

from util.network.proxy import Proxy
from util.common import config

from enum import Enum

import httpx
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)

def get_mounts(proxies = None):
    if proxies:
        proxy_url = proxies.get("http") or proxies.get("https")

        return {
            "http://": httpx.HTTPTransport(proxy = proxy_url, retries = 5),
            "https://": httpx.HTTPTransport(proxy = proxy_url, retries = 5)
        }
    else:
        return None

limits = httpx.Limits(max_connections = 10, max_keepalive_connections = 10)
transport = httpx.HTTPTransport(retries = 3)

client = httpx.Client(
    limits = limits,
    timeout = 5,
    mounts = get_mounts(Proxy().get_proxies()),
    transport = transport,
    follow_redirects = True
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
    RESPONSE = 5         # 返回完整的 Response 对象，供需要访问更多信息的情况使用

class SyncNetWorkRequest:
    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True, json_data: dict = None, data: dict = None, content_type: str = None):
        self.url = url
        self.params = params
        self.request_type = request_type
        self.response_type = response_type
        self.raise_for_status = raise_for_status
        self.json_data = json_data
        self.data = data
        self.content_type = content_type     # 供 POST 请求使用，自动设置 Content-Type 头部

        self.proxies = None

    def run(self):
        self.update_headers()

        if self.proxies:
            with httpx.Client(mounts = get_mounts(self.proxies), follow_redirects = True) as temp_client:
                response = temp_client.request(
                    method = self.request_type.name,
                    url = self.url,
                    params = self.params,
                    json = self.json_data,
                    headers = client.headers,
                    cookies = client.cookies,
                    data = self.data
                )
        else:
            response = client.request(
                method = self.request_type.name,
                url = self.url,
                params = self.params,
                json = self.json_data,
                headers = client.headers,
                cookies = client.cookies,
                data = self.data
            )

        if self.raise_for_status:
            response.raise_for_status()

        match self.response_type:
            case ResponseType.TEXT:
                return response.text

            case ResponseType.JSON:
                return response.json()

            case ResponseType.BYTES:
                return response.content

            case ResponseType.HEADERS:
                return response.headers

            case ResponseType.REDIRECT_URL:
                return str(response.url)
            
            case ResponseType.RESPONSE:
                return response
    
    def update_headers(self):
        client.headers.update(
            {
                "Referer": "https://www.bilibili.com/",
                "User-Agent": config.get(config.user_agent)
            }
        )

        if self.content_type:
            client.headers["Content-Type"] = self.content_type

class NetworkRequestWorker(SyncNetWorkRequest, QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True, json_data: dict = None, data: dict = None, content_type: str = None):
        SyncNetWorkRequest.__init__(self, url, request_type, params, response_type, raise_for_status, json_data, data, content_type)
        QObject.__init__(self)

    @Slot()
    def run(self):
        try:
            resp = super().run()

            self.success.emit(resp)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.proxies = None

            self.finished.emit()

    def set_proxies(self, proxies: dict):
        self.proxies = proxies

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
