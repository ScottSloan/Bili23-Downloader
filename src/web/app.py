"""
FastAPI 应用

**鉴权是默认开启、按需豁免的**：`/api/*` 一律要求会话，只有 `EXEMPT_PATHS` 里那几条
（登录、登录状态查询、健康检查）例外。反过来做 —— 给每个路由挂依赖 —— 迟早会漏掉一条，
而漏掉的后果是一个未鉴权的接口，这类错误不该靠人记得。

按 D16，这个进程不依赖 Qt 事件循环。整个 `web/` 包及其依赖都不得导入
QtWidgets 或 qfluentwidgets（`test/web_entry.py` 守着这一条）。
"""

from typing import Optional
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from util.common.config import config

from .security import SessionStore, SESSION_COOKIE, generate_password, hash_password
from .routes import auth as auth_routes
from .routes import system as system_routes

logger = logging.getLogger(__name__)

API_PREFIX = "/api/"

# 无需登录即可访问的路径。**只加确实不需要鉴权的**：
# 登录接口本身、查询是否已登录（前端据此决定跳不跳登录页）、健康检查
EXEMPT_PATHS = frozenset({
    "/api/auth/login",
    "/api/auth/session",
    "/api/health",
})

def ensure_password_configured() -> Optional[str]:
    """
    首次启动时生成随机口令，返回明文供调用方打印；已设过则返回 None

    **不返回给任何接口，也不写进日志文件** —— 只在控制台打印一次。
    默认口令写死（qBittorrent 早年的 adminadmin）会让暴露到公网的实例直接失守
    """
    if config.get(config.webui_password_hash):
        return None

    password = generate_password()

    config.set(config.webui_password_hash, hash_password(password))

    logger.info("首次启动，已生成随机登录口令（明文只打印到控制台，不入日志文件）")

    return password

def create_app() -> FastAPI:
    session_hours = config.get(config.webui_session_hours)

    sessions = SessionStore(ttl_seconds = session_hours * 3600)

    app = FastAPI(
        title = "Bili23 Downloader WebUI",
        version = config.app_version,
        # 文档页也在鉴权之后 —— 未登录时不该泄漏接口清单
        docs_url = "/api/docs",
        openapi_url = "/api/openapi.json",
    )

    app.state.sessions = sessions

    @app.middleware("http")
    async def require_session(request: Request, call_next):
        path = request.url.path

        if path.startswith(API_PREFIX) and path not in EXEMPT_PATHS:
            token = request.cookies.get(SESSION_COOKIE)

            if sessions.get(token) is None:
                # 用 401 而不是重定向：这是给前端的 API，重定向会让 fetch 拿到一个
                # 莫名其妙的 HTML 页面
                return JSONResponse({"detail": "Not authenticated"}, status_code = 401)

        return await call_next(request)

    app.include_router(system_routes.router, prefix = "/api")
    app.include_router(auth_routes.router, prefix = "/api/auth")

    return app
