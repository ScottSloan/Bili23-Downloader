from ..common.enum import ToastNotificationCategory
from ..common.signal_bus import signal_bus
from ..common.config import config
from ..common.runtime import runtime
from ..network.request import snapshot_client_cookies

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def store_wbi_keys(data: dict) -> bool:
    """
    从 nav 响应里取出 wbi 签名密钥写入配置，返回是否拿到。

    这两个 key 与登录态无关（匿名请求一样要签名），但只有 nav 接口会返回它们。
    因此每一处拿到 nav 响应的地方都顺手回写一次：重复写入没有代价，却能把
    「启动时那次请求失败」的场景交给之后任意一次成功的请求救回来。

    以返回值而不是异常告知结果，是因为调用方对「没拿到」的反应并不相同：
    有的要提示用户，有的只需静默跳过。

    写成模块级函数而不是 AuthBase 的方法，是因为解析层也要用它 ——
    在那里补取密钥时手里同样是这一份 nav 响应，没必要为此实例化一个 auth 对象。
    """
    wbi_img: dict = (data or {}).get("wbi_img") or {}

    img_url = wbi_img.get("img_url", "")
    sub_url = wbi_img.get("sub_url", "")

    if not img_url or not sub_url:
        return False

    # save = False：不落盘。这两个 key 是会话级的，存下去只会留下一份过期密钥，
    # 下次启动拿它去签名换回来一个语焉不详的 -403。
    #
    # 这也让本函数可以安全地在解析线程上被调用（补取密钥那条路）：不落盘时
    # config.set 只是一次属性赋值，不碰配置文件，不必额外加锁
    config.set(config.img_key, Path(img_url).stem, save = False)
    config.set(config.sub_key, Path(sub_url).stem, save = False)

    return True

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
        runtime.auth.is_expired = False
