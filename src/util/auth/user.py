from PySide6.QtGui import QPixmap

from util.network.request import NetworkRequestWorker, RequestType, ResponseType
from util.thread import AsyncTask, SyncTask
from util.auth.base import AuthBase

from util.common.signal_bus import signal_bus
from util.common.config import config

from pathlib import Path

class UserManager(AuthBase):
    def __init__(self):
        super().__init__()

    def get_user_info(self):
        def on_success(response: dict):
            data: dict = response.get("data", {})

            img_url = data["wbi_img"]["img_url"]
            sub_url = data["wbi_img"]["sub_url"]

            config.set(config.img_key, Path(img_url).stem, save = False)
            config.set(config.sub_key, Path(sub_url).stem, save = False)

            if not data["isLogin"] and config.get(config.is_login):
                config.set(config.is_expired, True, save = False)

                self.show_toast_error(
                    "登录状态失效",
                    "当前账号登录状态已失效，请重新登录"
                )

                return
            
            if data["isLogin"]:
                config.user_uname = data.get("uname", "")
                config.user_uid = data.get("mid")

                self.get_user_face(data["face"])

        def on_error(error_message: str):
            self.show_toast_error("获取用户信息失败", error_message)
        
        url = "https://api.bilibili.com/x/web-interface/nav"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

    def get_user_face(self, face_url: str):
        def on_success(response: bytes):
            avatar_pixmap = QPixmap()
            avatar_pixmap.loadFromData(response)

            config.user_avatar_pixmap = avatar_pixmap

            signal_bus.login.update_avatar.emit(avatar_pixmap)

        def on_error(error_message: str):
            self.show_toast_error("获取用户头像失败", error_message)

        worker = NetworkRequestWorker(face_url, response_type = ResponseType.BYTES)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        SyncTask.run(worker)

    def logout(self):
        def on_success(response: dict):
            config.set(config.is_login, False)
            config.set(config.is_expired, False, save = False)

            config.set(config.bili_jct, "")
            config.set(config.DedeUserID, "")
            config.set(config.DedeUserID__ckMd5, "")
            config.set(config.SESSDATA, "")

        def on_error(error_message: str):
            self.show_toast_error("退出登录失败", error_message)

        params = {
            "biliCSRF": config.get(config.bili_jct)
        }

        url = "https://passport.bilibili.com/login/exit/v2"

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, params = params)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "未知错误")

            self.show_toast_error("错误", message)

            raise Exception(message)
