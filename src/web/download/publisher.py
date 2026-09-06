"""
把 signal_bus 上的任务事件转成 WebSocket 增量事件（S3-9）

订阅的是**桌面版发出的同一批事件** —— `util/` 层本就不认识界面，一律通过 signal_bus
通知上层，桌面接的是 Qt 模型，这里接的是 WebSocket。所以下载器、Merger、附加内容那边
一行都不用改。

回调落在哪个线程由 `web/dispatch.py` 决定：它把工作线程发出的事件投递回事件循环线程，
`EventHub.publish` 因此总是在正确的线程上跑。**没装那个调度器的话**，这里会就地跑在
FFmpeg 线程或后台线程上，往 asyncio 队列里塞东西不会报错，只是静默不生效。

订阅必须能解开：测试会反复建应用，不 detach 的话上一个 hub 会一直挂在 signal_bus 上，
收到事件后往一个已经没人读的队列里塞，直到进程结束。
"""

from typing import List
import logging

from util.common.signal_bus import signal_bus
from util.download.task.info import TaskInfo

from .view import task_view, task_views

logger = logging.getLogger(__name__)

EVENT_TASK_ADDED = "task.added"
EVENT_TASK_UPDATED = "task.updated"
EVENT_TASK_COMPLETED = "task.completed"
EVENT_TASK_REMOVED = "task.removed"
EVENT_ARIA2_STATUS = "aria2.status"

class TaskPublisher:
    def __init__(self, hub):
        self.hub = hub

        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return

        signal_bus.download.add_to_downloading_list.connect(self.on_added)
        signal_bus.download.update_downloading_item.connect(self.on_updated)
        signal_bus.download.add_to_completed_list.connect(self.on_completed)
        signal_bus.download.remove_from_downloading_list.connect(self.on_removed)

        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return

        signal_bus.download.add_to_downloading_list.disconnect(self.on_added)
        signal_bus.download.update_downloading_item.disconnect(self.on_updated)
        signal_bus.download.add_to_completed_list.disconnect(self.on_completed)
        signal_bus.download.remove_from_downloading_list.disconnect(self.on_removed)

        self._attached = False

    # ---- 任务 ----

    def on_added(self, task_info_list: List[TaskInfo], *args, **kwargs) -> None:
        self.hub.publish(EVENT_TASK_ADDED, task_views(task_info_list))

    def on_updated(self, task_info: TaskInfo, *args, **kwargs) -> None:
        self.hub.publish(EVENT_TASK_UPDATED, task_view(task_info))

    def on_completed(self, task_info_list: List[TaskInfo], *args, **kwargs) -> None:
        self.hub.publish(EVENT_TASK_COMPLETED, task_views(task_info_list))

    def on_removed(self, task_info: TaskInfo, *args, **kwargs) -> None:
        self.hub.publish(EVENT_TASK_REMOVED, {"task_id": task_info.Basic.task_id})

    # ---- aria2 ----

    def publish_aria2(self, connected: bool, error: str = None) -> None:
        """
        aria2 断开 / 重连要让前端知道

        它断开时任务不会再有任何进度事件，界面上看起来与「网络很慢」一模一样。
        不告诉前端的话，用户只会觉得下载卡住了
        """
        self.hub.publish(EVENT_ARIA2_STATUS, {"connected": connected, "error": error})
