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

class SyncNetWorkRequest:
    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True, json_data: dict = None, timeout: int = None):
        self.url = url
        self.params = params
        self.request_type = request_type
        self.response_type = response_type
        self.raise_for_status = raise_for_status
        self.json_data = json_data
        self.timeout = timeout

        self.proxies = None

    def run(self):
        self.update_headers()

        if self.proxies:
            with httpx.Client(mounts = get_mounts(self.proxies), timeout = self.timeout, follow_redirects = True) as temp_client:
                response = temp_client.request(
                    method = self.request_type.name,
                    url = self.url,
                    params = self.params,
                    json = self.json_data,
                    headers = client.headers,
                    cookies = client.cookies,
                )
        else:
            response = client.request(
                method = self.request_type.name,
                url = self.url,
                params = self.params,
                json = self.json_data,
                headers = client.headers,
                cookies = client.cookies,
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
    
    def update_headers(self):
        client.headers.update(
            {
                "Referer": "https://www.bilibili.com/",
                "User-Agent": config.get(config.user_agent)
            }
        )

class NetworkRequestWorker(SyncNetWorkRequest, QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True, json_data: dict = None, timeout: int = None):
        SyncNetWorkRequest.__init__(self, url, request_type, params, response_type, raise_for_status, json_data, timeout)
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

def load_cookies_from_file(cookie_file_path: str) -> bool:
    """从 Netscape 格式的 cookies 文件加载 cookies 到 httpx client"""
    import os
    
    if not cookie_file_path or not os.path.exists(cookie_file_path):
        return False
    
    try:
        loaded_count = 0
        
        with open(cookie_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue
                
                # Netscape 格式: domain	flag	path	secure	expiration	name	value
                parts = line.split('\t')
                if len(parts) >= 7:
                    domain = parts[0]
                    path = parts[2]
                    name = parts[5]
                    value = parts[6]
                    
                    client.cookies.set(
                        name=name,
                        value=value,
                        domain=domain,
                        path=path
                    )
                    loaded_count += 1
        
        return loaded_count > 0
    except Exception as e:
        return False
