from PySide6.QtCore import Signal, QObject, Slot

from ..common._json import json_loads
from ..common.config import config

from threading import Lock
from enum import Enum
import logging
import httpx
import ssl
import os

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

_client = None
_client_lock = Lock()

_ssl_context = None
_ssl_context_lock = Lock()

def get_ssl_context():
    # httpx 默认会为每个 Client / HTTPTransport 重新构建 SSLContext，加载完整的 CA 根证书列表耗时约 170ms。
    # 由于全局的证书配置是一致的，此处只构建一次并复用，创建 Client 的开销可降至微秒级。
    global _ssl_context

    if _ssl_context is None:
        with _ssl_context_lock:
            if _ssl_context is None:
                _ssl_context = _create_ssl_context()

    return _ssl_context

def _create_ssl_context():
    # 与 httpx 默认行为保持一致：优先使用环境变量指定的证书，否则回退到 certifi 提供的证书列表
    try:
        if cert_file := os.environ.get("SSL_CERT_FILE"):
            return ssl.create_default_context(cafile = cert_file)

        if cert_dir := os.environ.get("SSL_CERT_DIR"):
            return ssl.create_default_context(capath = cert_dir)

        import certifi

        return ssl.create_default_context(cafile = certifi.where())

    except Exception:
        logger.exception("构建 SSL 上下文失败，已回退到系统默认证书")

        return ssl.create_default_context()

def get_mounts(proxies = None):
    if proxies:
        proxy_url = proxies.get("http") or proxies.get("https")

        return {
            "http://": httpx.HTTPTransport(proxy = proxy_url, retries = 5, verify = get_ssl_context()),
            "https://": httpx.HTTPTransport(proxy = proxy_url, retries = 5, verify = get_ssl_context())
        }
    else:
        return None

def _create_client():
    from .proxy import Proxy

    limits = httpx.Limits(max_connections = 10, max_keepalive_connections = 10)
    transport = httpx.HTTPTransport(retries = 3, verify = get_ssl_context())

    if config.get(config.proxy_enabled):
        logger.info("已启用代理，类型：%s，服务器：%s:%s", config.get(config.proxy_type), config.get(config.proxy_server), config.get(config.proxy_port))

    return httpx.Client(
        limits = limits,
        timeout = 5,
        mounts = get_mounts(Proxy().get_proxies()),
        transport = transport,
        follow_redirects = True,
        verify = get_ssl_context()
    )


def _apply_cookies(client_obj, cookies: dict):
    for key, value in cookies.items():
        client_obj.cookies.set(
            name = key,
            value = value,
            domain = ".bilibili.com",
            path = "/"
        )


def _load_persisted_cookies():
    return get_cookies()


def _ensure_client():
    global _client

    if _client is None:
        with _client_lock:
            if _client is None:
                _client = _create_client()
                _apply_cookies(_client, _load_persisted_cookies())

    return _client


def get_client():
    return _ensure_client()


class _LazyClientProxy:
    def __getattr__(self, name):
        return getattr(get_client(), name)

    def __repr__(self):
        return repr(get_client())


client = _LazyClientProxy()

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
    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True, json_data: dict = None, data: dict = None, content_type: str = None, extra_headers: dict = None):
        self.url = url
        self.params = params
        self.request_type = request_type
        self.response_type = response_type
        self.raise_for_status = raise_for_status
        self.json_data = json_data
        self.data = data
        self.content_type = content_type     # 供 POST 请求使用，自动设置 Content-Type 头部
        self.extra_headers = extra_headers

        self.proxies = None

    def run(self):
        self.update_headers()

        if self.proxies:
            with httpx.Client(mounts = get_mounts(self.proxies), follow_redirects = True, verify = get_ssl_context()) as temp_client:
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
                return json_loads(response.text)

            case ResponseType.BYTES:
                return response.content

            case ResponseType.HEADERS:
                return response.headers

            case ResponseType.REDIRECT_URL:
                return str(response.url)
            
            case ResponseType.RESPONSE:
                return response
    
    def update_headers(self):
        get_client().headers.update(
            {
                "Referer": "https://www.bilibili.com/",
                "User-Agent": config.get(config.user_agent)
            }
        )

        if self.content_type:
            get_client().headers["Content-Type"] = self.content_type

        else:
            # 如果没有指定 content_type，则移除可能存在的 Content-Type 头部，避免影响某些请求
            if "Content-Type" in get_client().headers:
                get_client().headers.pop("Content-Type", None)

        if self.extra_headers:
            get_client().headers.update(self.extra_headers)

class NetworkRequestWorker(SyncNetWorkRequest, QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True, json_data: dict = None, data: dict = None, content_type: str = None, extra_headers: dict = None):
        SyncNetWorkRequest.__init__(self, url, request_type, params, response_type, raise_for_status, json_data, data, content_type, extra_headers)
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
    client_obj = _ensure_client()

    _apply_cookies(client_obj, cookies)
