"""
登录相关的纯逻辑 —— Cookie 登录、用户信息、登出

与 `qrcode_session.py` 同一个思路：把「拼 URL、校验响应、写回配置」这些两端都要做的事
抽出来，Qt 那一侧只留界面相关的壳。

原先这三条链路都长在 `NetworkRequestWorker` + `AsyncTask` 上（桌面的异步机制），
WebUI 用不了。这里给出阻塞版，服务端丢线程池里跑。

**nav 接口的返回要处理两件事**，桌面版当初把它们写在一个回调里，很容易只搬一半：

1. wbi 签名用的 `img_key` / `sub_key` —— 解析链路每次请求都要用，取不到就全线失败
2. 登录态与用户信息

所以下面 `fetch_user_info()` 两件都做，两端共用同一份。
"""

from pathlib import Path
from typing import Dict, Optional
import json
import logging

from ..common.config import config
from ..network.request import (
    RequestType, SyncNetWorkRequest, delete_client_cookies, set_client_cookies,
    update_cookies as sync_cookies_from_config,
)
from .base import AuthBase

logger = logging.getLogger(__name__)

NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
LOGOUT_URL = "https://passport.bilibili.com/login/exit/v2"

# 登录相关的 Cookie 字段
LOGIN_COOKIE_KEYS = ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5")

def parse_cookies(text: str) -> dict:
    """
    解析用户粘贴的 Cookie

    支持三种形态：请求头原文（`SESSDATA=xxx; bili_jct=xxx`）、JSON 对象、换行分隔。
    解析不出有效字段时返回空字典 —— 这是 `cookie_login.py` 原本的实现，原样搬过来共用
    """
    text = (text or "").strip()

    if text.lower().startswith("cookie:"):
        text = text[len("cookie:"):]

    cookies = {}

    try:
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

def apply_login_cookies(cookies: dict) -> None:
    set_client_cookies({
        key: value
        for key in LOGIN_COOKIE_KEYS
        if (value := cookies.get(key, ""))
    })

def restore_cookies() -> None:
    """把刚应用上去的登录 Cookie 撤掉，恢复成配置里存的那份"""
    delete_client_cookies(LOGIN_COOKIE_KEYS)

    sync_cookies_from_config()

def ensure_wbi_keys() -> bool:
    """
    确保 wbi 的签名密钥可用，缺了就去 nav 接口取一次

    **这不是可有可无的**：投稿视频的 playurl 要 wbi 签名，而 `enc_wbi` 在密钥为空时
    抛的是 `IndexError: string index out of range` —— 一句完全看不出病因的报错。
    桌面版启动时会调 `init_user_info()` 顺带把密钥取回来，服务端没有那一步，
    所以在真正要用之前自己保证一次。

    已经有密钥时不发请求，可以放心地在每次解析、预览前调
    """
    if config.get(config.img_key) and config.get(config.sub_key):
        return True

    try:
        LoginSession().fetch_user_info()

    except Exception as e:
        logger.warning("获取 wbi 签名密钥失败：%s", e)

        return False

    return bool(config.get(config.img_key) and config.get(config.sub_key))

class LoginSession(AuthBase):
    """阻塞版的登录操作。调用方负责放到线程里"""

    def __init__(self):
        super().__init__()

        self.error = _NullSignal()

    # ---- 用户信息 ----

    def fetch_user_info(self) -> dict:
        """
        取 nav 接口，顺带把 wbi 的 img_key / sub_key 落进配置

        **wbi key 那一步不能省**：解析链路的每个请求都要用它签名，
        少了它整条解析会以「请求失败」的形式失败，而原因完全看不出来
        """
        response = SyncNetWorkRequest(NAV_URL).run()

        data: dict = response.get("data", {}) or {}

        wbi = data.get("wbi_img") or {}

        if wbi.get("img_url") and wbi.get("sub_url"):
            config.set(config.img_key, Path(wbi["img_url"]).stem, save = False)
            config.set(config.sub_key, Path(wbi["sub_url"]).stem, save = False)

        if data.get("isLogin"):
            config.user_uname = data.get("uname", "")
            config.user_uid = data.get("mid")
            config.user_face_url = data.get("face", "")

            config.is_expired = False

            return {
                "logged_in": True,
                "uname": config.user_uname,
                "uid": config.user_uid,
                "face": config.user_face_url,
                "vip_status": data.get("vipStatus", 0),
                "level": (data.get("level_info") or {}).get("current_level", 0),
            }

        if config.get(config.is_login):
            # 配置里说已登录，接口说没有 —— Cookie 过期了。
            # 这里不清配置：用户可能只是网络异常，清掉会让他重新登录一次
            config.is_expired = True

        return {"logged_in": False, "expired": bool(config.get(config.is_login))}

    # ---- Cookie 登录 ----

    def login_with_cookie(self, text: str) -> dict:
        """
        用粘贴的 Cookie 登录

        先把 Cookie 应用到 client 上再拿 nav 验证，**验证失败必须回滚** ——
        不回滚的话，一串无效 Cookie 会一直挂在 client 上，
        之后所有请求都带着它，表现为「登录过但什么都取不到」
        """
        cookies = parse_cookies(text)

        if not cookies:
            raise ValueError("COOKIE_FORMAT_INVALID")

        if not cookies.get("SESSDATA"):
            raise ValueError("COOKIE_MISSING_SESSDATA")

        apply_login_cookies(cookies)

        try:
            response = SyncNetWorkRequest(NAV_URL).run()

        except Exception:
            restore_cookies()

            raise

        if not (response.get("data") or {}).get("isLogin"):
            restore_cookies()

            raise ValueError("COOKIE_INVALID")

        self.update_cookies()

        return self.fetch_user_info()

    # ---- 登出 ----

    def logout(self) -> dict:
        params = {"biliCSRF": config.get(config.bili_jct)}

        try:
            SyncNetWorkRequest(LOGOUT_URL, request_type = RequestType.POST, params = params).run()

        except Exception as e:
            # 接口失败也要把本地登录态清掉：用户点了退出，界面上还显示已登录是更糟的结果。
            # 服务端的会话失效与否不影响本地这份 Cookie 已经不该再用
            logger.warning("调用登出接口失败，仍清除本地登录态：%s", e)

        config.set(config.is_login, False)
        config.is_expired = False

        for item in (config.bili_jct, config.DedeUserID, config.DedeUserID__ckMd5, config.SESSDATA):
            config.set(item, "")

        restore_cookies()

        config.user_uname = ""
        config.user_uid = 0
        config.user_face_url = ""

        return {"logged_in": False}

class _NullSignal:
    """AuthBase.on_error 要往 self.error 上发信号，纯逻辑这边没有信号可发"""

    def emit(self, *args, **kwargs) -> None:
        pass

    def connect(self, *args, **kwargs) -> None:
        pass

    def disconnect(self, *args, **kwargs) -> None:
        pass
