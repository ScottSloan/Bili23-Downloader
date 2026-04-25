from PySide6.QtCore import QObject, Signal

from util.network import NetworkRequestWorker, RequestType
from util.common import signal_bus
from util.thread import AsyncTask

from .captcha import CaptchaInfo
from .base import AuthBase

class SMSInfo:
    cid = ""
    tel = ""

    verification_code = ""

    countdown = 60

class SMS(AuthBase, QObject):
    sms_sent = Signal()
    sms_login_success = Signal()

    error = Signal(str)

    def __init__(self, parent = None):
        AuthBase.__init__(self)
        QObject.__init__(self, parent)

        self._cleaned_up = False

        signal_bus.login.send_sms.connect(self.send)

    def cleanup(self):
        self._cleaned_up = True

        try:
            signal_bus.login.send_sms.disconnect(self.send)
        except Exception:
            pass

    def on_error(self, message: str):
        if self._cleaned_up:
            return

        super().on_error(message)

    def send(self):
        def on_success(response: dict):
            if self._cleaned_up:
                return

            self.check_response(response)

            CaptchaInfo.captcha_key = response["data"]["captcha_key"]

            self.sms_sent.emit()

        params = {
                "cid": SMSInfo.cid,
                "tel": SMSInfo.tel,
                "source": "main-fe-header",
                "token": CaptchaInfo.token,
                "challenge": CaptchaInfo.challenge,
                "validate": CaptchaInfo.validate,
                "seccode": CaptchaInfo.seccode
            }

        url = "https://passport.bilibili.com/x/passport-login/web/sms/send"

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, params = params)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    def login(self):
        def on_success(response: dict):
            if self._cleaned_up:
                return

            self.check_response(response)

            self.update_cookies()

            self.sms_login_success.emit()

        params = {
                "cid": SMSInfo.cid,
                "tel": SMSInfo.tel,
                "code": SMSInfo.verification_code,
                "source": "main-fe-header",
                "captcha_key": CaptchaInfo.captcha_key,
                "go_url": "https://www.bilibili.com/"
            }
        
        url = "https://passport.bilibili.com/x/passport-login/web/login/sms"

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, params = params)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    def update_cid_tel(self, cid: str, tel: str):
        SMSInfo.cid = cid
        SMSInfo.tel = tel

    def update_verification_code(self, code: str):
        SMSInfo.verification_code = code
