from PySide6.QtCore import QObject, Signal, Slot, QCoreApplication

from functools import wraps
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class _MainThreadDispatcher(QObject):
    """
    把任意可调用对象投递到 GUI 线程执行

    AsyncTask 的 worker 信号是在子线程发出的，回调落在哪个线程取决于连接形式：
    连到 QObject 的方法时 Qt 会自动排队回该对象所在线程，而连到局部闭包或 lambda
    时是就地直连，回调整个跑在子线程里。后者碰 Qt 控件、QPixmap、QTimer 或全局
    可变状态都不安全，且显式指定 Qt.QueuedConnection 也修不了 —— 无 context 时
    Qt 按 sender 线程排队，而 sender 正是子线程里的 worker。

    这里用一个常驻 GUI 线程的 QObject 做中转：子线程 emit，Qt 按 AutoConnection
    排队到 GUI 线程的事件循环里执行。调用方本就在 GUI 线程时退化为直连，保持同步语义。
    """
    _invoke = Signal(object, object, object)

    def __init__(self):
        super().__init__()

        app = QCoreApplication.instance()

        # 首次使用可能发生在子线程，需要把自己迁到 GUI 线程，否则中转没有意义
        if app is not None and app.thread() is not self.thread():
            self.moveToThread(app.thread())

        self._invoke.connect(self._on_invoke)

    @Slot(object, object, object)
    def _on_invoke(self, func, args, kwargs):
        try:
            func(*args, **kwargs)

        except Exception:
            # 排队执行时异常会在 GUI 线程的事件循环里抛出，PySide 处理不了会直接终止进程
            logger.exception("主线程回调执行失败：%s", getattr(func, "__qualname__", func))

    def post(self, func, args, kwargs):
        self._invoke.emit(func, args, kwargs)

_dispatcher: _MainThreadDispatcher = None
_dispatcher_lock = Lock()

def _get_dispatcher():
    global _dispatcher

    if _dispatcher is None:
        with _dispatcher_lock:
            if _dispatcher is None:
                _dispatcher = _MainThreadDispatcher()

    return _dispatcher

def post_to_main_thread(func, *args, **kwargs):
    """
    把 func 投递到 GUI 线程执行，调用方已在 GUI 线程时直接同步执行
    """
    _get_dispatcher().post(func, args, kwargs)

def run_in_main_thread(func):
    """
    包装回调，使其无论从哪个线程被触发都在 GUI 线程执行

    用于 AsyncTask 的 worker 信号回调：`worker.success.connect(run_in_main_thread(on_success))`
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        post_to_main_thread(func, *args, **kwargs)

    return wrapper
