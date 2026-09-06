"""
一个业务任务 ↔ 多个 aria2 gid 的映射与进度聚合（S3-4）

一条视频在 dash 下是**分开的两路流**（视频 + 音频），旧版 flv 还会是若干分片。
aria2 只认单个下载，所以业务层要自己把它们拢成一个任务：一个 TaskInfo 对应 N 个 gid，
进度、速度、状态都要聚合出来。

**这一层是纯逻辑，不碰 aria2 也不碰数据库**，好让聚合规则能被单独测。
真正去问 aria2 要数据的部分在 `monitor.py`。

## 进度为什么要等所有流都拿到大小才开始报

聚合进度 = 已完成字节之和 / 总字节之和。但 aria2 刚接到任务时 `totalLength` 是 0 ——
服务端还没回响应头。此时若拿「已知的那部分」当分母，分母偏小、进度偏大，
等另一路的大小到位后**进度会往回跳**。

进度倒退是这个仓库明确要避免的（task.db 的快照取样那里有同样的记载）。
所以在所有流都拿到大小之前，一律报 0 并把状态标成「准备中」——
这段通常只有一两秒，用户感知不到，比看着进度条往回缩强。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import threading

# aria2 的状态字符串（tellStatus 的 status 字段）
ARIA2_ACTIVE = "active"
ARIA2_WAITING = "waiting"
ARIA2_PAUSED = "paused"
ARIA2_ERROR = "error"
ARIA2_COMPLETE = "complete"
ARIA2_REMOVED = "removed"

# 聚合后的任务状态
TASK_PREPARING = "preparing"
TASK_ACTIVE = "active"
TASK_WAITING = "waiting"
TASK_PAUSED = "paused"
TASK_ERROR = "error"
TASK_COMPLETE = "complete"
TASK_REMOVED = "removed"

@dataclass
class StreamState:
    """一路流的状态。字段与 aria2 tellStatus 的返回一一对应"""

    gid: str
    file_key: str

    total: int = 0
    completed: int = 0
    speed: int = 0
    status: str = ARIA2_WAITING
    error_message: str = ""

    @property
    def size_known(self) -> bool:
        return self.total > 0

@dataclass
class TaskStreams:
    task_id: str
    streams: Dict[str, StreamState] = field(default_factory = dict)

    # ---- 聚合 ----

    @property
    def total_size(self) -> int:
        return sum(s.total for s in self.streams.values())

    @property
    def downloaded_size(self) -> int:
        return sum(s.completed for s in self.streams.values())

    @property
    def speed(self) -> int:
        # 只算还在跑的那些，否则暂停后残留的速度值会一直挂在界面上
        return sum(s.speed for s in self.streams.values() if s.status == ARIA2_ACTIVE)

    @property
    def all_sizes_known(self) -> bool:
        return bool(self.streams) and all(s.size_known for s in self.streams.values())

    @property
    def progress(self) -> int:
        """0 - 100。所有流都拿到大小之前一律返回 0，理由见模块说明"""
        if not self.all_sizes_known:
            return 0

        total = self.total_size

        if total <= 0:
            return 0

        # 全部完成时直接给 100：字节数相加可能因为 aria2 的统计口径差一点点，
        # 让「已完成」的任务停在 99 是最让人困惑的一种显示
        if self.status == TASK_COMPLETE:
            return 100

        return min(99, int(self.downloaded_size * 100 / total))

    @property
    def status(self) -> str:
        """
        聚合状态。**判定顺序是有讲究的**：

        - 出错优先 —— 一路挂了整个任务就废了，不能因为另一路还在跑就显示「下载中」
        - 其次是「全部完成」—— 必须排在「有活动的」前面，否则最后一路完成的瞬间
          会因为别的流还在 complete 状态而判不出来
        - 再往后按活跃程度递减
        """
        if not self.streams:
            return TASK_WAITING

        states = [s.status for s in self.streams.values()]

        if any(s == ARIA2_ERROR for s in states):
            return TASK_ERROR

        if any(s == ARIA2_REMOVED for s in states):
            return TASK_REMOVED

        if all(s == ARIA2_COMPLETE for s in states):
            return TASK_COMPLETE

        if any(s == ARIA2_ACTIVE for s in states):
            # 还没拿到大小时报「准备中」，避免界面上出现一个不动的 0%
            return TASK_ACTIVE if self.all_sizes_known else TASK_PREPARING

        if any(s == ARIA2_PAUSED for s in states):
            return TASK_PAUSED

        return TASK_WAITING

    @property
    def error_message(self) -> str:
        for stream in self.streams.values():
            if stream.status == ARIA2_ERROR and stream.error_message:
                return stream.error_message

        return ""

    def snapshot(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "speed": self.speed,
            "error_message": self.error_message,
            "streams": {
                key: {
                    "gid": s.gid,
                    "status": s.status,
                    "total": s.total,
                    "completed": s.completed,
                    "speed": s.speed,
                }
                for key, s in self.streams.items()
            },
        }

class StreamRegistry:
    """
    gid ↔ 业务任务的双向映射

    aria2 的通知只带 gid，所以反查必须是 O(1) 的 —— 一个批量任务下来 gid 会有几十个，
    每次事件都遍历一遍任务表不合适。
    """

    def __init__(self):
        self._tasks: Dict[str, TaskStreams] = {}
        self._gid_index: Dict[str, tuple] = {}      # gid -> (task_id, file_key)

        self._lock = threading.RLock()

    # ---- 登记 ----

    def register(self, task_id: str, file_key: str, gid: str) -> None:
        with self._lock:
            task = self._tasks.setdefault(task_id, TaskStreams(task_id = task_id))

            # 同一个 file_key 重新登记（换 CDN 重试）：把旧 gid 的索引摘掉，
            # 否则旧 gid 的迟到事件会打到新流上
            previous = task.streams.get(file_key)

            if previous is not None:
                self._gid_index.pop(previous.gid, None)

            task.streams[file_key] = StreamState(gid = gid, file_key = file_key)

            self._gid_index[gid] = (task_id, file_key)

    def unregister_task(self, task_id: str) -> List[str]:
        """移除一个任务，返回它名下的所有 gid（调用方拿去告诉 aria2 删掉）"""
        with self._lock:
            task = self._tasks.pop(task_id, None)

            if task is None:
                return []

            gids = []

            for stream in task.streams.values():
                gids.append(stream.gid)

                self._gid_index.pop(stream.gid, None)

            return gids

    # ---- 查 ----

    def task_id_of(self, gid: str) -> Optional[str]:
        with self._lock:
            entry = self._gid_index.get(gid)

            return entry[0] if entry else None

    def stream_of(self, gid: str) -> Optional[StreamState]:
        with self._lock:
            entry = self._gid_index.get(gid)

            if entry is None:
                return None

            task = self._tasks.get(entry[0])

            return task.streams.get(entry[1]) if task else None

    def get(self, task_id: str) -> Optional[TaskStreams]:
        with self._lock:
            return self._tasks.get(task_id)

    def gids_of(self, task_id: str) -> List[str]:
        with self._lock:
            task = self._tasks.get(task_id)

            return [s.gid for s in task.streams.values()] if task else []

    def all_gids(self) -> List[str]:
        with self._lock:
            return list(self._gid_index)

    def task_ids(self) -> List[str]:
        with self._lock:
            return list(self._tasks)

    # ---- 更新 ----

    def update_from_status(self, status: dict) -> Optional[str]:
        """
        用 aria2 tellStatus / tellActive 的一条返回更新对应的流

        返回受影响的 task_id，认不出这个 gid 时返回 None ——
        aria2 里可能有不是我们建的任务（比如上次没退干净留下的），不该当成错误
        """
        gid = status.get("gid")

        if not gid:
            return None

        with self._lock:
            entry = self._gid_index.get(gid)

            if entry is None:
                return None

            task_id, file_key = entry

            stream = self._tasks[task_id].streams.get(file_key)

            if stream is None:
                return None

            stream.total = int(status.get("totalLength", stream.total) or 0)
            stream.completed = int(status.get("completedLength", stream.completed) or 0)
            stream.speed = int(status.get("downloadSpeed", 0) or 0)

            if status.get("status"):
                stream.status = status["status"]

            error = status.get("errorMessage")

            if error:
                stream.error_message = error

            return task_id

    def set_status(self, gid: str, status: str) -> Optional[str]:
        """只改状态，用于 aria2 推来的事件通知（那些通知只带 gid）"""
        with self._lock:
            entry = self._gid_index.get(gid)

            if entry is None:
                return None

            task_id, file_key = entry

            stream = self._tasks[task_id].streams.get(file_key)

            if stream is None:
                return None

            stream.status = status

            # 停下来的流速度要归零，否则界面上会一直挂着最后一次的速度
            if status != ARIA2_ACTIVE:
                stream.speed = 0

            return task_id

    def snapshot(self, task_id: str) -> Optional[dict]:
        with self._lock:
            task = self._tasks.get(task_id)

            return task.snapshot() if task else None

    def snapshot_all(self) -> List[dict]:
        with self._lock:
            return [task.snapshot() for task in self._tasks.values()]

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()
            self._gid_index.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._tasks)
