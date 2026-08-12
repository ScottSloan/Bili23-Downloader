from PySide6.QtCore import QObject, Signal, Slot

from ..common.translator import Translator

from ..network.request import NetworkRequestWorker, set_client_cookies, delete_client_cookies, update_cookies as sync_cookies_from_config
from ..thread.async_ import AsyncTask
from .base import AuthBase

import json

# 登录相关的 Cookie 字段
LOGIN_COOKIE_KEYS = ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5")

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

    @staticmethod
    def parse_cookies(text: str) -> dict:
        """
        解析用户粘贴的 Cookie 请求头字符串（如 SESSDATA=xxx; bili_jct=xxx）或json格式对象
        支持分号或换行分隔。无法解析出有效字段时返回空字典。
        """
        text = text.strip()

        if text.lower().startswith("cookie:"):
            text = text[len("cookie:"):]

        cookies = {}

        try:
            # 尝试解析为 JSON 对象
            data = json.loads(text)

            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(key, str) and isinstance(value, str):
                        cookies[key] = value

                return cookies
        except Exception:
            pass

        for part in text.replace("\n", ";").split(";"):
            key, sep, value = part.partition("=")
            key, value = key.strip(), value.strip().strip('"')

            # 合法的 Cookie 名不含空白字符，借此过滤随意粘贴的无效文本
            if sep and key and not any(char.isspace() for char in key):
                cookies[key] = value

        return cookies

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
        set_client_cookies({
            key: value
            for key in LOGIN_COOKIE_KEYS
            if (value := cookies.get(key, ""))
        })

    def restore_cookies(self):
        # 移除已应用的登录 Cookie，并恢复为配置中保存的 Cookie
        self._pending_restore = False

        delete_client_cookies(LOGIN_COOKIE_KEYS)

        sync_cookies_from_config()
