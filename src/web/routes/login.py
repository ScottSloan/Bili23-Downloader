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

## 短信登录暂缺

它需要极验（geetest）的滑块验证，桌面版是开一个内嵌浏览器让用户过验证再把 token 带回来。
这套流程在 WebUI 里要重做一遍前端，不适合塞在这一批里 —— 扫码与 Cookie 两条已经够用。
"""

from typing import Optional
import asyncio
import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.auth.qrcode_session import QRCodeSession
from util.auth.session import LoginSession
from util.common.config import config
from util.thread import background

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["login"])

# 这些操作都要发网络请求，阻塞几百毫秒到几秒不等，绝不能在事件循环里直接跑
async def _off_loop(func, *args):
    return await asyncio.wrap_future(background.submit(func, *args))

class CookieLoginRequest(BaseModel):
    # 粘贴的 Cookie 可能是一整段 JSON，给足长度
    text: str = Field(min_length = 1, max_length = 8192)

@router.get("/login/status")
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

@router.post("/login/qrcode")
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

@router.get("/login/qrcode/poll")
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

@router.post("/login/cookie")
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

@router.post("/login/logout")
async def logout():
    """退出 B 站账号。**不影响 WebUI 自身的会话**"""
    session = LoginSession()

    return await _off_loop(session.logout)
