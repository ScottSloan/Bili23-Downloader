"""
扫码登录的纯逻辑 —— 不依赖 Qt

原先整条链路长在 `qrcode.py` 的 QObject 里：QTimer 轮询 + QPixmap 出图 + Qt 信号回调。
WebUI 三样都用不了 ——

- **QTimer 在没有 Qt 事件循环的进程里静默失效**（D16），轮询根本不会跑
- **QPixmap 出图那一套用不了**，那是 QtGui

所以这里只留四样东西：拼 URL、出一张 SVG 二维码、校验响应、成功后把 Cookie 写回配置。

出图这件事原先写着「不该由服务端做，前端拿 URL 自己渲染」—— 理由是不想把 QtGui
拖进容器。用 `qrcode` 出 SVG 不沾 Qt，而它本来就是基础依赖（`requirements.txt`），
于是这条理由不成立了：前端为此单独装一个二维码库，换来的只是同一张图在别处生成。
`url` 仍然照发，那是「用 App 打开」这类用法要的。
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

def render_svg(data: str) -> str:
    """
    把一段文本渲染成 SVG 二维码

    纠错等级取 `L`，与桌面版 `qrcode.py` 的 `_build_qrcode_pixmap` 一致 ——
    换一档会改变模块数，两边扫出来的图案就不是同一张了。

    输出去掉 XML 声明并把尺寸换成 `viewBox` + 100%：**带 `width="33mm"` 的话，
    浏览器里它就是 33 毫米，跟容器多大没关系**，缩不到 160×160 的框里
    """
    import io as _io
    import re

    import qrcode
    from qrcode.image.svg import SvgPathImage

    maker = qrcode.QRCode(
        version = None,
        error_correction = qrcode.constants.ERROR_CORRECT_L,
        box_size = 10,
        border = 2,
    )

    maker.add_data(data)
    maker.make(fit = True)

    buffer = _io.BytesIO()

    maker.make_image(image_factory = SvgPathImage).save(buffer)

    svg = buffer.getvalue().decode("utf-8")

    # 只留 <svg> 那一段，去掉 <?xml ...?>
    svg = svg[svg.index("<svg"):]

    svg = re.sub(r'\swidth="[^"]*"', ' width="100%"', svg, count = 1)
    svg = re.sub(r'\sheight="[^"]*"', ' height="100%"', svg, count = 1)

    return svg

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
