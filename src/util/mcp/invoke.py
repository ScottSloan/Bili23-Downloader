from ..thread.dispatcher import post_to_main_thread

from threading import Event
import logging

logger = logging.getLogger(__name__)

class MainThreadTimeout(Exception):
    """GUI 线程未能在预算内给出结果"""

# 程序开始退出后，投递到 GUI 线程的任务不再会被执行：aboutToQuit 发出时
# 事件循环已在收尾。此时若还按正常超时去等，在途的 MCP 请求会把 HTTP 线程
# 拖住整整一个 timeout，退出流程只能等到超时或被强制结束。
# 置位后所有跨线程调用立即失败，HTTP 线程得以迅速回到循环并退出。
_shutting_down = Event()

def begin_shutdown():
    _shutting_down.set()

def clear_shutdown():
    # 重启服务器（改端口、换令牌）同样会走 stop()，若不复位，重启后的所有请求
    # 都会立刻以"正在退出"失败
    _shutting_down.clear()

def is_shutting_down() -> bool:
    return _shutting_down.is_set()

class _Result:
    __slots__ = ("value", "error")

    def __init__(self):
        self.value = None
        self.error = None

def call_in_main_thread(func, *args, timeout: float = 30.0, **kwargs):
    """
    在 GUI 线程执行 func 并同步等待其返回值

    MCP 请求跑在 HTTP 工作线程上。该线程直接触碰 Qt 对象会触发
    "Cannot create children for a parent that is in a different thread"，
    紧随其后往往就是访问违例（见 main.py 的 THREAD_SAFETY_WARNINGS）。
    因此凡是要读写解析树、下载任务、config 的操作，都必须先回到 GUI 线程。

    这里借 post_to_main_thread 把调用排队到 GUI 线程的事件循环，再用 Event
    等回结果。超时是必需的：GUI 线程可能正卡在模态对话框上（下载选项、重复
    下载确认等），没有超时的话 HTTP 线程会一直挂着，客户端只能看到连接僵死。
    """
    if _shutting_down.is_set():
        raise MainThreadTimeout("程序正在退出，不再受理请求")

    result = _Result()
    done = Event()

    def runner():
        try:
            result.value = func(*args, **kwargs)

        except Exception as e:
            result.error = e

        finally:
            done.set()

    post_to_main_thread(runner)

    # 分段等待，退出开始后立即放弃，不必耗满整个预算
    deadline = timeout
    step = 0.2

    while deadline > 0:
        if done.wait(min(step, deadline)):
            break

        deadline -= step

        if _shutting_down.is_set():
            raise MainThreadTimeout("程序正在退出，请求已中止")

    if not done.is_set():
        raise MainThreadTimeout(f"等待主线程执行 {getattr(func, '__qualname__', func)} 超时（{timeout}s）")

    if result.error is not None:
        raise result.error

    return result.value

def wait_for_signal(signal, trigger, timeout: float = 60.0, predicate = None):
    """
    在 GUI 线程发起 trigger，并等待 signal 触发后返回其参数

    用于解析这类"发起与完成分离"的链路：ParseWorker 在自己的 QThread 上跑，
    完成后经 signal_bus 通知界面，调用方拿不到直接的返回值。

    连接必须赶在 trigger 之前建立，否则解析极快时信号会先于连接发出而丢失。
    predicate 用于过滤不属于本次调用的信号（界面上的解析同样会触发它）。
    """
    captured = {}
    done = Event()

    def on_signal(*args):
        if predicate is not None and not predicate(*args):
            return

        captured["args"] = args
        done.set()

    # 连接与断开都在 GUI 线程完成：signal 属于 GUI 线程的 QObject，
    # 从工作线程 connect 会把接收者绑到错误的线程上
    call_in_main_thread(signal.connect, on_signal, timeout = 5.0)

    try:
        call_in_main_thread(trigger, timeout = 10.0)

        if not done.wait(timeout):
            raise MainThreadTimeout(f"等待信号超时（{timeout}s）")

        return captured.get("args", ())

    finally:
        try:
            call_in_main_thread(signal.disconnect, on_signal, timeout = 5.0)

        except Exception:
            # 断开失败不影响本次调用的结果，但要留下痕迹：
            # 残留的连接会让后续解析重复触发这个已失效的回调
            logger.exception("断开信号连接失败")
