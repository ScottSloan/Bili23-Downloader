"""
aria2 的 JSON-RPC 客户端（WebSocket）

**用 WebSocket 而不是 HTTP，是为了拿 aria2 的主动通知**（D4 / PLAN S3-3）：
下载开始、暂停、完成、出错都由 aria2 推过来，不用轮询 `tellStatus`。
轮询在任务多的时候既费 CPU 又有延迟，而进度这种高频数据轮询更划不来。

一条连接上同时跑两种消息：

- **响应** —— 带 `id`，对应我们发出去的某个请求
- **通知** —— 有 `method` 没有 `id`，如 `aria2.onDownloadComplete`

所以必须有一个常驻的读取任务负责分发，`call()` 只是把请求发出去再等对应的 future。

## 重连

aria2 可能崩溃或被重启。断线后不重连的话，后端会永久失去下载能力却还在正常响应 HTTP ——
这种「假活」比直接挂掉更难排查。因此内置了带退避的重连，并在重连成功后回调
`on_reconnect`，让上层有机会重新对账（S3-8）。

重连期间未完成的请求会**立即失败**而不是挂着等：aria2 重启后 gid 可能已经不在了，
让调用方早点知道并重试，比抱着一个永远不会有响应的 future 强。
"""

from typing import Any, Callable, Dict, List, Optional
import asyncio
import contextlib
import json
import logging

import websockets
from websockets.asyncio.client import connect as ws_connect

logger = logging.getLogger(__name__)

# aria2 会推送的通知。参数固定是 [{"gid": "..."}]
EVENT_DOWNLOAD_START = "onDownloadStart"
EVENT_DOWNLOAD_PAUSE = "onDownloadPause"
EVENT_DOWNLOAD_STOP = "onDownloadStop"
EVENT_DOWNLOAD_COMPLETE = "onDownloadComplete"
EVENT_DOWNLOAD_ERROR = "onDownloadError"
EVENT_BT_DOWNLOAD_COMPLETE = "onBtDownloadComplete"

ALL_EVENTS = (
    EVENT_DOWNLOAD_START,
    EVENT_DOWNLOAD_PAUSE,
    EVENT_DOWNLOAD_STOP,
    EVENT_DOWNLOAD_COMPLETE,
    EVENT_DOWNLOAD_ERROR,
    EVENT_BT_DOWNLOAD_COMPLETE,
)

DEFAULT_TIMEOUT = 30.0

# 重连退避：首次 0.5 秒，每次翻倍，封顶 10 秒
RECONNECT_INITIAL_DELAY = 0.5
RECONNECT_MAX_DELAY = 10.0

class Aria2Error(Exception):
    """aria2 返回的 JSON-RPC 错误"""

    def __init__(self, code: int, message: str):
        super().__init__(f"aria2 错误 {code}：{message}")

        self.code = code
        self.message = message

class Aria2NotConnected(Exception):
    pass

