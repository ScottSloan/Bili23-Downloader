"""
FastAPI 应用

**鉴权是默认开启、按需豁免的**：`/api/*` 一律要求会话，只有 `EXEMPT_PATHS` 里那几条
（登录、登录状态查询、健康检查）例外。反过来做 —— 给每个路由挂依赖 —— 迟早会漏掉一条，
而漏掉的后果是一个未鉴权的接口，这类错误不该靠人记得。

按 D16，这个进程不依赖 Qt 事件循环。整个 `web/` 包及其依赖都不得导入
QtWidgets 或 qfluentwidgets（`test/web_entry.py` 守着这一条）。
"""

from contextlib import asynccontextmanager
import asyncio
from typing import Optional
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from util.common.config import config
from util.thread import background

from .aria2 import Aria2Client, Aria2Process
from .dispatch import install as install_dispatcher
from .download import (
    DownloadDriver, MergeCoordinator, Reconciler, StreamMonitor, StreamRegistry, TaskPublisher,
)
from .events import EventHub
from .security import SessionStore, SESSION_COOKIE, generate_password, hash_password
from . import static
from .routes import aria2 as aria2_routes
from .routes import events as events_routes
from .routes import files as files_routes
from .routes import login as login_routes
from .routes import parse as parse_routes
from .routes import preview as preview_routes
from .routes import settings as settings_routes
from .routes import tasks as tasks_routes
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

@asynccontextmanager
async def _base_lifespan(app: FastAPI):
    """
    与 aria2 无关的那部分：事件总线

    **不能只在带 aria2 的形态下建。** 快照与 WebSocket 属于 HTTP 层，
    aria2 起不起得来都要能用 —— 否则「aria2 未连接」这件事本身就推不到前端
    """
    hub = EventHub()
    publisher = TaskPublisher(hub)

    publisher.attach()

    app.state.events = hub
    app.state.publisher = publisher

    try:
        yield

    finally:
        # 订阅一定要解开：signal_bus 持的是强引用，不解开的话这个 hub 会一直收事件，
        # 往一个再也没人读的队列里塞，直到进程结束
        publisher.detach()

