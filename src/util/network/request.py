from PySide6.QtCore import Signal, QObject, Slot

from ..common._json import json_loads
from ..common.config import config
from ..common.enum import ProxyMode

from threading import Lock
from enum import Enum
import logging
import ssl
import os

# 不在模块顶层导入 httpx：本模块会被解析、预览等界面模块间接引入，而导入 httpx 需要连带加载
# httpcore 等一系列模块（约 0.1 秒）。改为在真正用到的函数内导入，把这笔开销留给后台预热线程。

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

_client = None
_client_lock = Lock()

_ssl_context = None
_ssl_context_lock = Lock()

# client.cookies 由解析、下载、封面等多个线程共用，httpx 的 Cookies 只是 cookiejar 的薄封装，
# 遍历时并没有加锁。登录流程在 GUI 线程写、请求线程在读，撞上就会抛 RuntimeError，
# 因此本模块内所有对 cookies 的读写都必须持有这把锁
_cookies_lock = Lock()

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
    import httpx

    if proxies:
        proxy_url = proxies.get("http") or proxies.get("https")

        return {
            "http://": httpx.HTTPTransport(proxy = proxy_url, retries = 5, verify = get_ssl_context()),
            "https://": httpx.HTTPTransport(proxy = proxy_url, retries = 5, verify = get_ssl_context())
        }
    else:
        return None

def _get_environment_proxies():
    # 直接复用 httpx 自身的解析实现，保证 NO_PROXY 里的域名、IPv4、IPv6、localhost 等各种写法
    # 与 httpx 默认行为完全一致，不去手抄一份容易出现偏差的解析逻辑
    try:
        from httpx._utils import get_environment_proxies

        return get_environment_proxies()

    except ImportError:
        logger.warning("当前 httpx 版本未提供 get_environment_proxies，已跳过系统代理设置")

        return {}

def get_env_mounts():
    # httpx 只在未显式传入 transport 时才会读取环境变量（Windows / macOS 上还包括系统代理设置）中的代理，
    # 见 httpx._client 中的 allow_env_proxies = trust_env and transport is None。
    # 本项目为了设置 retries 并复用全局 SSLContext，一律显式传入 transport，系统代理因此被静默绕过：
    # 用户明明开着代理，程序却直连 bilibili，部分网络环境下会被服务端重置连接（Error 10054），
    # 表现为二维码登录等请求直接失败。这里把系统代理手动还原成 mounts，补回 httpx 的默认行为。
    import httpx

    mounts = {}

    for pattern, proxy_url in _get_environment_proxies().items():
        if proxy_url is None:
            # NO_PROXY 命中的地址，None 表示改用 Client 的默认 transport，即直连
            mounts[pattern] = None
        else:
            try:
                # httpx 对 http(s) 代理不使用 retries，此处与 get_mounts 一样只依赖代理本身的连接行为
                mounts[pattern] = httpx.HTTPTransport(proxy = proxy_url, verify = get_ssl_context())

            except Exception as e:
                # httpx 不认识的代理协议（如 socks4）会抛 ValueError，socks5 缺少 socksio 依赖时会抛 ImportError。
                # 这里只跳过这一条挂载，不要让整个 Client 创建失败，该地址的行为退化为直连
                logger.warning("系统代理挂载 %s 创建失败，已忽略：%s", pattern, e)

    return mounts or None

def get_proxy_mounts():
    # 按用户选择的代理模式生成 httpx Client 使用的 mounts，解析与下载共用同一套判定：
    # 不启用代理 → None（直连）；使用系统代理 → 从环境变量还原；手动设置 → 使用程序内配置的代理服务器
    from .proxy import Proxy

    match config.get(config.proxy_mode):
        case ProxyMode.MANUAL:
            return get_mounts(Proxy().get_proxies())

        case ProxyMode.SYSTEM:
            return get_env_mounts()

        case _:
            return None

