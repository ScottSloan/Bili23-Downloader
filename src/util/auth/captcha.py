from ..network.worker import NetworkRequestWorker
from ..common.signal_bus import signal_bus
from ..thread.async_ import AsyncTask
from ..misc.web import WebPage
from .base import AuthBase
from .sms_session import CAPTCHA_URL, parse_captcha

class CaptchaInfo:
    token = ""
    challenge = ""
    gt = ""

    seccode = ""
    validate = ""

    captcha_key = ""

class Captcha(AuthBase):
    def __init__(self):
        super().__init__()

        self.server_running = False
        self._cleaned_up = False

    def cleanup(self):
        self._cleaned_up = True

        if not self.server_running:
            return

        signal_bus.login.stop_server.emit()
        self.server_running = False

    def init_geetest(self):
        def on_success(response: dict):
            if self._cleaned_up:
                return

            self.check_response(response)

            # 字段提取在 sms_session.py 里，与 WebUI 共用一份
            info = parse_captcha(response)

            CaptchaInfo.token = info["token"]
            CaptchaInfo.challenge = info["challenge"]
            CaptchaInfo.gt = info["gt"]

            if not self.server_running:
                # 延迟启动服务器，确保在获取到验证码信息后才启动，避免不必要的资源占用
                from .server import ServerManager

                signal_bus.login.start_server.emit()

                self.server_running = True

            WebPage.open("captcha.html")

        worker = NetworkRequestWorker(CAPTCHA_URL)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)
