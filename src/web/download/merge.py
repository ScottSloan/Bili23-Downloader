"""
下载完成 → 附加内容 → FFmpeg 合并（S3-7）

aria2 报完最后一路流之后，剩下的事情**全在业务层**：取附加内容、调 FFmpeg 合并、
重命名、嵌封面 / 字幕 / 章节、按配置删临时文件。这些一件都不属于 aria2（D4）。

合并本身直接用桌面版的 `downloader/merger.py`。它在 S2-6 已经不依赖 Qt 了
（`FFmpegTask` 是普通线程 + 调度层回调），两端跑同一个类 —— 「产出与 GUI 一致的 mp4/mkv」
因此是构造上成立的，而不是靠两份实现碰巧对齐。

## 缺的那一块是调度

桌面版的合并排队逻辑长在 GUI 的 model 里（`gui/component/download_list/model.py` 的
`_manageConcurrentMerges`），服务端用不了，所以这里重写了一份**同样规则**的：
**同时只允许一个合并**。FFmpeg 是 CPU 与磁盘大户，放开并发只会让每个任务都变慢。

触发方式与桌面版一致：`Merger` 无论成功还是失败都会发
`signal_bus.download.auto_manage_concurrent_downloads`，两边都订阅这一个事件来推进队列。

## 重入

`Merger.start()` 在不需要 FFmpeg 的分支（只有单路流、直接重命名）里会**同步走完**，
一路调到 `mark_as_completed()` 并就地发出上面那个事件 —— 于是调度会在自己还没返回时
被再次调用。桌面侧靠 `_managing_merges` 挡住，这里同理。

挡住之后被跳过的那一次不会丢：本轮 for 循环还会继续往下扫，且每次合并结束都会再发一次事件。
"""

from typing import Dict, List, Optional
import asyncio
import logging
import threading

from util.common.enum import DownloadStatus
from util.common.signal_bus import signal_bus
from util.download.downloader.merger import Merger
from util.download.task.info import TaskInfo
from util.download.task.manager import task_manager
from util.parse.additional.runner import AdditionalRunner

from . import additional

logger = logging.getLogger(__name__)

# 同时进行的合并数。与桌面版一致，写死为 1 —— 见模块说明
MAX_CONCURRENT_MERGES = 1

# 正在占用合并额度的状态
BUSY_STATUS = (DownloadStatus.MERGING, DownloadStatus.CONVERTING)

