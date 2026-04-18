from util.common import signal_bus, config
from util.network import client

import logging

logger = logging.getLogger(__name__)

class AuthBase:
    def __init__(self):
        pass

    def on_error(self, message: str):
        logger.error(message)

        signal_bus.emit_signal(self.error, message)
    
    def show_toast_error(self, title: str, message: str):
        logger.error("%s: %s", title, message)

        signal_bus.emit_signal(signal_bus.toast.show_long_message, *(title, message))

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "未知错误")

            logger.error("请求失败，%s: %s", message, response)

            signal_bus.emit_signal(self.error, message)

            raise Exception(message)
    
    def update_cookies(self):
        # 登录成功后更新 cookies 信息到配置中
        config.set(config.bili_jct, client.cookies.get("bili_jct", ""))
        config.set(config.DedeUserID, client.cookies.get("DedeUserID", ""))
        config.set(config.DedeUserID__ckMd5, client.cookies.get("DedeUserID__ckMd5", ""))
        config.set(config.SESSDATA, client.cookies.get("SESSDATA", ""))
        config.set(config.is_login, True)
        config.is_expired = False