def _create_client():
    import httpx

    # 封面加载线程池上限就有 16，叠加解析线程后并发请求数远超 10。
    # 连接数不够时后来的请求要排队等空闲连接，而排队时间同样计入超时，
    # 批量解析边下载时很容易把解析请求本身拖成 PoolTimeout。
    limits = httpx.Limits(max_connections = 32, max_keepalive_connections = 16)
    transport = httpx.HTTPTransport(retries = 3, verify = get_ssl_context())

    mounts = get_proxy_mounts()

    match config.get(config.proxy_mode):
        case ProxyMode.MANUAL:
            logger.info("已启用手动代理，类型：%s，服务器：%s:%s", config.get(config.proxy_type), config.get(config.proxy_server), config.get(config.proxy_port))

        case ProxyMode.SYSTEM:
            # 系统代理地址可能带有账号密码，不写进日志
            logger.info("已启用系统代理，挂载数量：%s", len(mounts) if mounts else 0)

    return httpx.Client(
        limits = limits,
        # 连接、读写仍为 5s；等待空闲连接单独放宽，避免高并发下把排队算成请求超时
        timeout = httpx.Timeout(5.0, pool = 30.0),
        mounts = mounts,
        transport = transport,
        follow_redirects = True,
        verify = get_ssl_context()
    )


def _apply_cookies(client_obj, cookies: dict):
    with _cookies_lock:
        for key, value in cookies.items():
            client_obj.cookies.set(
                name = key,
                value = value,
                domain = ".bilibili.com",
                path = "/"
            )


def set_client_cookies(cookies: dict):
    # 供登录流程写入 Cookie，写入必须走这里，不要直接操作 client.cookies
    _apply_cookies(_ensure_client(), cookies)


def delete_client_cookies(keys, domain: str = ".bilibili.com", path: str = "/"):
    client_obj = _ensure_client()

    with _cookies_lock:
        for key in keys:
            try:
                client_obj.cookies.delete(key, domain = domain, path = path)

            except KeyError:
                pass


def snapshot_client_cookies() -> dict:
    # 遍历 cookiejar 取快照。httpx 的 Cookies 不是线程安全的，读取时同样要持锁，
    # 否则与登录流程的写入撞上会抛 RuntimeError
    with _cookies_lock:
        return dict(_ensure_client().cookies)


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
        import httpx

        headers = self.get_headers()

        if self.proxies:
            # 临时 client 没有全局 client 的 cookiejar，需要带一份快照过去
            with httpx.Client(mounts = get_mounts(self.proxies), follow_redirects = True, verify = get_ssl_context()) as temp_client:
                response = temp_client.request(
                    method = self.request_type.name,
                    url = self.url,
                    params = self.params,
                    json = self.json_data,
                    headers = headers,
                    cookies = snapshot_client_cookies(),
                    data = self.data
                )
        else:
            # 不再传 cookies = client.cookies：httpx 会把请求的 cookies 与 client 自身的
            # cookiejar 合并，传自己等于让每次请求都在子线程里多遍历一遍 cookiejar，
            # 与登录写入或响应回写的 Set-Cookie 撞上就会抛 RuntimeError。
            # 省略该参数时 client 本就会带上自己的 Cookie，行为不变
            response = client.request(
                method = self.request_type.name,
                url = self.url,
                params = self.params,
                json = self.json_data,
                headers = headers,
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
    
    def get_headers(self):
        # 全部逐请求构造，不再改写全局 client 的 headers。
        # 该 client 被下载解析线程与 16 个封面线程共用，原先每次请求都要往上面
        # update / pop 一次 Content-Type，多线程并发时会互相串扰：A 刚设上的
        # Content-Type 可能被 B 删掉，httpx.Headers 本身也不是线程安全的。
        # httpx 会把 client.headers 与本次请求的 headers 合并（后者优先），
        # 所以这里只需要给出需要覆盖的部分。
        headers = {
            "Referer": "https://www.bilibili.com/",
            "User-Agent": config.get(config.user_agent)
        }

        if self.content_type:
            headers["Content-Type"] = self.content_type

        if self.extra_headers:
            headers.update(self.extra_headers)

        return headers

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