class MergeCoordinator:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_MERGES):
        self.max_concurrent = max_concurrent

        self._tasks: Dict[str, TaskInfo] = {}
        self._mergers: Dict[str, Merger] = {}

        self._lock = threading.RLock()
        self._scheduling = False

        self._attached = False

    # ---- 生命周期 ----

    def attach(self) -> None:
        """订阅推进队列的事件。与桌面版订阅的是同一个"""
        if self._attached:
            return

        signal_bus.download.auto_manage_concurrent_downloads.connect(self.schedule)

        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return

        signal_bus.download.auto_manage_concurrent_downloads.disconnect(self.schedule)

        self._attached = False

    def shutdown(self, timeout: float = 3.0) -> None:
        """
        停掉所有在跑的 FFmpeg

        **不能省。** FFmpeg 子进程不停掉的话，本进程退出后它会变成孤儿，
        继续往输出文件里写 —— 下次启动看到的是一个还在长大的「已完成」文件
        """
        self.detach()

        with self._lock:
            mergers = list(self._mergers.items())

            self._mergers.clear()

        for task_id, merger in mergers:
            try:
                merger.stop(timeout)

            except Exception:
                logger.exception("停止合并任务失败：%s", task_id)

    # ---- 任务登记 ----
    #
    # 这张表兼作**整个服务端那份「活的 TaskInfo」登记表**：合并调度要用它，
    # 下载调度（driver.py）、重启对账、路由也都从这里拿任务。
    # 名字听着只管合并，实际上是进程里唯一的那份 —— 详见 driver.py 的模块说明

    def track(self, task_info: TaskInfo) -> None:
        """登记（覆盖）。已经有一份实例时用 `adopt`，不要用这个"""
        with self._lock:
            self._tasks[task_info.Basic.task_id] = task_info

    def adopt(self, task_info: TaskInfo) -> TaskInfo:
        """
        登记，但已经有一份实例时返回已有的那份

        **同一个任务在内存里只能有一个 TaskInfo。** 两份的话两边各改各的、
        谁后写库谁赢，表现是「进度偶尔倒退」「暂停了又自己跑起来」——
        而两处代码单看都没错。路由查库拿到的对象也要先过这里
        """
        with self._lock:
            existing = self._tasks.get(task_info.Basic.task_id)

            if existing is not None:
                return existing

            self._tasks[task_info.Basic.task_id] = task_info

            return task_info

    def forget(self, task_id: str) -> None:
        with self._lock:
            self._tasks.pop(task_id, None)

            merger = self._mergers.pop(task_id, None)

        if merger is not None:
            try:
                merger.stop()

            except Exception:
                logger.exception("停止合并任务失败：%s", task_id)

    def get(self, task_id: str) -> Optional[TaskInfo]:
        with self._lock:
            return self._tasks.get(task_id)

    def tracked(self) -> List[TaskInfo]:
        with self._lock:
            return list(self._tasks.values())

    # ---- 下载完成 ----

    def on_stream_snapshot(self, snapshot: dict) -> None:
        """
        接 `StreamMonitor.on_task_changed`

        只认「这个任务的所有流都完成了」，其余状态原样放过 —— 进度、暂停之类
        与合并无关。认不出来的 task_id 同样放过：aria2 里可能有不是我们建的下载
        """
        from .streams import TASK_COMPLETE

        if snapshot.get("status") != TASK_COMPLETE:
            return

        task_info = self.get(snapshot.get("task_id"))

        if task_info is None:
            return

        if task_info.Download.status not in (DownloadStatus.DOWNLOADING, DownloadStatus.PARSING,
                                             DownloadStatus.QUEUED, DownloadStatus.PAUSED):
            # 已经进过附加内容或合并阶段了。aria2 的完成事件与进度轮询都会走到这里，
            # 同一个任务大概率被通知不止一次，重复触发会让附加内容重跑、合并被打断
            return

        asyncio.ensure_future(self.on_download_finished(task_info))

    async def on_download_finished(self, task_info: TaskInfo) -> None:
        """
        下载完成后的收尾：附加内容 → 排进合并队列

        与桌面版 `Downloader.on_download_completed()` 同一套状态迁移
        """
        task_info.Download.speed = 0
        task_info.Download.progress = 100

        if AdditionalRunner.has_work(task_info):
            task_info.Download.status = DownloadStatus.ADDITIONAL_PROCESSING

            task_manager.update_async(task_info)

            try:
                await additional.run(task_info)

            except Exception as e:
                logger.exception("附加内容处理失败：%s", task_info.Basic.task_id)

                task_info.Download.status = DownloadStatus.FAILED
                task_info.Download.status_label = str(e)

                task_manager.update_async(task_info)

                signal_bus.download.update_downloading_item.emit(task_info)

                return

        task_info.Download.status = DownloadStatus.FFMPEG_QUEUED

        task_manager.update_async(task_info)

        signal_bus.download.update_downloading_item.emit(task_info)

        self.schedule()

    # ---- 合并调度 ----

    def schedule(self, *args, **kwargs) -> None:
        """
        推进合并队列

        参数一律吃掉：它同时挂在 `auto_manage_concurrent_downloads` 上，
        而那个事件将来可能带参数
        """
        with self._lock:
            if self._scheduling:
                # 重入。被跳过的这一次不会丢，理由见模块说明
                return

            self._scheduling = True

        try:
            self._schedule()

        finally:
            with self._lock:
                self._scheduling = False

    def _schedule(self) -> None:
        with self._lock:
            tasks = list(self._tasks.values())

        merging = 0
        queued = []

        for task_info in tasks:
            match task_info.Download.status:
                case DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                    merging += 1

                case DownloadStatus.FFMPEG_QUEUED:
                    queued.append(task_info)

        for task_info in queued:
            if merging >= self.max_concurrent:
                break

            self._start_merge(task_info)

            # 不需要 FFmpeg 的任务（单路流直接重命名）会同步走完，不占额度 ——
            # 这里必须重新读状态而不是无脑加一，否则队列会莫名其妙地卡住
            if task_info.Download.status in BUSY_STATUS:
                merging += 1

        self._reap_finished()

    def _start_merge(self, task_info: TaskInfo) -> None:
        task_id = task_info.Basic.task_id

        # 合并失败后可以重试，上一次的 Merger 里那个 FFmpeg 线程必须先停掉，
        # 否则两次合并会同时往同一个输出文件写
        self._release_merger(task_id)

        task_info.Download.status = DownloadStatus.MERGING

        merger = Merger(task_info)

        with self._lock:
            self._mergers[task_id] = merger

        signal_bus.download.update_downloading_item.emit(task_info)

        try:
            merger.start()

        except Exception as e:
            logger.exception("启动合并失败：%s", task_id)

            task_info.Download.status = DownloadStatus.FFMPEG_FAILED
            task_info.Download.status_label = str(e)

            task_manager.update_async(task_info)

    def _release_merger(self, task_id: str) -> None:
        with self._lock:
            merger = self._mergers.pop(task_id, None)

        if merger is None:
            return

        try:
            merger.stop()

        except Exception:
            logger.exception("停止合并任务失败：%s", task_id)

    def _reap_finished(self) -> None:
        """丢掉已经不在合并中的 Merger 引用。它持有 FFmpeg 线程，留着没意义"""
        with self._lock:
            finished = [
                task_id for task_id in self._mergers
                if task_id not in self._tasks
                or self._tasks[task_id].Download.status not in BUSY_STATUS
            ]

            for task_id in finished:
                self._mergers.pop(task_id, None)

    # ---- 观测 ----

    def merging_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.Download.status in BUSY_STATUS)

    def queued_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values()
                       if t.Download.status == DownloadStatus.FFMPEG_QUEUED)
