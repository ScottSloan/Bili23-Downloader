"""
把 aria2 的状态喂给 StreamRegistry（S3-4）

## 事件用推的，进度用拉的 —— 这不是自相矛盾

S3-3 定的是「用 aria2 的主动通知，不轮询」，指的是**状态变化**：开始、暂停、完成、出错
都由 aria2 推过来，不用挨个任务去问。

但**进度 aria2 不推**。它没有 onProgress 这类通知，字节数只能靠 `tellStatus` 取。
关键在于用 `tellActive`：**一次调用拿回所有活动下载的进度**，而不是每个任务问一遍。
所以这里是「每秒一次固定开销」，与任务数无关 —— 和「轮询每个任务」是两回事。

没有活动任务时连这一次都不发，纯静默。

## 变更通知

进度每秒都在动，但没必要每秒都往前端推一遍完整快照。这里只在**聚合后的可见字段真的变了**
时才回调 `on_task_changed`（S3-9 的 WebSocket 增量事件会接在这上面）。
"""

from typing import Callable, Dict, List, Optional
import asyncio
import contextlib
import logging

from ..aria2 import (
    Aria2Client, Aria2NotConnected,
    EVENT_DOWNLOAD_START, EVENT_DOWNLOAD_PAUSE, EVENT_DOWNLOAD_STOP,
    EVENT_DOWNLOAD_COMPLETE, EVENT_DOWNLOAD_ERROR,
)

from .streams import (
    StreamRegistry,
    ARIA2_ACTIVE, ARIA2_PAUSED, ARIA2_REMOVED, ARIA2_COMPLETE, ARIA2_ERROR,
)

logger = logging.getLogger(__name__)

# 进度拉取间隔。一秒是界面观感与开销的常见折中，且与任务数无关（tellActive 一次拿全部）
POLL_INTERVAL = 1.0

# tellActive 只要这几个字段，少传一点是一点
STATUS_KEYS = ["gid", "status", "totalLength", "completedLength", "downloadSpeed", "errorMessage"]

# 事件 → aria2 状态字符串
EVENT_STATUS = {
    EVENT_DOWNLOAD_START: ARIA2_ACTIVE,
    EVENT_DOWNLOAD_PAUSE: ARIA2_PAUSED,
    EVENT_DOWNLOAD_STOP: ARIA2_REMOVED,
    EVENT_DOWNLOAD_COMPLETE: ARIA2_COMPLETE,
    EVENT_DOWNLOAD_ERROR: ARIA2_ERROR,
}

# 参与「有没有变化」判定的字段。**故意不包含 speed**：
# 速度每秒都在抖，把它算进去等于每秒都推一次全量快照
CHANGE_KEYS = ("status", "progress", "total_size")

