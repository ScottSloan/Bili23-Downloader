from ..common.enum import ProxyMode

from dataclasses import dataclass
from enum import Enum

# 不在模块顶层导入 httpx，理由同 request.py：本模块的类型会被解析界面引用，而解析界面在启动路径上

# B 站风控拦截的两种表现：HTTP 层直接返回 412，或者 HTTP 200 而接口 JSON 里 code 为 -412
RISK_CONTROL_HTTP_STATUS = 412
RISK_CONTROL_API_CODE = -412

class NetworkErrorKind(Enum):
    PROXY = "proxy"                 # 请求经代理发出，在连接层面失败
    CONNECTION = "connection"       # 直连时在连接层面失败
    RISK_CONTROL = "risk_control"   # 连接是通的，但请求被 B 站风控拦截

@dataclass(frozen = True)
class NetworkErrorInfo:
    kind: NetworkErrorKind

    # 取自建 client 那一刻实际生效的代理，见 request.get_client_proxy。CONNECTION 时恒为空；
    # RISK_CONTROL 时也会带上 —— 风控按 IP 判定，代理节点的出口 IP 被标记是常见原因
    proxy_mode: ProxyMode | None = None
    proxy_address: str = ""

class APIError(RuntimeError):
    """
    接口返回的 code 不为 0。

    仍是 RuntimeError 的子类，原先按 RuntimeError 捕获的地方不受影响；
    str() 也仍是接口给的 message，界面上的报错文案不变。多带一个 code，供上面的分类使用
    """
    def __init__(self, message: str, code: int):
        super().__init__(message)

        self.code = code

def _connection_level_errors():
    import httpx

    # 只认连接层面的失败。PoolTimeout 是本进程连接池排队太久，UnsupportedProtocol 是链接本身有问题，
    # 都与网络、代理无关；HTTP 状态码错误说明连接是通的，除风控的 412 外同样不在此列
    return (
        httpx.NetworkError,             # ConnectError / ReadError / WriteError / CloseError
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.ProxyError,
        httpx.RemoteProtocolError,      # 代理或中间设备掐断连接时常见的 "Server disconnected without sending a response"
    )

def _classify_one(exc: BaseException, connection_errors: tuple) -> NetworkErrorKind | None:
    import httpx

    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == RISK_CONTROL_HTTP_STATUS:
        return NetworkErrorKind.RISK_CONTROL

    if isinstance(exc, APIError) and exc.code == RISK_CONTROL_API_CODE:
        return NetworkErrorKind.RISK_CONTROL

    if isinstance(exc, connection_errors):
        # 是否经过代理由调用方再判断
        return NetworkErrorKind.CONNECTION

    return None

def classify_network_error(exc: BaseException) -> NetworkErrorInfo | None:
    """
    判断一次请求失败是否属于网络问题，以及代理是否牵涉其中。不是网络问题时返回 None。

    最常见的场景：程序默认跟随系统代理，代理软件退出后系统代理设置却没有被还原，
    此时所有请求都会撞在一个已经没人监听的本地端口上，报出「由于目标计算机积极拒绝，无法连接」。
    这句报错对用户毫无指向性，原样弹出去，用户只会以为是程序或 B 站出了问题。

    只要请求经过了代理，连接层面的失败一律先归到代理上：代理软件退出、端口变更、规则把 B 站
    转发到失效节点，都会表现为这几类异常，而让用户先排查代理几乎不会走弯路。

    被风控拦截（412）单独成类：连接本身没问题，重试也无济于事，只能换网络环境或等一段时间。
    """
    from .request import get_client_proxy

    connection_errors = _connection_level_errors()
    seen = set()
    kind = None

    # 解析器可能把底层异常包一层再抛（raise ... from e，或在 except 块里抛出新异常），沿异常链往下找
    while exc is not None and id(exc) not in seen:
        if kind := _classify_one(exc, connection_errors):
            break

        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__

    if kind is None:
        return None

    proxy = get_client_proxy()
    proxy_mode, proxy_address = proxy or (None, "")

    if kind == NetworkErrorKind.RISK_CONTROL:
        return NetworkErrorInfo(kind, proxy_mode, proxy_address)

    if proxy:
        return NetworkErrorInfo(NetworkErrorKind.PROXY, proxy_mode, proxy_address)

    return NetworkErrorInfo(NetworkErrorKind.CONNECTION)
