"""
扫码登录的纯逻辑 —— 不依赖 Qt

原先整条链路长在 `qrcode.py` 的 QObject 里：QTimer 轮询 + QPixmap 出图 + Qt 信号回调。
WebUI 三样都用不了 ——

- **QTimer 在没有 Qt 事件循环的进程里静默失效**（D16），轮询根本不会跑
- **二维码图片就不该由服务端画**。前端拿到 URL 自己渲染即可，省掉一次图片传输，
  也省掉容器里的 QtGui 依赖

所以这里只留三样东西：拼 URL、校验响应、成功后把 Cookie 写回配置。
桌面侧的 `qrcode.py` 复用它们，仍旧用自己的 QTimer 与 NetworkRequestWorker 保持异步。

## 轮询的节奏由调用方定

不在这里内置定时器：桌面是 QTimer，服务端是前端自己按需来问。
把节奏塞进这一层只会让两边都得绕开它。
"""

from typing import Optional, Tuple
from urllib.parse import urlencode
import logging

from ..common.enum import QRCodeScanStatus
from ..network.request import SyncNetWorkRequest
from .base import AuthBase

logger = logging.getLogger(__name__)

GENERATE_PARAMS = {
    "source": "main-fe-header",
    "go_url": "https://www.bilibili.com/",
    "web_location": "333.1007"
}

def generate_url() -> str:
    return ("https://passport.bilibili.com/x/passport-login/web/qrcode/generate?"
            + urlencode(GENERATE_PARAMS))

def poll_url(qrcode_key: str) -> str:
    return ("https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key="
            + str(qrcode_key))

class QRCodeSession(AuthBase):
    """
    一次扫码登录的会话

    阻塞执行，调用方自行决定放在哪个线程上。服务端用 `asyncio.to_thread` 之类丢出去，
    别在事件循环里直接调
    """

    def __init__(self):
        super().__init__()

        self.qrcode_url = ""
        self.qrcode_key = ""

        # AuthBase.on_error 会往 self.error 上发信号，服务端这边没有信号可发，
        # 让它落到一个空实现上即可 —— 错误由异常向上传
        self.error = _NullSignal()

    # ---- 响应处理：两端共用 ----

    def parse_generate(self, response: dict) -> Tuple[str, str]:
        """从 generate 接口的返回里取出二维码 URL 与轮询用的 key"""
        self.check_response(response)

        data = response["data"]

        self.qrcode_url = data["url"]
        self.qrcode_key = data["qrcode_key"]

        return self.qrcode_url, self.qrcode_key

    def parse_poll(self, response: dict) -> int:
        """
        从 poll 接口的返回里取出扫码状态

        **扫码成功时要在这里就把 Cookie 落到配置**：登录态是靠 httpx 的 cookiejar
        承接的，等调用方想起来再写就可能已经被别的请求覆盖了
        """
        self.check_response(response)

        code = response["data"]["code"]

        if code == QRCodeScanStatus.SUCCESS:
            self.update_cookies()

        return code

    # ---- 阻塞版：服务端用 ----

    def generate(self) -> dict:
        response = SyncNetWorkRequest(generate_url()).run()

        url, key = self.parse_generate(response)

        return {"url": url, "key": key}

    def poll(self, qrcode_key: str = None) -> dict:
        key = qrcode_key or self.qrcode_key

        if not key:
            raise RuntimeError("尚未生成二维码")

        response = SyncNetWorkRequest(poll_url(key)).run()

        code = self.parse_poll(response)

        return {
            "code": int(code),
            "status": _status_name(code),
            "message": response.get("data", {}).get("message", ""),
        }

class _NullSignal:
    """
    占位的信号

    `AuthBase.on_error` 会 `signal_bus.emit_signal(self.error, ...)`，桌面侧那个
    `self.error` 是 Qt 信号。纯逻辑这边没有，给一个什么都不做的对象顶上，
    比在 AuthBase 里加分支干净
    """

    def emit(self, *args, **kwargs) -> None:
        pass

    def connect(self, *args, **kwargs) -> None:
        pass

    def disconnect(self, *args, **kwargs) -> None:
        pass

def _status_name(code: int) -> str:
    """状态码转成名字，前端不必再查一遍枚举"""
    try:
        return QRCodeScanStatus(code).name.lower()

    except ValueError:
        return "unknown"
