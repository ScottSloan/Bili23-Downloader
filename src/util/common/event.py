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

3. **默认不做 Qt 那样的「接收者析构即自动断开」。**
   纯 Python 持有的是强引用，订阅者不会被回收。signal_bus 的订阅方都是随窗口存活的长生命周期
   对象，只在 __init__ 里连一次，不存在重建；临时订阅（MCP 的两处、SMS 的 cleanup）都有配对的
   disconnect。**新增订阅时若接收者会被重建，必须自己 disconnect，否则既泄漏又会把事件
   投给已废弃的对象。**

   例外是 `Event(weak = True)`：绑定方法改用弱引用持有，接收者被回收后自动摘除订阅。
   配置项的 valueChanged 走的就是这条路 —— 它原本是 ConfigItem（QObject）上的 Qt 信号，
   下载选项对话框那类每次打开都重建的控件会反复连上来，靠 Qt 的析构自动断开收尾。
   换成强引用会让这些控件永远无法回收，而且控件的 C++ 对象销毁后回调还会持续抛
   RuntimeError。**弱引用只覆盖绑定方法**：普通函数与闭包往往除连接外无人持有，
   一律弱引用会让它们当场失效。
"""

from threading import RLock
from typing import Callable
import logging
import weakref

from ..thread.dispatch import Dispatcher, get_default_dispatcher

logger = logging.getLogger(__name__)

def _make_ref(callback: Callable, on_dead: Callable):
    """
    绑定方法用 WeakMethod 持有，其余（普通函数、闭包、可调用对象）保持强引用

    绑定方法每次访问都是新对象，普通 weakref 指向的临时对象会立刻失效，必须用 WeakMethod。
    """
    if hasattr(callback, "__self__") and hasattr(callback, "__func__"):
        return weakref.WeakMethod(callback, on_dead)

    return None

class _Subscriber:
    """一条订阅记录。ref 为 None 表示强引用，回调直接放在 callback 上"""

    __slots__ = ("callback", "ref", "dispatcher", "__weakref__")

    def __init__(self, callback: Callable, ref, dispatcher):
        self.callback = None if ref is not None else callback
        self.ref = ref
        self.dispatcher = dispatcher

    def resolve(self):
        """取出真正的回调，接收者已被回收时返回 None"""
        if self.ref is None:
            return self.callback

        return self.ref()

    def matches(self, callback: Callable) -> bool:
        if self.ref is None:
            return self.callback is callback

        # 绑定方法每次访问都是新对象，不能用 is 比较，要比 __self__ 与 __func__
        current = self.ref()

        if current is None:
            return False

        return (current.__self__ is getattr(callback, "__self__", None)
                and current.__func__ is getattr(callback, "__func__", None))

class Event:
    __slots__ = ("_name", "_subscribers", "_lock", "_weak")

    def __init__(self, name: str, weak: bool = False):
        """
        weak = True 时，绑定方法改用弱引用持有，接收者被回收后订阅自动摘除。
        用于接收者会被反复重建的场景（配置项的 valueChanged），详见模块说明第 3 条
        """
        self._name = name
        self._weak = weak

        self._subscribers: list[_Subscriber] = []

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
            if any(sub.matches(callback) for sub in self._subscribers):
                # Qt 允许重复连接并会重复触发，这里按「同一个回调只订阅一次」处理：
                # 重复连接在本项目里只会是失误，而重复触发极难排查
                logger.debug("事件 %s 重复订阅同一回调，已忽略", self._name)

                return

            ref = _make_ref(callback, self._on_dead) if self._weak else None

            self._subscribers.append(_Subscriber(callback, ref, dispatcher))

    def disconnect(self, callback: Callable) -> None:
        """
        取消订阅。未订阅时静默返回（Qt 会抛异常，调用方为此普遍套了 try/except）
        """
        with self._lock:
            for index, sub in enumerate(self._subscribers):
                if sub.matches(callback):
                    del self._subscribers[index]

                    return

    def emit(self, *args, **kwargs) -> None:
        with self._lock:
            subscribers = list(self._subscribers)

        if not subscribers:
            return

        default = get_default_dispatcher()

        for sub in subscribers:
            callback = sub.resolve()

            # 接收者已被回收（weak = True 时才可能出现），跳过。
            # 清理由 _on_dead 负责，这里不动订阅表 —— emit 在锁外执行
            if callback is None:
                continue

            (sub.dispatcher or default).dispatch(self._invoke, (callback, args, kwargs), {})

    def _on_dead(self, ref) -> None:
        """
        弱引用失效时的回调。**它可能在任意线程、甚至在 GC 过程中被调用**，
        因此只做「从列表里摘掉这一项」这一件事，不发日志也不触发用户代码
        """
        with self._lock:
            for index, sub in enumerate(self._subscribers):
                if sub.ref is ref:
                    del self._subscribers[index]

                    return

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
            count = sum(1 for sub in self._subscribers if sub.resolve() is not None)

        return f"<Event {self._name} subscribers={count}>"
