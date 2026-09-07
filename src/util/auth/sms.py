from PySide6.QtCore import QObject, Signal, Slot

from ..network.request import RequestType
from ..network.worker import NetworkRequestWorker
from ..common.signal_bus import signal_bus
from ..thread.async_ import AsyncTask

from .captcha import CaptchaInfo
from .base import AuthBase
from .sms_session import SMS_LOGIN_URL, SMS_SEND_URL, login_params, send_params

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
        # 参数拼装在 sms_session.py 里，与 WebUI 共用一份
        params = send_params(
            cid = SMSInfo.cid,
            tel = SMSInfo.tel,
            token = CaptchaInfo.token,
            challenge = CaptchaInfo.challenge,
            validate = CaptchaInfo.validate,
            seccode = CaptchaInfo.seccode
        )

        worker = NetworkRequestWorker(SMS_SEND_URL, request_type = RequestType.POST, params = params)
        # 连到本对象的方法而非闭包，由 Qt 排队回 GUI 线程，避免在请求线程里改动全局登录状态
        worker.success.connect(self.on_send_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    @Slot(object)
    def on_send_success(self, response: dict):
        if self._cleaned_up:
            return

        try:
            self.check_response(response)

        except RuntimeError:
            # check_response 内部已经发出过 error 信号
            return

        CaptchaInfo.captcha_key = response["data"]["captcha_key"]

        self.sms_sent.emit()

    def login(self):
        params = login_params(
            cid = SMSInfo.cid,
            tel = SMSInfo.tel,
            code = SMSInfo.verification_code,
            captcha_key = CaptchaInfo.captcha_key
        )

        worker = NetworkRequestWorker(SMS_LOGIN_URL, request_type = RequestType.POST, params = params)
        worker.success.connect(self.on_login_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    @Slot(object)
    def on_login_success(self, response: dict):
        if self._cleaned_up:
            return

        try:
            self.check_response(response)

        except RuntimeError:
            return

        self.update_cookies()

        self.sms_login_success.emit()

    def update_cid_tel(self, cid: str, tel: str):
        SMSInfo.cid = cid
        SMSInfo.tel = tel

    def update_verification_code(self, code: str):
        SMSInfo.verification_code = code