@asynccontextmanager
async def _aria2_lifespan(app: FastAPI):
    """
    拉起 aria2、连上它的 RPC，并把「下载完成 → 合并」这条链路接起来

    **aria2 起不来不阻止服务启动**：那样用户连登录页都打不开，只能看着一个起不来的进程干瞪眼。
    改成照常提供服务，由 `/api/aria2/status` 报告它不可用 —— 至少能登进来看到原因
    """
    # 必须在任何回调发生之前装好：不装的话，工作线程发出的事件会就地执行，
    # 而其中一部分（WebSocket 推送）只能在事件循环线程上做，且失败时不报错
    install_dispatcher()

    process = Aria2Process()

    client = Aria2Client(process.rpc_url, secret = process.secret)

    registry = StreamRegistry()
    monitor = StreamMonitor(client, registry)
    merges = MergeCoordinator()
    driver = DownloadDriver(client, registry, merges)
    reconciler = Reconciler(client, registry, merges)

    # aria2 报完最后一路流之后，剩下的（附加内容、合并、重命名）全在业务层。
    # 进度快照同时要往前端推 —— 一个回调两个去处，这里做扇出
    def _on_stream_changed(snapshot: dict):
        merges.on_stream_snapshot(snapshot)

        app.state.events.publish("stream.progress", snapshot)

    monitor.on_task_changed = _on_stream_changed

    # 每次轮询都要把速度与进度写回 TaskInfo，否则前端只有一个不动的进度条
    monitor.on_task_progress = driver.on_stream_progress

    merges.attach()
    driver.attach()

    app.state.aria2_process = process
    app.state.aria2 = client
    app.state.aria2_error = None
    app.state.streams = registry
    app.state.monitor = monitor
    app.state.merges = merges
    app.state.driver = driver
    app.state.reconciler = reconciler

    # aria2 崩溃重启后 gid 全部作废，必须重新对一次账，否则界面上的任务会永远停在
    # 最后一次的进度上 —— 后端还在正常响应 HTTP，这种「假活」最难查
    async def _on_reconnect():
        logger.info("aria2 已重连，重新对账")

        app.state.publisher.publish_aria2(True)

        await reconciler.run()

        # 断连期间新建的任务退回了排队，重连后要把它们推上路
        driver.schedule()

    client.on_reconnect = _on_reconnect

    if process.start():
        try:
            await client.connect(timeout = 15)

            monitor.attach()

            # 先对账再开轮询：轮询会按 registry 里的 gid 去问进度，
            # 而 registry 是内存里的，重启后要靠对账重新填起来
            await reconciler.run()

            # 对账只管「还在跑的」，排队中与已暂停的要靠这一步收进登记表 ——
            # 不收的话，上次没下完的任务重启后再也不会自己开始
            await asyncio.wrap_future(background.submit(driver.load))

            await monitor.start()

            driver.schedule()

        except Exception as e:
            app.state.aria2_error = str(e)

            logger.error("连接 aria2 失败：%s", e)

    else:
        app.state.aria2_error = "aria2c 未能启动，请确认已安装并在 PATH 中，或在配置里指定 aria2_path"

        logger.error(app.state.aria2_error)

        app.state.publisher.publish_aria2(False, app.state.aria2_error)

    try:
        yield

    finally:
        # 顺序有讲究：先停合并（里面的 FFmpeg 子进程不停掉会变成孤儿继续写输出文件），
        # 再停进度轮询，最后才断 aria2 与它的进程
        driver.detach()

        merges.shutdown()

        await monitor.stop()

        # 让 aria2 自己干净退出：它会把 .aria2 控制文件刷完整，下次续传才准。
        # terminate 在 Windows 上是硬杀（实测），没有这个机会
        if process.is_running_owned():
            try:
                await client.shutdown(force = True)

            except Exception as e:
                logger.debug("请求 aria2 退出失败，改由进程管理收尾：%s", e)

        await client.close()

        process.stop()

def _lifespan_for(with_aria2: bool):
    """事件总线永远要，aria2 那段按需叠加"""
    if not with_aria2:
        return _base_lifespan

    @asynccontextmanager
    async def _combined(app: FastAPI):
        async with _base_lifespan(app):
            async with _aria2_lifespan(app):
                yield

    return _combined

def create_app(with_aria2: bool = True) -> FastAPI:
    """
    with_aria2 = False 时不接管 aria2 的生命周期，供只关心 HTTP 层的测试使用 ——
    不加这个开关，跑一次鉴权测试就得连带拉起一个 aria2 进程
    """
    session_hours = config.get(config.webui_session_hours)

    sessions = SessionStore(ttl_seconds = session_hours * 3600)

    app = FastAPI(
        title = "Bili23 Downloader WebUI",
        version = config.app_version,
        # 文档页也在鉴权之后 —— 未登录时不该泄漏接口清单
        docs_url = "/api/docs",
        openapi_url = "/api/openapi.json",
        lifespan = _lifespan_for(with_aria2),
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
                return JSONResponse({"detail": "Not authenticated", "code": "NOT_AUTHENTICATED"},
                            status_code = 401)

        return await call_next(request)

    app.include_router(system_routes.router, prefix = "/api")
    app.include_router(auth_routes.router, prefix = "/api/auth")
    app.include_router(aria2_routes.router, prefix = "/api/aria2")
    app.include_router(events_routes.router, prefix = "/api")
    app.include_router(files_routes.router, prefix = "/api")
    app.include_router(login_routes.router, prefix = "/api")
    app.include_router(parse_routes.router, prefix = "/api")
    app.include_router(preview_routes.router, prefix = "/api")
    app.include_router(settings_routes.router, prefix = "/api")
    app.include_router(tasks_routes.router, prefix = "/api")

    # **必须在所有 API 路由之后**：前端挂在根路径上，会吃掉所有未匹配的路径。
    # 先挂的话 API 就再也轮不到了
    static.mount(app, api_prefix = API_PREFIX)

    return app
