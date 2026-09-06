"""
WebUI 的下载编排

按 D4，aria2 只负责搬字节，以下必须留在这一层：CDN 探测择优、文件名生成与冲突处理、
重复下载判定、**多流聚合**、附加内容下载。

- `streams.py` —— 一个业务任务 ↔ 多个 gid 的映射与进度聚合（纯逻辑）
- `monitor.py` —— 把 aria2 的事件与进度喂给上面那层
"""

from .monitor import StreamMonitor, POLL_INTERVAL
from .streams import (
    StreamRegistry, TaskStreams, StreamState,
    TASK_PREPARING, TASK_ACTIVE, TASK_WAITING, TASK_PAUSED,
    TASK_ERROR, TASK_COMPLETE, TASK_REMOVED,
)

__all__ = [
    "StreamMonitor", "POLL_INTERVAL",
    "StreamRegistry", "TaskStreams", "StreamState",
    "TASK_PREPARING", "TASK_ACTIVE", "TASK_WAITING", "TASK_PAUSED",
    "TASK_ERROR", "TASK_COMPLETE", "TASK_REMOVED",
]