class Aria2Client:
    def __init__(self, url: str, secret: str = "", auto_reconnect: bool = True):
        self.url = url
        self.secret = secret
        self.auto_reconnect = auto_reconnect

        self._ws = None
        self._reader: Optional[asyncio.Task] = None

        self._next_id = 0
        self._pending: Dict[str, asyncio.Future] = {}

        self._listeners: Dict[str, List[Callable]] = {}

        self._connected = asyncio.Event()
        self._closing = False

        self.on_reconnect: Optional[Callable] = None

    # ---- 连接 ----

    async def connect(self, timeout: float = 10.0) -> None:
        """建立连接并启动读取任务。已连接时直接返回"""
        if self._reader is not None and not self._reader.done():
            await asyncio.wait_for(self._connected.wait(), timeout = timeout)

            return

        self._closing = False

        self._reader = asyncio.create_task(self._run(), name = "aria2-reader")

        try:
            await asyncio.wait_for(self._connected.wait(), timeout = timeout)

        except asyncio.TimeoutError:
            await self.close()

            raise Aria2NotConnected(f"连接 aria2 超时：{self.url}")

    async def close(self) -> None:
        self._closing = True

        reader = self._reader
        self._reader = None

        if reader is not None:
            reader.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await reader

        await self._drop_connection(Aria2NotConnected("连接已关闭"))

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    async def _run(self) -> None:
        """读取循环 + 重连。整个客户端的生命周期都在这个任务里"""
        delay = RECONNECT_INITIAL_DELAY
        first = True

        while not self._closing:
            try:
                async with ws_connect(self.url, max_size = None) as ws:
                    self._ws = ws
                    self._connected.set()

                    delay = RECONNECT_INITIAL_DELAY

                    if first:
                        logger.info("已连接 aria2：%s", self.url)

                        first = False

                    else:
                        logger.info("已重新连接 aria2")

                        if self.on_reconnect is not None:
                            # 上层可能要重新对账，别让它的异常打断读取循环
                            try:
                                result = self.on_reconnect()

                                if asyncio.iscoroutine(result):
                                    await result

                            except Exception:
                                logger.exception("重连回调执行失败")

                    async for message in ws:
                        self._dispatch(message)

            except asyncio.CancelledError:
                raise

            except Exception as e:
                if self._closing:
                    break

                logger.warning("aria2 连接断开：%s", e)

            # 走到这里说明连接没了
            await self._drop_connection(Aria2NotConnected("与 aria2 的连接已断开"))

            if self._closing or not self.auto_reconnect:
                break

            await asyncio.sleep(delay)

            delay = min(delay * 2, RECONNECT_MAX_DELAY)

    async def _drop_connection(self, error: Exception) -> None:
        self._ws = None
        self._connected.clear()

        # 未完成的请求立即失败。aria2 重启后 gid 可能已经不在了，
        # 让调用方早点知道并重试，比抱着一个永远不会有响应的 future 强
        pending = list(self._pending.items())

        self._pending.clear()

        for _, future in pending:
            if not future.done():
                future.set_exception(error)

    # ---- 收 ----

    def _dispatch(self, raw) -> None:
        try:
            message = json.loads(raw)

        except Exception:
            logger.warning("aria2 发来无法解析的消息：%r", raw[:200])

            return

        # 批量调用会返回一个数组
        if isinstance(message, list):
            for item in message:
                self._dispatch_one(item)

            return

        self._dispatch_one(message)

    def _dispatch_one(self, message: dict) -> None:
        if not isinstance(message, dict):
            return

        message_id = message.get("id")

        if message_id is not None:
            future = self._pending.pop(str(message_id), None)

            if future is None or future.done():
                # 超时后又姗姗来迟的响应，丢掉即可
                return

            error = message.get("error")

            if error:
                future.set_exception(Aria2Error(error.get("code", -1),
                                                error.get("message", "unknown")))

            else:
                future.set_result(message.get("result"))

            return

        method = message.get("method")

        if not method:
            return

        # 通知的 method 形如 "aria2.onDownloadComplete"
        event = method.split(".", 1)[-1]

        params = message.get("params") or [{}]

        gid = params[0].get("gid") if isinstance(params[0], dict) else None

        for callback in self._listeners.get(event, ()):
            try:
                result = callback(gid)

                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)

            except Exception:
                # 一个监听者出问题不该连累其他监听者，更不该打断读取循环
                logger.exception("aria2 事件 %s 的监听者执行失败", event)

    def on(self, event: str, callback: Callable) -> None:
        """订阅 aria2 的通知。callback 收到 gid，可以是协程函数"""
        self._listeners.setdefault(event, []).append(callback)

    # ---- 发 ----

    async def call(self, method: str, *params: Any, timeout: float = DEFAULT_TIMEOUT) -> Any:
        """
        调用一个 aria2 方法

        方法名可以省略 `aria2.` 前缀。带令牌时会自动在参数最前面插入 `token:<secret>`
        """
        ws = self._ws

        if ws is None or not self._connected.is_set():
            raise Aria2NotConnected("尚未连接 aria2")

        if "." not in method:
            method = f"aria2.{method}"

        self._next_id += 1

        request_id = str(self._next_id)

        payload_params: List[Any] = list(params)

        if self.secret:
            payload_params.insert(0, f"token:{self.secret}")

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": payload_params,
        }

        future: asyncio.Future = asyncio.get_running_loop().create_future()

        self._pending[request_id] = future

        try:
            await ws.send(json.dumps(payload))

            return await asyncio.wait_for(future, timeout = timeout)

        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)

            raise Aria2NotConnected(f"调用 {method} 超时（{timeout} 秒）")

        except websockets.exceptions.WebSocketException as e:
            self._pending.pop(request_id, None)

            raise Aria2NotConnected(f"调用 {method} 时连接出错：{e}")

    # ---- 常用方法的薄封装 ----
    #
    # 只包最常用的几个，其余直接用 call()。包装层薄一点，
    # aria2 的参数语义就少一层需要同步维护的转述

    async def add_uri(self, uris: List[str], options: dict = None, position: int = None) -> str:
        """加一个下载，返回 gid"""
        params: List[Any] = [uris, options or {}]

        if position is not None:
            params.append(position)

        return await self.call("addUri", *params)

    async def pause(self, gid: str, force: bool = False) -> str:
        return await self.call("forcePause" if force else "pause", gid)

    async def unpause(self, gid: str) -> str:
        return await self.call("unpause", gid)

    async def remove(self, gid: str, force: bool = False) -> str:
        return await self.call("forceRemove" if force else "remove", gid)

    async def remove_result(self, gid: str) -> str:
        """把已停止的任务从 aria2 的结果列表里清掉，否则它会一直占着 gid"""
        return await self.call("removeDownloadResult", gid)

    async def tell_status(self, gid: str, keys: List[str] = None) -> dict:
        params: List[Any] = [gid]

        if keys:
            params.append(keys)

        return await self.call("tellStatus", *params)

    async def tell_active(self, keys: List[str] = None) -> List[dict]:
        return await self.call("tellActive", *( [keys] if keys else [] ))

    async def get_global_stat(self) -> dict:
        return await self.call("getGlobalStat")

    async def get_version(self) -> dict:
        return await self.call("getVersion")

    async def change_global_option(self, options: dict) -> str:
        return await self.call("changeGlobalOption", options)

    async def shutdown(self, force: bool = False) -> str:
        return await self.call("forceShutdown" if force else "shutdown")
