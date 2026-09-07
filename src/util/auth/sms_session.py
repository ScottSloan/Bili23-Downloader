"""
短信登录的纯逻辑 —— 不依赖 Qt

三步：申请极验参数 → 用户过滑块 → 拿验证结果发短信 → 输入验证码登录。

## 桌面与 WebUI 的差别只在中间那一步

滑块必须在浏览器里做（极验的 JS 只跑在网页环境）。桌面版为此绕了一大圈：
起一个本地 HTTP 服务器（`auth/server.py`，端口 2333），把 `res/html/captcha.html`
用系统浏览器打开，页面从 `/geetest/captcha/init` 取 gt / challenge，
用户过完滑块再 POST 回 `/geetest/captcha/callback`。

**WebUI 不需要这一圈** —— 它本身就是网页。前端直接拿本模块返回的 gt / challenge
调 `initGeetest`，把 `getValidate()` 的结果回传即可，既不用本地服务器，
也不用另开一个浏览器窗口。

所以这里只保留三次 HTTP 请求与参数拼装，两端共用；那圈本地服务器留在桌面侧。

## 顺序不能乱

`captcha_key` 是发短信那一步的返回值，登录时要带上。极验的 challenge / validate / seccode
则是发短信的入参 —— 拿去登录接口是没用的。这几个名字长得像，很容易接错。
"""

from typing import Optional
import logging

from ..network.request import RequestType, SyncNetWorkRequest
from .base import AuthBase

logger = logging.getLogger(__name__)

CAPTCHA_URL = ("https://passport.bilibili.com/x/passport-login/captcha"
               "?source=main-fe-header&t=0.1867987009754133")
SMS_SEND_URL = "https://passport.bilibili.com/x/passport-login/web/sms/send"
SMS_LOGIN_URL = "https://passport.bilibili.com/x/passport-login/web/login/sms"

def parse_captcha(response: dict) -> dict:
    """从 captcha 接口的返回里取出极验参数"""
    data = response["data"]

    geetest = data["geetest"]

    return {
        # token 是 B 站这一侧的，发短信时要原样带回去；gt / challenge 给极验的 JS
        "token": data["token"],
        "gt": geetest["gt"],
        "challenge": geetest["challenge"],
    }

def send_params(cid: str, tel: str, token: str, challenge: str,
                validate: str, seccode: str) -> dict:
    return {
        "cid": cid,
        "tel": tel,
        "source": "main-fe-header",
        "token": token,
        "challenge": challenge,
        "validate": validate,
        "seccode": seccode,
    }

def login_params(cid: str, tel: str, code: str, captcha_key: str) -> dict:
    return {
        "cid": cid,
        "tel": tel,
        "code": code,
        "source": "main-fe-header",
        "captcha_key": captcha_key,
        "go_url": "https://www.bilibili.com/",
    }

class SMSSession(AuthBase):
    """阻塞版的短信登录。调用方负责放到线程里"""

    def __init__(self):
        super().__init__()

        self.error = _NullSignal()

    def init_captcha(self) -> dict:
        """申请极验参数。返回 {token, gt, challenge}，交给前端去过滑块"""
        response = SyncNetWorkRequest(CAPTCHA_URL).run()

        self.check_response(response)

        return parse_captcha(response)

    def send(self, cid: str, tel: str, token: str, challenge: str,
             validate: str, seccode: str) -> dict:
        """发送验证码短信，返回登录时要用的 captcha_key"""
        params = send_params(cid, tel, token, challenge, validate, seccode)

        response = SyncNetWorkRequest(SMS_SEND_URL, request_type = RequestType.POST,
                                      params = params).run()

        self.check_response(response)

        return {"captcha_key": response["data"]["captcha_key"]}

    def login(self, cid: str, tel: str, code: str, captcha_key: str) -> dict:
        """
        用短信验证码登录

        **成功后就地把 Cookie 写进配置**：登录态由 httpx 的 cookiejar 承接，
        等调用方想起来再写就可能已经被别的请求覆盖了
        """
        params = login_params(cid, tel, code, captcha_key)

        response = SyncNetWorkRequest(SMS_LOGIN_URL, request_type = RequestType.POST,
                                      params = params).run()

        self.check_response(response)

        # 登录接口自身 code 为 0，但 data.status 非 0 时也不算成功
        # （常见于「需要二次验证」这类分支）
        status = (response.get("data") or {}).get("status", 0)

        if status != 0:
            message = (response.get("data") or {}).get("message") or "登录未完成"

            logger.warning("短信登录未完成，status=%s：%s", status, message)

            raise RuntimeError(message)

        self.update_cookies()

        return {"logged_in": True}

class _NullSignal:
    """AuthBase.on_error 要往 self.error 上发信号，纯逻辑这边没有信号可发"""

    def emit(self, *args, **kwargs) -> None:
        pass

    def connect(self, *args, **kwargs) -> None:
        pass

    def disconnect(self, *args, **kwargs) -> None:
        pass
