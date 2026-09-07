"""
全量快照 REST + 增量 WebSocket 事件（S3-9）

## WebSocket 的鉴权必须在这里显式做

`app.py` 的鉴权是 `@app.middleware("http")` —— 顾名思义**只包 HTTP**。
WebSocket 走的是另一套 scope，中间件根本不会被调用到，所以「默认开启、按需豁免」
那条规则在这里不成立：不在这个文件里自己查一次会话，`/api/ws` 就是一个**完全不鉴权的
实时数据出口**，而且从路由表上看不出任何异常。

**在 accept 之前拒绝**：没通过鉴权就不该建立连接。代价是客户端看不到自定义关闭码 ——
ASGI 里 accept 之前的 close 会退化成一个 HTTP 403 响应，WebSocket 关闭码只有在握手
完成之后才有地方放。先 accept 再用 4401 关掉倒是能带上码，但那等于先把门打开再赶人，
不值得为一个错误码这么做。
"""

from typing import Optional
import asyncio
import logging

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect

from util.download.task.manager import task_manager

from ..download.view import task_views
from ..events import EVENT_RESYNC
from ..security import SESSION_COOKIE

from ..schemas import TaskSnapshot

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["events"])

# 服务不可用时的关闭码。1000-2999 是协议保留段，应用自己的原因码要用 4000-4999。
# 鉴权失败不在此列 —— 那一条在 accept 之前就拒了，走的是 HTTP 403
WS_UNAVAILABLE = 4503

@router.get("/tasks", response_model = TaskSnapshot)
async def task_snapshot(request: Request, limit: int = Query(default = None, ge = 1, le = 5000)):
    """
    全量快照

    带上 `cursor`：前端拿它去连 WebSocket（`?since=cursor`），服务端会把这之后的
    增量补发出来。没有这个游标的话，快照与增量之间会漏掉一段
    """
    hub = getattr(request.app.state, "events", None)

    downloading = task_manager.query(completed = False, limit = limit)
    completed = task_manager.query(completed = True, limit = limit)

    return {
        # 游标要在查询**之后**取：先取的话，查询期间产生的事件会被当成「快照已包含」
        # 而不再补发，那正是要避免的那条缝
        "cursor": hub.cursor if hub is not None else 0,
        "downloading": task_views(downloading),
        "completed": task_views(completed),
    }

@router.websocket("/ws")
async def events_socket(websocket: WebSocket, since: Optional[int] = Query(default = None)):
    sessions = getattr(websocket.app.state, "sessions", None)
    hub = getattr(websocket.app.state, "events", None)

    token = websocket.cookies.get(SESSION_COOKIE)

    if sessions is None or sessions.get(token) is None:
        # 中间件管不到 WebSocket，这一句就是这条路径上唯一的鉴权。
        # accept 之前 close，客户端收到的是 HTTP 403 而不是握手成功后的关闭帧
        await websocket.close()

        return

    if hub is None:
        await websocket.close(code = WS_UNAVAILABLE)

        return

    await websocket.accept()

    subscriber = hub.subscribe()

    try:
        backlog = hub.replay_since(since)

        if backlog is None:
            # 补不上了（缓冲区滚过去了，或后端重启过导致编号回退）。
            # 让前端重新拉一次快照，比装作无事发生强
            await websocket.send_json({"type": EVENT_RESYNC, "seq": hub.cursor})

        else:
            for message in backlog:
                await websocket.send_json(message)

        # 读方向单独跑一个任务：客户端主动断开时，只有真正去读才会拿到断开信号。
        # 不读的话，一个已经关掉的标签页会一直挂在订阅者列表里
        reader = asyncio.create_task(_drain(websocket))

        getter = None

        try:
            while True:
                # **必须同时等队列和读方向。** 只 `await queue.get()` 的话，客户端断开后
                # 这个协程会一直挂在那里等下一条消息 —— 订阅者不会被清理，
                # 而且 uvicorn 会因为连接没结束而无法关停（实测卡在这里）
                getter = asyncio.ensure_future(subscriber.queue.get())

                done, _ = await asyncio.wait(
                    {getter, reader}, return_when = asyncio.FIRST_COMPLETED)

                if reader in done:
                    break

                await websocket.send_json(getter.result())

                getter = None

        finally:
            if getter is not None:
                getter.cancel()

            reader.cancel()

    except WebSocketDisconnect:
        pass

    except Exception:
        logger.exception("推送事件时出错")

    finally:
        hub.unsubscribe(subscriber)

async def _drain(websocket: WebSocket) -> None:
    """
    把客户端发来的东西读掉

    我们不需要它说什么，读只是为了尽早发现断开。收到什么一律忽略 ——
    **不要在这里加命令通道**：那会绕过 REST 那一侧的入参校验
    """
    try:
        while True:
            await websocket.receive_text()

    except Exception:
        return
