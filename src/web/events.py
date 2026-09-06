"""
事件总线：全量快照 + 增量事件（S3-9）

PLAN 对 S3-9 的验收标准：**前端刷新页面能完整恢复现场**。两条路径缺一不可 ——
只有增量的话，刷新之后前端手里什么都没有；只有快照的话，就只能退回轮询。

## 快照与增量之间的缝

先拉快照再连 WebSocket，两步之间发生的事件会丢；反过来先连再拉，又会拿到比快照更旧的事件。
这条缝在轮询年代不存在，是改推送之后新引入的，而且**只在状态变化恰好落在两步之间时才出现**
—— 平时测不出来，上线后表现为「进度条偶尔卡住不动，刷新一下就好了」。

这里的处理是给每个事件编号（`seq`）：

- 快照带上 `cursor` = 发快照那一刻的最新编号
- 前端带 `?since=<cursor>` 连 WebSocket，服务端把这之后的事件补发出来
- 补不上了（缓冲区已经滚过去）就回一条 `resync`，让前端重新拉一次快照

编号本身也是前端自查的依据：收到的 `seq` 不连续就说明漏了，同样重新拉快照。

## 慢客户端不能拖住发布方

每个连接一个有界队列。写满了不是阻塞，也不是断开，而是**清空队列并塞一条 `resync`** ——
积压的那些增量已经没有意义了，让它重新拉一次快照反而更快、更省。

发布方（下载线程、FFmpeg 线程）绝不能因为某个浏览器标签页卡住而被拖慢。
"""

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set
import asyncio
import logging

logger = logging.getLogger(__name__)

# 环形缓冲里保留多少条历史事件，供断线重连补发。
# 按每秒一次进度更新算，200 条约等于三分钟的窗口，够覆盖一次刷新或短暂断网
HISTORY_SIZE = 200

# 单个连接的待发队列上限。超了说明这个客户端跟不上，补发已无意义
CLIENT_QUEUE_SIZE = 100

# 让客户端重新拉快照的信号
EVENT_RESYNC = "resync"

class Subscriber:
    """一个 WebSocket 连接的待发队列"""

    def __init__(self, queue_size: int = CLIENT_QUEUE_SIZE):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize = queue_size)

    def put(self, message: dict) -> None:
        """
        非阻塞投递

        **满了就丢掉全部积压并要求重新同步**：一个卡住的标签页不该影响别人，
        更不该反压到下载线程上
        """
        try:
            self.queue.put_nowait(message)

        except asyncio.QueueFull:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()

                except asyncio.QueueEmpty:
                    break

            try:
                self.queue.put_nowait({"type": EVENT_RESYNC, "seq": message.get("seq")})

            except asyncio.QueueFull:
                pass

            logger.warning("事件队列积压，已要求该连接重新同步")

class EventHub:
    def __init__(self, history_size: int = HISTORY_SIZE):
        self._seq = 0
        self._history: Deque[dict] = deque(maxlen = history_size)
        self._subscribers: Set[Subscriber] = set()

    # ---- 发布 ----

    @property
    def cursor(self) -> int:
        """当前最新编号。REST 快照要把它一并带出去"""
        return self._seq

    def publish(self, event_type: str, payload: Any = None) -> dict:
        """
        发布一条增量事件

        **必须在事件循环线程上调用。** 上游的发布点都在 signal_bus 的订阅里，
        而调度器（web/dispatch.py）已经把它们投递回了循环线程
        """
        self._seq += 1

        message = {"seq": self._seq, "type": event_type, "data": payload}

        self._history.append(message)

        for subscriber in list(self._subscribers):
            subscriber.put(message)

        return message

    # ---- 订阅 ----

    def subscribe(self) -> Subscriber:
        subscriber = Subscriber()

        self._subscribers.add(subscriber)

        return subscriber

    def unsubscribe(self, subscriber: Subscriber) -> None:
        self._subscribers.discard(subscriber)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    # ---- 补发 ----

    def replay_since(self, since: Optional[int]) -> Optional[List[dict]]:
        """
        把 `since` 之后的事件取出来

        返回 None 表示补不上了（缓冲区已经滚过 since，或者 since 根本不合法），
        调用方应当让客户端重新拉快照
        """
        if since is None:
            return None

        if since > self._seq:
            # 客户端的编号比服务端还新：多半是后端重启过，编号从头开始了。
            # 这种情况绝不能沉默地接着发，否则前端会一直等一个永远到不了的编号
            return None

        if since == self._seq:
            return []

        if not self._history:
            return None

        oldest = self._history[0]["seq"]

        if since < oldest - 1:
            return None

        return [message for message in self._history if message["seq"] > since]

    def reset(self) -> None:
        self._seq = 0

        self._history.clear()
