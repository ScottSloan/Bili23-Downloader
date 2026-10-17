from ..common.enum import ProxyMode

from dataclasses import dataclass
from enum import Enum

# 不在模块顶层导入 httpx，理由同 request.py：本模块的类型会被解析界面引用，而解析界面在启动路径上

class NetworkErrorKind(Enum):
    PROXY = "proxy"                 # 请求经代理发出，在连接层面失败
    CONNECTION = "connection"       # 直连时在连接层面失败

@dataclass(frozen = True)
class NetworkErrorInfo:
    kind: NetworkErrorKind

    # 仅 PROXY 时有值，取自建 client 那一刻实际生效的代理，见 request.get_client_proxy
    proxy_mode: ProxyMode | None = None
    proxy_address: str = ""

def _connection_level_errors():
    import httpx

    # 只认连接层面的失败。PoolTimeout 是本进程连接池排队太久，UnsupportedProtocol 是链接本身有问题，
    # 都与网络、代理无关；HTTP 状态码错误（如风控返回的 412）说明连接是通的，同样不在此列
    return (
        httpx.NetworkError,             # ConnectError / ReadError / WriteError / CloseError
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.ProxyError,
        httpx.RemoteProtocolError,      # 代理或中间设备掐断连接时常见的 "Server disconnected without sending a response"
    )

def classify_network_error(exc: BaseException) -> NetworkErrorInfo | None:
    """
    判断一次请求失败是否属于网络问题，以及代理是否牵涉其中。不是网络问题时返回 None。

    最常见的场景：程序默认跟随系统代理，代理软件退出后系统代理设置却没有被还原，
    此时所有请求都会撞在一个已经没人监听的本地端口上，报出「由于目标计算机积极拒绝，无法连接」。
    这句报错对用户毫无指向性，原样弹出去，用户只会以为是程序或 B 站出了问题。

    只要请求经过了代理，连接层面的失败一律先归到代理上：代理软件退出、端口变更、规则把 B 站
    转发到失效节点，都会表现为这几类异常，而让用户先排查代理几乎不会走弯路。
    """
    from .request import get_client_proxy

    errors = _connection_level_errors()
    seen = set()

    # 解析器可能把底层异常包一层再抛（raise ... from e，或在 except 块里抛出新异常），沿异常链往下找
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, errors):
            break

        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__

    else:
        return None

    if proxy := get_client_proxy():
        proxy_mode, proxy_address = proxy

        return NetworkErrorInfo(NetworkErrorKind.PROXY, proxy_mode, proxy_address)

    return NetworkErrorInfo(NetworkErrorKind.CONNECTION)
