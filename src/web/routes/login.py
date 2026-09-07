"""
B 站账号登录（S3-11）

**注意区分两种登录**：`/api/auth/*` 是登进 WebUI 本身（D6 的单用户口令），
这里的 `/api/login/*` 是把 WebUI 背后的 B 站账号登上去。两者互不相干，
后者必须先通过前者的鉴权才能调用。

逻辑全在 `util/auth/qrcode_session.py` 与 `util/auth/session.py` 里，与桌面版共用。
这一层只负责把阻塞调用丢出事件循环，以及把异常翻译成 HTTP 状态码。

## 二维码图片不在服务端画

桌面版用 QPainter 画一张 QPixmap，那是因为它要往 QLabel 上贴。前端拿到 URL 自己渲染
即可 —— 省掉一次图片传输，也省掉容器里的 QtGui 依赖。

## 轮询由前端发起

桌面版是 QTimer 每秒问一次。这里不在服务端起定时器：**扫码是用户当面的动作**，
只有前端知道那个对话框还开不开着。服务端替它轮询的话，用户关掉页面之后
这个循环还会一直跑下去。

## 短信登录：WebUI 比桌面版简单一圈

滑块必须在浏览器里做（极验的 JS 只跑在网页环境）。桌面版为此起了一个本地 HTTP 服务器
（`auth/server.py`，端口 2333），把 `res/html/captcha.html` 用系统浏览器打开，
页面从 `/geetest/captcha/init` 取参数，用户过完再 POST 回 `/geetest/captcha/callback`。

**WebUI 不需要这一圈** —— 它本身就是网页。三步走：

1. `POST /api/login/sms/captcha` 拿 `{token, gt, challenge}`
2. 前端照 `res/html/captcha.html` 里那套调 `initGeetest`，把 `getValidate()` 的
   `geetest_challenge / geetest_validate / geetest_seccode` 回传
3. `POST /api/login/sms/send` 发短信拿 `captcha_key`，再 `POST /api/login/sms/verify` 登录

**别把这几个参数搞混**：challenge / validate / seccode 是**发短信**那一步的入参，
captcha_key 是发短信的**返回值**、登录时才用。名字长得像，接错了接口只会回一句
「参数错误」。
"""

from typing import Optional
import asyncio
import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.auth.qrcode_session import QRCodeSession
from util.auth.session import LoginSession
from util.auth.sms_session import SMSSession
from util.common.config import config
from util.thread import background

from ..schemas import (
    BilibiliStatus, CaptchaInfo, QRCodeInfo, QRCodeStatus, RegionList, SMSSendResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["login"])

# 这些操作都要发网络请求，阻塞几百毫秒到几秒不等，绝不能在事件循环里直接跑
async def _off_loop(func, *args):
    return await asyncio.wrap_future(background.submit(func, *args))

class CookieLoginRequest(BaseModel):
    # 粘贴的 Cookie 可能是一整段 JSON，给足长度
    text: str = Field(min_length = 1, max_length = 8192)

class SMSSendRequest(BaseModel):
    cid: str = Field(min_length = 1, max_length = 8)
    tel: str = Field(min_length = 1, max_length = 32)
    token: str = Field(min_length = 1, max_length = 256)
    challenge: str = Field(min_length = 1, max_length = 256)
    # **字段名不能直接叫 validate**：那是 pydantic BaseModel 自己的属性，
    # 会被它警告并遮蔽。用别名把对外的 JSON 键保持成极验回调里那个名字
    validate_code: str = Field(min_length = 1, max_length = 512, alias = "validate")
    seccode: str = Field(min_length = 1, max_length = 512)

class SMSVerifyRequest(BaseModel):
    cid: str = Field(min_length = 1, max_length = 8)
    tel: str = Field(min_length = 1, max_length = 32)
    code: str = Field(min_length = 1, max_length = 16)
    captcha_key: str = Field(min_length = 1, max_length = 512)

@router.get("/login/status", response_model = BilibiliStatus)
async def login_status(refresh: bool = Query(default = False)):
    """
    当前的 B 站登录态

    `refresh = True` 时去问一次 nav 接口（顺带刷新 wbi 签名用的 key）；
    否则只报配置里存的状态，不发请求 —— 前端轮询这个接口时不该每次都打一次 B 站
    """
    if refresh:
        session = LoginSession()

        try:
            return await _off_loop(session.fetch_user_info)

        except Exception as e:
            logger.warning("获取用户信息失败：%s", e)

            return JSONResponse({"detail": str(e)}, status_code = 502)

    return {
        "logged_in": bool(config.get(config.is_login)),
        "expired": bool(getattr(config, "is_expired", False)),
        "uname": config.user_uname or "",
        "uid": config.user_uid or 0,
        "face": config.user_face_url or "",
    }

