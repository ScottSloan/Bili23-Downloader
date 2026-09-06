"""
WebUI 的下载编排

按 D4，aria2 只负责搬字节，以下必须留在这一层：CDN 探测择优、文件名生成与冲突处理、
重复下载判定、**多流聚合**、附加内容下载。

- `streams.py`  —— 一个业务任务 ↔ 多个 gid 的映射与进度聚合（纯逻辑）
- `monitor.py`  —— 把 aria2 的事件与进度喂给上面那层
- `resolver.py` —— CDN 择优（复用 GUI 同一条链路）与 aria2 参数构造
- `additional.py` —— 附加内容走 httpx，不进 aria2；编排与桌面版同一份
- `merge.py`     —— 下载完成 → 附加内容 → FFmpeg 合并，合并并发固定为 1
"""

from . import additional
from .merge import MergeCoordinator, MAX_CONCURRENT_MERGES
from .monitor import StreamMonitor, POLL_INTERVAL
from .resolver import (
    extract_urls, format_cookie, build_headers, build_options, build_global_options,
    resolve_dash, resolve_mp4, resolve_dash_sync, resolve_mp4_sync, submit_stream,
    MIN_FILE_SIZE, DEFAULT_REFERER,
)
from .streams import (
    StreamRegistry, TaskStreams, StreamState,
    TASK_PREPARING, TASK_ACTIVE, TASK_WAITING, TASK_PAUSED,
    TASK_ERROR, TASK_COMPLETE, TASK_REMOVED,
)

__all__ = [
    "additional",
    "MergeCoordinator", "MAX_CONCURRENT_MERGES",
    "StreamMonitor", "POLL_INTERVAL",
    "StreamRegistry", "TaskStreams", "StreamState",
    "TASK_PREPARING", "TASK_ACTIVE", "TASK_WAITING", "TASK_PAUSED",
    "TASK_ERROR", "TASK_COMPLETE", "TASK_REMOVED",
    "extract_urls", "format_cookie", "build_headers", "build_options", "build_global_options",
    "resolve_dash", "resolve_mp4", "resolve_dash_sync", "resolve_mp4_sync", "submit_stream",
    "MIN_FILE_SIZE", "DEFAULT_REFERER",
]
