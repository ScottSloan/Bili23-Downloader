from util.common import signal_bus, config
from util.network.request import session

import logging

logger = logging.getLogger(__name__)

class AuthBase:
    def __init__(self):
        pass

    def on_error(self, message: str):
        logger.error(message)
        
        self.error.emit(message)
    
    def show_toast_error(self, title: str, message: str):
        logger.error("%s: %s", title, message)

        signal_bus.toast.show_long_message.emit(title, message)

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "未知错误")

            logger.error("请求失败，%s: %s", message, response)
            self.error.emit(message)

            raise Exception(message)
    
    def update_cookies(self):
        config.set(config.bili_jct, session.cookies.get("bili_jct", ""))
        config.set(config.DedeUserID, session.cookies.get("DedeUserID", ""))
        config.set(config.DedeUserID__ckMd5, session.cookies.get("DedeUserID__ckMd5", ""))
        config.set(config.SESSDATA, session.cookies.get("SESSDATA", ""))
        config.set(config.is_login, True)
        config.is_expired = False
