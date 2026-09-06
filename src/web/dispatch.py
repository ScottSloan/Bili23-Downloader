"""
服务端侧的回调调度器

`util/thread/dispatch.py` 里说过这一层存在的理由：signal_bus 换成纯 Python 事件之后，
默认行为变成「一律就地执行」，而回调的发出点可能在任意工作线程上。
桌面侧装的是投递回 GUI 线程的实现，服务端侧就是这里 —— 投递回 **asyncio 事件循环所在的线程**。

## 为什么服务端也需要它

下载完成、合并完成、FFmpeg 进度这些回调都是从工作线程发出来的（aria2 的读取任务除外）。
不投递的话，它们会就地跑在 FFmpeg 线程或后台线程上，而这些回调最终要去改共享状态、
往 WebSocket 推事件 —— 后者更是**只能在事件循环线程上做**，在别的线程上调
`asyncio` 的东西不会报错，只会静默不生效（D16 记过同类现象）。

## 已经在循环线程上时直接调用

对齐 Qt 的 AutoConnection：发射方本就在目标线程时退化为同步直调。
不这么做的话，同一次调用链里「发出事件 → 处理 → 再发出事件」的顺序会被拆到不同的
循环迭代里，而现有代码（比如合并调度的重入保护）是照着同步语义写的。

代价是要容忍重入，这一点与桌面侧一致。
"""

from typing import Any, Callable, Optional
import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

class AsyncioDispatcher:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

        # 记下循环所在的线程 id。`asyncio.get_running_loop()` 只在协程里管用，
        # 而这里多数时候是从普通线程调进来的
        self._thread_id = threading.get_ident()

    def dispatch(self, func: Callable, args: tuple, kwargs: dict) -> None:
        if threading.get_ident() == self._thread_id:
            # 已经在循环线程上，直接调用（对齐 Qt 的 AutoConnection）
            self._invoke(func, args, kwargs)

            return

        try:
            self.loop.call_soon_threadsafe(self._invoke, func, args, kwargs)

        except RuntimeError:
            # 循环已经关掉了（退出流程中）。这时候丢掉回调是对的 ——
            # 抛出去只会把正在收尾的工作线程搞崩
            logger.debug("事件循环已关闭，丢弃回调：%s", getattr(func, "__qualname__", func))

    @staticmethod
    def _invoke(func: Callable, args: tuple, kwargs: dict) -> None:
        # 回调抛异常不能让循环或工作线程跟着倒下 —— 一个订阅者出错不该波及其他订阅者
        try:
            func(*args, **kwargs)

        except Exception:
            logger.exception("回调执行失败：%s", getattr(func, "__qualname__", repr(func)))

_installed: Optional[AsyncioDispatcher] = None

def install(loop: asyncio.AbstractEventLoop = None) -> AsyncioDispatcher:
    """把调度器装成进程默认。在事件循环线程上调用"""
    global _installed

    from util.thread.dispatch import set_default_dispatcher

    if loop is None:
        loop = asyncio.get_running_loop()

    _installed = AsyncioDispatcher(loop)

    set_default_dispatcher(_installed)

    return _installed

def get_installed() -> Optional[AsyncioDispatcher]:
    return _installed
