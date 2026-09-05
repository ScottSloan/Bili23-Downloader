"""
纯 Python 的事件对象，用于替代 Qt 的 Signal

API 形态与 Qt Signal 保持一致（connect / disconnect / emit），调用方零改动。
与 Qt 的行为差异有三处，都是有意为之：

1. **线程投递交给 util/thread/dispatch，而不是靠接收者是不是 QObject 来决定。**
   Qt 的规则是隐式的：接收者是 QObject 的绑定方法就排队回它所在的线程，
   是普通函数或闭包就地直连。这条规则纯 Python 复刻不了，也不该复刻 ——
   改成统一走调度器，桌面侧投递回 GUI 线程，服务端侧推进事件队列。
   详见 util/thread/dispatch.py 开头的说明。

2. **回调抛异常只记日志，不打断其他订阅者。**
   一条事件常有多个互不相干的订阅者，让其中一个的失败连累其余没有道理。
   Qt 的排队连接本来也会把异常吞在事件循环里（见 thread/dispatcher.py）。

3. **不做 Qt 那样的「接收者析构即自动断开」。**
   纯 Python 持有的是强引用，订阅者不会被回收。现有订阅方都是随窗口存活的长生命周期对象，
   只在 __init__ 里连一次，不存在重建；临时订阅（MCP 的两处、SMS 的 cleanup）都有配对的
   disconnect。**新增订阅时若接收者会被重建，必须自己 disconnect，否则既泄漏又会把事件
   投给已废弃的对象。**
"""

from threading import RLock
from typing import Callable
import logging

from ..thread.dispatch import Dispatcher, get_default_dispatcher

logger = logging.getLogger(__name__)

class Event:
    __slots__ = ("_name", "_subscribers", "_lock")

    def __init__(self, name: str):
        self._name = name

        # [(回调, 调度器或 None)]，None 表示用发射时的默认调度器
        self._subscribers: list[tuple[Callable, Dispatcher | None]] = []

        # 保护订阅表。emit 只在锁内取一份快照，回调在锁外执行 ——
        # 否则订阅者在回调里再 connect / disconnect 就会自锁
        self._lock = RLock()

    @property
    def name(self) -> str:
        return self._name

    def connect(self, callback: Callable, dispatcher: Dispatcher = None) -> None:
        """
        订阅。dispatcher 传 DIRECT 可要求就地执行，默认走全局调度器
        """
        with self._lock:
            if any(existing is callback for existing, _ in self._subscribers):
                # Qt 允许重复连接并会重复触发，这里按「同一个回调只订阅一次」处理：
                # 重复连接在本项目里只会是失误，而重复触发极难排查
                logger.debug("事件 %s 重复订阅同一回调，已忽略", self._name)

                return

            self._subscribers.append((callback, dispatcher))

    def disconnect(self, callback: Callable) -> None:
        """
        取消订阅。未订阅时静默返回（Qt 会抛异常，调用方为此普遍套了 try/except）
        """
        with self._lock:
            for index, (existing, _) in enumerate(self._subscribers):
                if existing is callback:
                    del self._subscribers[index]

                    return

    def emit(self, *args, **kwargs) -> None:
        with self._lock:
            subscribers = list(self._subscribers)

        if not subscribers:
            return

        default = get_default_dispatcher()

        for callback, dispatcher in subscribers:
            (dispatcher or default).dispatch(self._invoke, (callback, args, kwargs), {})

    def __call__(self, *args, **kwargs) -> None:
        """
        等价于 emit

        Qt Signal 本身可以作为另一个信号的槽（`qt_signal.connect(bus_event)`），
        换成 Event 之后 Qt 会因为它既不是信号也不是可调用对象而拒绝连接
        （gui/interface/setting.py 的 mica_effect_switch 就是这么用的）。
        实现 __call__ 让这种写法继续可用，调用方无需改动
        """
        self.emit(*args, **kwargs)

    def _invoke(self, callback: Callable, args: tuple, kwargs: dict) -> None:
        try:
            callback(*args, **kwargs)

        except Exception:
            # 一个订阅者出问题不该连累其他订阅者，也不该把异常抛回发射方 ——
            # 发射方往往是解析、下载线程，异常冒上去只会让那条链路整个断掉
            logger.exception("事件 %s 的订阅者执行失败：%s", self._name,
                             getattr(callback, "__qualname__", callback))

    def __repr__(self) -> str:
        with self._lock:
            count = len(self._subscribers)

        return f"<Event {self._name} subscribers={count}>"
