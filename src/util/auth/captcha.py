from util.network import NetworkRequestWorker
from util.common import signal_bus
from util.thread import AsyncTask
from util.misc import WebPage

from .base import AuthBase

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

            CaptchaInfo.token = response["data"]["token"]
            CaptchaInfo.challenge = response["data"]["geetest"]["challenge"]
            CaptchaInfo.gt = response["data"]["geetest"]["gt"]

            if not self.server_running:
                signal_bus.login.start_server.emit()

                self.server_running = True

            WebPage.open("captcha.html")

        url = "https://passport.bilibili.com/x/passport-login/captcha?source=main-fe-header&t=0.1867987009754133"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)
