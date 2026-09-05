"""
回调调度层

这一层存在的唯一理由：**Qt Signal 有一个纯 Python 实现给不了的语义 —— 跨线程时自动
把调用排队到接收者所在的线程。**

现状是这样的（Qt 的 AutoConnection 规则）：

- 接收者是 QObject 的绑定方法 → Qt 按接收者所在线程排队，实际都落在 GUI 线程；
  发射方本就在 GUI 线程时退化为同步直调
- 接收者是普通函数、闭包或非 QObject 的方法 → 直连，**就地跑在发射方线程上**

把 signal_bus 换成纯 Python 的 EventBus 之后，默认行为会变成「一律就地执行」。
GUI 侧那三十多个订阅者绝大多数要碰 QWidget / QAbstractItemModel / QPixmap，
在解析线程或下载线程里直接调用它们，轻则「Cannot create children for a parent that is
in a different thread」，重则访问违例；而且是偶发、难复现的那一类崩溃。
这个仓库在线程析构上已经栽过两次，不能再靠运气。

所以：**EventBus 不直接调用回调，一律交给这里的 Dispatcher。** 桌面侧装一个把调用投递回
GUI 线程的实现，服务端侧装一个推进事件队列的实现，core 本身不认识 Qt。

默认值刻意选「投递到主线程」而不是「就地执行」：
选错方向的代价不对等 —— 该排队却直连会崩，不该排队却排队只是多一次入队。
少数确实需要就地执行的订阅者（比如接收者本身就要在工作线程上干活）显式传
DIRECT 即可。
"""

from typing import Any, Callable, Protocol
import logging

logger = logging.getLogger(__name__)

class Dispatcher(Protocol):
    """把一次回调调用投递到合适的线程上执行"""

    def dispatch(self, func: Callable, args: tuple, kwargs: dict) -> None: ...

class DirectDispatcher:
    """
    就地执行，等价于 Qt 的 DirectConnection

    仅用于确认过不碰 GUI 对象、且需要留在发射方线程上的回调
    """
    def dispatch(self, func: Callable, args: tuple, kwargs: dict) -> None:
        func(*args, **kwargs)

DIRECT = DirectDispatcher()

# 进程级默认调度器。桌面侧在启动早期换成投递回 GUI 线程的实现，
# 服务端侧换成推进事件队列的实现；两者都没装时退化为就地执行
_default: Dispatcher = DIRECT

def set_default_dispatcher(dispatcher: Dispatcher) -> None:
    global _default

    _default = dispatcher

    logger.debug("默认回调调度器已设为 %s", type(dispatcher).__name__)

def get_default_dispatcher() -> Dispatcher:
    return _default

def dispatch(func: Callable, *args: Any, **kwargs: Any) -> None:
    """按默认调度器投递一次调用"""
    _default.dispatch(func, args, kwargs)
