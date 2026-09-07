from PySide6.QtCore import QObject, Signal, Slot

from ..common.translator import Translator

from ..network.worker import NetworkRequestWorker
from ..thread.async_ import AsyncTask
from .base import AuthBase
from .session import (
    LOGIN_COOKIE_KEYS, apply_login_cookies as _apply_login_cookies,
    parse_cookies as _parse_cookies, restore_cookies as _restore_cookies,
)

class CookieLogin(AuthBase, QObject):
    login_success = Signal()

    error = Signal(str)

    def __init__(self, parent = None):
        AuthBase.__init__(self)
        QObject.__init__(self, parent)

        self._cleaned_up = False
        self._pending_restore = False #已应用待验证的 Cookie，尚未确认有效

    def cleanup(self):
        self._cleaned_up = True

        # 验证未完成时回滚
        if self._pending_restore:
            self.restore_cookies()

    def on_error(self, message: str):
        if self._cleaned_up:
            return

        super().on_error(message)

    # 解析、应用、回滚都在 auth/session.py 里，与 WebUI 共用一份
    parse_cookies = staticmethod(_parse_cookies)

    def login(self, text: str):
        cookies = self.parse_cookies(text)

        if not cookies:
            self.on_error(Translator.ERROR_MESSAGES("COOKIE_FORMAT_INVALID"))
            return

        if not cookies.get("SESSDATA"):
            self.on_error(Translator.ERROR_MESSAGES("COOKIE_MISSING_SESSDATA"))
            return

        self.apply_login_cookies(cookies)

        self._pending_restore = True

        # 通过 nav 接口校验 Cookie 是否有效
        url = "https://api.bilibili.com/x/web-interface/nav"

        worker = NetworkRequestWorker(url)
        # 校验结果要回写 Cookie 与配置，连到闭包会让这些写入落在请求线程里，
        # 因此连到本对象的方法，由 Qt 排队回 GUI 线程执行
        worker.success.connect(self.on_verify_success)
        worker.error.connect(self.on_verify_error)

        AsyncTask.run(worker)

    @Slot(object)
    def on_verify_success(self, response: dict):
        if self._cleaned_up:
            return

        data: dict = response.get("data", {})

        if data.get("isLogin"):
            self._pending_restore = False

            self.update_cookies()

            self.login_success.emit()

        else:
            self.restore_cookies()

            self.on_error(Translator.ERROR_MESSAGES("COOKIE_INVALID"))

    @Slot(str)
    def on_verify_error(self, error_message: str):
        if self._cleaned_up:
            return

        self.restore_cookies()

        self.on_error(error_message)

    def apply_login_cookies(self, cookies: dict):
        _apply_login_cookies(cookies)

    def restore_cookies(self):
        # 移除已应用的登录 Cookie，并恢复为配置中保存的 Cookie
        self._pending_restore = False

        _restore_cookies()