@router.post("/login/qrcode", response_model = QRCodeInfo)
async def create_qrcode():
    """
    申请一个登录二维码

    返回的 `url` 由前端渲染成二维码，`key` 用于后续轮询
    """
    session = QRCodeSession()

    try:
        return await _off_loop(session.generate)

    except Exception as e:
        logger.warning("申请登录二维码失败：%s", e)

        return JSONResponse({"detail": str(e)}, status_code = 502)

@router.get("/login/qrcode/poll", response_model = QRCodeStatus)
async def poll_qrcode(key: str = Query(min_length = 1, max_length = 256)):
    """
    查一次扫码状态

    状态为 `success` 时 Cookie 已经写进配置了（在 `parse_poll` 里就地完成），
    前端接着调 `/api/login/status?refresh=true` 取用户信息即可
    """
    session = QRCodeSession()

    try:
        return await _off_loop(session.poll, key)

    except Exception as e:
        logger.warning("查询扫码状态失败：%s", e)

        return JSONResponse({"detail": str(e)}, status_code = 502)

@router.post("/login/cookie", response_model = BilibiliStatus)
async def login_with_cookie(payload: CookieLoginRequest):
    """用粘贴的 Cookie 登录。验证不通过会回滚，不会把无效 Cookie 留在 client 上"""
    session = LoginSession()

    try:
        return await _off_loop(session.login_with_cookie, payload.text)

    except ValueError as e:
        # 格式不对、缺 SESSDATA、验证不通过 —— 都是用户输入的问题，400 而不是 502
        return JSONResponse({"detail": str(e)}, status_code = 400)

    except Exception as e:
        logger.warning("Cookie 登录失败：%s", e)

        return JSONResponse({"detail": str(e)}, status_code = 502)

@router.post("/login/logout", response_model = BilibiliStatus)
async def logout():
    """退出 B 站账号。**不影响 WebUI 自身的会话**"""
    session = LoginSession()

    return await _off_loop(session.logout)

# ---------------- 短信登录 ----------------

@router.get("/login/sms/regions", response_model = RegionList)
async def sms_regions():
    """国家/地区区号。与桌面版下拉框用的是同一份数据"""
    from util.common.data import cid_list

    return {"regions": cid_list}

@router.post("/login/sms/captcha", response_model = CaptchaInfo)
async def sms_captcha():
    """
    申请极验参数

    前端拿 `gt` 与 `challenge` 调 `initGeetest`（写法见 `src/res/html/captcha.html`），
    `token` 原样留着，发短信时要带回去
    """
    session = SMSSession()

    try:
        return await _off_loop(session.init_captcha)

    except Exception as e:
        logger.warning("申请极验参数失败：%s", e)

        return JSONResponse({"detail": str(e)}, status_code = 502)

@router.post("/login/sms/send", response_model = SMSSendResult)
async def sms_send(payload: SMSSendRequest):
    """发送验证码短信。返回的 captcha_key 登录时要用"""
    session = SMSSession()

    try:
        return await _off_loop(session.send, payload.cid, payload.tel, payload.token,
                               payload.challenge, payload.validate_code, payload.seccode)

    except Exception as e:
        logger.warning("发送验证码失败：%s", e)

        # 手机号不对、滑块过期这类都由 B 站判定并回一句话，原样透给前端
        return JSONResponse({"detail": str(e)}, status_code = 400)

@router.post("/login/sms/verify", response_model = BilibiliStatus)
async def sms_verify(payload: SMSVerifyRequest):
    """用收到的验证码完成登录"""
    session = SMSSession()

    try:
        await _off_loop(session.login, payload.cid, payload.tel,
                        payload.code, payload.captcha_key)

    except Exception as e:
        logger.warning("短信登录失败：%s", e)

        return JSONResponse({"detail": str(e)}, status_code = 400)

    # 登录成功后顺手把用户信息与 wbi key 取回来，省前端一次往返
    return await _off_loop(LoginSession().fetch_user_info)
