"""
aria2 接管字节搬运（D4）

- `process.py` —— aria2c 进程的生命周期与 RPC 令牌
- `client.py` —— JSON-RPC over WebSocket 客户端，**用 aria2 的主动通知而非轮询**

D4 划的边界：aria2 只负责搬字节。CDN 探测择优、文件名生成与冲突处理、
重复下载判定、多流聚合、附加内容下载，全部留在业务层。
"""

from .client import (
    Aria2Client, Aria2Error, Aria2NotConnected,
    EVENT_DOWNLOAD_START, EVENT_DOWNLOAD_PAUSE, EVENT_DOWNLOAD_STOP,
    EVENT_DOWNLOAD_COMPLETE, EVENT_DOWNLOAD_ERROR, EVENT_BT_DOWNLOAD_COMPLETE,
    ALL_EVENTS,
)
from .process import Aria2Process, resolve_executable, ensure_secret

__all__ = [
    "Aria2Client", "Aria2Error", "Aria2NotConnected",
    "Aria2Process", "resolve_executable", "ensure_secret",
    "EVENT_DOWNLOAD_START", "EVENT_DOWNLOAD_PAUSE", "EVENT_DOWNLOAD_STOP",
    "EVENT_DOWNLOAD_COMPLETE", "EVENT_DOWNLOAD_ERROR", "EVENT_BT_DOWNLOAD_COMPLETE",
    "ALL_EVENTS",
]
