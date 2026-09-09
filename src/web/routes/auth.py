"""
登录 / 登出 / 会话查询（D6）

单用户，用户名 + 口令换 session cookie。
"""

import asyncio
import logging
import time

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.common.config import config

from ..schemas import LogoutResult, SessionInfo
from ..security import SESSION_COOKIE, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["auth"])

# 连续失败后的锁定阈值与时长。单用户服务没有「换个账号试」的余地，
# 因此按来源 IP 记账就够了。不做持久化：进程重启即清零，
# 而重启需要能碰到服务器，那种情况下已经不是这道防线该管的事了
MAX_FAILURES = 5
LOCKOUT_SECONDS = 300

_failures: dict[str, list[float]] = {}

# 口令长度下限。上限只是防着有人往里灌几兆的正文，PBKDF2 本身不在乎长度
MIN_PASSWORD_LENGTH = 8

class LoginRequest(BaseModel):
    username: str = Field(min_length = 1, max_length = 128)
    password: str = Field(min_length = 1, max_length = 1024)

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length = 1, max_length = 1024)
    new_password: str = Field(min_length = MIN_PASSWORD_LENGTH, max_length = 1024)

def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"

def _record_failure(key: str) -> None:
    now = time.time()

    attempts = [t for t in _failures.get(key, []) if now - t < LOCKOUT_SECONDS]
    attempts.append(now)

    _failures[key] = attempts

def _locked_out(key: str) -> bool:
    now = time.time()

    attempts = [t for t in _failures.get(key, []) if now - t < LOCKOUT_SECONDS]

    _failures[key] = attempts

    return len(attempts) >= MAX_FAILURES

@router.post("/login", response_model = SessionInfo)
async def login(payload: LoginRequest, request: Request, response: Response):
    key = _client_key(request)

    if _locked_out(key):
        logger.warning("登录失败次数过多，暂时拒绝：%s", key)

        return JSONResponse(
            {"detail": "Too many failed attempts. Try again later.",
             "code": "TOO_MANY_ATTEMPTS"}, status_code = 429)

    expected_username = config.get(config.webui_username)
    password_hash = config.get(config.webui_password_hash)

    # PBKDF2 是刻意慢的（默认 60 万次迭代，约 200ms）。直接在协程里算会把整个事件循环
    # 卡住那么久，登录期间所有请求都得排队 —— 丢给线程池
    ok = await asyncio.to_thread(verify_password, payload.password, password_hash)

    if payload.username != expected_username or not ok:
        _record_failure(key)

        logger.warning("登录失败：%s", key)

        # 不区分「用户名不对」与「口令不对」，避免用它来枚举用户名
        return JSONResponse({"detail": "Invalid username or password",
                             "code": "INVALID_CREDENTIALS"}, status_code = 401)

    _failures.pop(key, None)

    session = request.app.state.sessions.create()

    response.set_cookie(
        SESSION_COOKIE,
        session.token,
        httponly = True,
        samesite = "lax",
        max_age = int(session.expires_at - session.created_at),
        # 不设 secure：自托管场景多数是 http 的局域网地址，设了会导致 cookie 根本存不下。
        # 需要 https 时由反向代理负责
    )

    logger.info("登录成功：%s", key)

    return {"authenticated": True, "username": expected_username}

@router.post("/logout", response_model = LogoutResult)
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)

    request.app.state.sessions.revoke(token)

    response.delete_cookie(SESSION_COOKIE)

    return {"authenticated": False}

@router.post("/password", response_model = SessionInfo)
async def change_password(payload: PasswordChangeRequest, request: Request, response: Response):
    """
    改登录口令

    这条路由**不在 `EXEMPT_PATHS` 里**，也就是说中间件已经要求过会话了。
    仍然要再验一次旧口令：会话可能是别人在这台机器上留下的（浏览器没关、cookie 还在），
    不验的话拿到一个活会话就等于能永久接管。

    改完把**所有**会话清掉再给调用方发一个新的：改口令的常见动机就是「怀疑别人也登着」，
    只留下当前这一个才对得上这个动机。代价是其他设备上要重新登录一次。
    """
    key = _client_key(request)

    if _locked_out(key):
        return JSONResponse(
            {"detail": "Too many failed attempts. Try again later.",
             "code": "TOO_MANY_ATTEMPTS"}, status_code = 429)

    password_hash = config.get(config.webui_password_hash)

    # 与登录同理：PBKDF2 是刻意慢的，放线程池里算，别卡住事件循环
    ok = await asyncio.to_thread(verify_password, payload.current_password, password_hash)

    if not ok:
        _record_failure(key)

        logger.warning("修改口令失败，旧口令不正确：%s", key)

        return JSONResponse({"detail": "Current password is incorrect",
                             "code": "INVALID_PASSWORD"}, status_code = 401)

    if payload.new_password == payload.current_password:
        return JSONResponse({"detail": "New password must differ from the current one",
                             "code": "PASSWORD_UNCHANGED"}, status_code = 400)

    _failures.pop(key, None)

    encoded = await asyncio.to_thread(hash_password, payload.new_password)

    config.set(config.webui_password_hash, encoded)

    sessions = request.app.state.sessions

    sessions.clear()

    session = sessions.create()

    response.set_cookie(
        SESSION_COOKIE,
        session.token,
        httponly = True,
        samesite = "lax",
        max_age = int(session.expires_at - session.created_at),
    )

    logger.info("登录口令已修改，其余会话全部失效：%s", key)

    return {"authenticated": True, "username": config.get(config.webui_username)}

@router.get("/session", response_model = SessionInfo)
async def session_state(request: Request):
    """
    查询当前是否已登录。**不需要鉴权** —— 前端要靠它决定跳不跳登录页，
    因此只回答「是 / 否」，不带任何其他信息
    """
    token = request.cookies.get(SESSION_COOKIE)

    session = request.app.state.sessions.get(token)

    if session is None:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "username": config.get(config.webui_username),
        "expires_at": session.expires_at,
    }
