from ..common.enum import ToastNotificationCategory
from ..common.signal_bus import signal_bus
from ..common.config import config
from ..network.request import snapshot_client_cookies

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

        signal_bus.emit_signal(signal_bus.toast.show_long_message, *(ToastNotificationCategory.ERROR, title, message))

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "未知错误")

            logger.error("请求失败，%s: %s", message, response)

            signal_bus.emit_signal(self.error, message)

            raise RuntimeError(message)
    
    def update_cookies(self):
        # 登录成功后更新 cookies 信息到配置中
        # 取一份快照再逐项读取，避免四次读取分别去遍历共用的 cookiejar
        cookies = snapshot_client_cookies()

        config.set(config.bili_jct, cookies.get("bili_jct", ""))
        config.set(config.DedeUserID, cookies.get("DedeUserID", ""))
        config.set(config.DedeUserID__ckMd5, cookies.get("DedeUserID__ckMd5", ""))
        config.set(config.SESSDATA, cookies.get("SESSDATA", ""))
        config.set(config.is_login, True)
        config.is_expired = False