class StreamMonitor:
    def __init__(self, client: Aria2Client, registry: StreamRegistry = None):
        self.client = client

        # **必须用 is None 判断**：StreamRegistry 定义了 __len__，空的时候布尔值是 False，
        # 写成 `registry or StreamRegistry()` 会把调用方传进来的空 registry 丢掉，
        # 换成一个新的 —— 于是调用方拿着的那个永远不会被更新，且毫无报错
        self.registry = registry if registry is not None else StreamRegistry()

        self.on_task_changed: Optional[Callable[[dict], None]] = None

        # 每次轮询都调，不做变更判定 —— 速度必须走这条：CHANGE_KEYS 刻意不含 speed，
        # 只挂在 on_task_changed 上的话，界面上的速度要等进度整整跳一个百分点才动一次。
        # 一秒一条小 JSON × 并发下载数（默认 1），开销可以忽略
        self.on_task_progress: Optional[Callable[[dict], None]] = None

        self._task: Optional[asyncio.Task] = None
        self._last_seen: Dict[str, tuple] = {}

    # ---- 生命周期 ----

    def attach(self) -> None:
        """订阅 aria2 的事件通知"""
        for event, status in EVENT_STATUS.items():
            self.client.on(event, self._make_handler(event, status))

    def _make_handler(self, event: str, status: str):
        def handler(gid: str):
            task_id = self.registry.set_status(gid, status)

            if task_id is None:
                # 不是我们建的任务（上次没退干净留下的等），忽略即可
                return

            logger.debug("aria2 事件 %s：gid=%s task=%s", event, gid, task_id)

            # 出错与完成要立刻把详情补齐 —— 事件只带 gid，errorMessage 得单独取
            if status in (ARIA2_ERROR, ARIA2_COMPLETE):
                asyncio.create_task(self._refresh_gid(gid))

            else:
                self._notify(task_id)

        return handler

    async def _refresh_gid(self, gid: str) -> None:
        try:
            status = await self.client.tell_status(gid, STATUS_KEYS)

        except Exception as e:
            logger.debug("补取 gid %s 的状态失败：%s", gid, e)

            return

        task_id = self.registry.update_from_status(status)

        if task_id:
            self._notify(task_id)

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        self._task = asyncio.create_task(self._poll_loop(), name = "aria2-progress")

    async def stop(self) -> None:
        task = self._task
        self._task = None

        if task is None:
            return

        task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task

    # ---- 进度 ----

    async def _poll_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(POLL_INTERVAL)

                await self.poll_once()

            except asyncio.CancelledError:
                raise

            except Exception:
                # 拉进度失败不该让循环停掉 —— 停了就再也不会恢复，
                # 而界面会永远停在最后一次的进度上
                logger.exception("拉取 aria2 进度时出错")

    async def poll_once(self) -> List[str]:
        """拉一次进度，返回发生变化的 task_id 列表"""
        if not self.registry.all_gids():
            # 没有登记在册的任务，连这一次调用都省掉
            return []

        if not self.client.connected:
            return []

        try:
            active = await self.client.tell_active(STATUS_KEYS)

        except Aria2NotConnected:
            return []

        changed = []

        for status in active:
            task_id = self.registry.update_from_status(status)

            if not task_id:
                continue

            self._report_progress(task_id)

            if self._notify(task_id):
                changed.append(task_id)

        return changed

    def _report_progress(self, task_id: str) -> None:
        if self.on_task_progress is None:
            return

        snapshot = self.registry.snapshot(task_id)

        if snapshot is None:
            return

        try:
            self.on_task_progress(snapshot)

        except Exception:
            # 进度回写出错不该让整个轮询循环停掉
            logger.exception("任务进度回写失败：%s", task_id)

    async def refresh_task(self, task_id: str) -> Optional[dict]:
        """
        逐个 gid 把某个任务的状态查全

        用在「刚建完任务」「重连后对账」这类需要准确一次性快照的场合 ——
        `tellActive` 只返回活动中的，暂停和已完成的查不到
        """
        for gid in self.registry.gids_of(task_id):
            try:
                status = await self.client.tell_status(gid, STATUS_KEYS)

            except Exception as e:
                logger.debug("查询 gid %s 失败：%s", gid, e)

                continue

            self.registry.update_from_status(status)

        snapshot = self.registry.snapshot(task_id)

        if snapshot:
            self._notify(task_id, force = True)

        return snapshot

    # ---- 变更通知 ----

    def _notify(self, task_id: str, force: bool = False) -> bool:
        """聚合后的可见字段变了才回调。返回是否真的变了"""
        snapshot = self.registry.snapshot(task_id)

        if snapshot is None:
            return False

        signature = tuple(snapshot.get(key) for key in CHANGE_KEYS)

        if not force and self._last_seen.get(task_id) == signature:
            return False

        self._last_seen[task_id] = signature

        if self.on_task_changed is not None:
            try:
                self.on_task_changed(snapshot)

            except Exception:
                logger.exception("任务变更回调执行失败：%s", task_id)

        return True

    def forget(self, task_id: str) -> List[str]:
        """任务被删掉时清理登记，返回它名下的 gid 供调用方交给 aria2"""
        self._last_seen.pop(task_id, None)

        return self.registry.unregister_task(task_id)
