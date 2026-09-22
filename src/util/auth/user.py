from PySide6.QtCore import QObject, Slot

from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..common.config import config
from ..common.runtime import runtime

from ..network.request import NetworkRequestWorker, RequestType, ResponseType
from ..thread.async_ import AsyncTask
from .base import AuthBase

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class UserManager(AuthBase, QObject):
    def __init__(self):
        AuthBase.__init__(self)
        QObject.__init__(self)

    def init_user_info(self):
        self.get_user_info()

    def get_user_info(self):
        url = "https://api.bilibili.com/x/web-interface/nav"

        worker = NetworkRequestWorker(url)
        # 连到本对象的方法而非闭包，Qt 会把回调排队回 GUI 线程；
        # 闭包没有可识别的接收者线程，连接会退化成直连，就地跑在网络请求的子线程里
        worker.success.connect(self.on_get_user_info_success)
        worker.error.connect(self.on_get_user_info_error)

        AsyncTask.run(worker)

    @Slot(object)
    def on_get_user_info_success(self, response: dict):
        data: dict = response.get("data", {})

        img_url = data["wbi_img"]["img_url"]
        sub_url = data["wbi_img"]["sub_url"]

        config.set(config.img_key, Path(img_url).stem, save = False)
        config.set(config.sub_key, Path(sub_url).stem, save = False)

        if data.get("isLogin"):
            runtime.auth.uname = data.get("uname", "")
            runtime.auth.uid = data.get("mid")

            self.get_user_avatar(data.get("face", ""))

            signal_bus.emit_signal(signal_bus.parse.update_preview_info)

            logger.info("用户信息获取成功，用户名: %s, UID: %s", runtime.auth.uname, runtime.auth.uid)

        else:
            if config.get(config.is_login):
                runtime.auth.is_expired = True

                self.show_toast_error(
                    Translator.ERROR_MESSAGES("LOGIN_EXPIRED"),
                    Translator.ERROR_MESSAGES("LOGIN_EXPIRED_MESSAGE")
                )

                return

            logger.warning("用户未登录，无法获取用户信息")

    @Slot(str)
    def on_get_user_info_error(self, error_message: str):
        self.show_toast_error(Translator.ERROR_MESSAGES("USER_INFO_FAILED"), error_message)

    def get_user_avatar(self, face_url: str):
        if not face_url:
            return

        request = NetworkRequestWorker(face_url, response_type = ResponseType.BYTES)
        request.success.connect(self.on_get_user_avatar_success)
        request.error.connect(self.on_get_user_avatar_error)

        AsyncTask.run(request)

    @Slot(object)
    def on_get_user_avatar_success(self, response: bytes):
        signal_bus.emit_signal(signal_bus.login.update_avatar, response)

    @Slot(str)
    def on_get_user_avatar_error(self, error_message: str):
        self.show_toast_error(Translator.ERROR_MESSAGES("USER_AVATAR_FAILED"), error_message)

    def logout(self):
        params = {
            "biliCSRF": config.get(config.bili_jct)
        }

        url = "https://passport.bilibili.com/login/exit/v2"

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, params = params)
        worker.success.connect(self.on_logout_success)
        worker.error.connect(self.on_logout_error)

        AsyncTask.run(worker)

    @Slot(object)
    def on_logout_success(self, response: dict):
        config.set(config.is_login, False)
        runtime.auth.is_expired = False

        config.set(config.bili_jct, "")
        config.set(config.DedeUserID, "")
        config.set(config.DedeUserID__ckMd5, "")
        config.set(config.SESSDATA, "")

    @Slot(str)
    def on_logout_error(self, error_message: str):
        self.show_toast_error(Translator.ERROR_MESSAGES("LOGOUT_FAILED"), error_message)

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "Unknown error")

            self.show_toast_error(Translator.ERROR_MESSAGES("UNKNOWN_ERROR"), message)

            raise RuntimeError(message)

user_manager = UserManager()
