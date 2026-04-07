from util.network.request import NetworkRequestWorker, SyncNetWorkRequest, RequestType, ResponseType
from util.common import signal_bus, config, Translator
from util.thread import AsyncTask
from util.auth import AuthBase

from pathlib import Path

class UserManager(AuthBase):
    def __init__(self):
        super().__init__()

    def init_user_info(self):
        self.get_user_info()

    def get_user_info(self):
        def on_success(response: dict):
            data: dict = response.get("data", {})

            img_url = data["wbi_img"]["img_url"]
            sub_url = data["wbi_img"]["sub_url"]

            config.set(config.img_key, Path(img_url).stem, save = False)
            config.set(config.sub_key, Path(sub_url).stem, save = False)

            if not data["isLogin"] and config.get(config.is_login):
                config.is_expired = True

                self.show_toast_error(
                    Translator.ERROR_MESSAGES("LOGIN_EXPIRED"),
                    Translator.ERROR_MESSAGES("LOGIN_EXPIRED_MESSAGE")
                )

                return
            
            if data.get("isLogin"):
                config.user_uname = data.get("uname", "")
                config.user_uid = data.get("mid")

                self.get_user_avatar(data.get("face", ""))

        def on_error(error_message: str):
            self.show_toast_error(Translator.ERROR_MESSAGES("USER_INFO_FAILED"), error_message)
        
        url = "https://api.bilibili.com/x/web-interface/nav"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

    def get_user_avatar(self, face_url: str):
        try:
            request = SyncNetWorkRequest(face_url, response_type = ResponseType.BYTES)
            response = request.run()

            signal_bus.emit_signal(signal_bus.login.update_avatar, response)
            
        except Exception as e:
            self.show_toast_error(Translator.ERROR_MESSAGES("USER_AVATAR_FAILED"), str(e))

    def logout(self):
        def on_success(response: dict):
            config.set(config.is_login, False)
            config.is_expired = False

            config.set(config.bili_jct, "")
            config.set(config.DedeUserID, "")
            config.set(config.DedeUserID__ckMd5, "")
            config.set(config.SESSDATA, "")

        def on_error(error_message: str):
            self.show_toast_error(Translator.ERROR_MESSAGES("LOGOUT_FAILED"), error_message)

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
            message = response.get("message", "Unknown error")

            self.show_toast_error(Translator.ERROR_MESSAGES("UNKNOWN_ERROR"), message)

            raise Exception(message)

user_manager = UserManager()
