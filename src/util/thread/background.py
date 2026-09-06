"""
后台执行「跑一下就完」的任务

**不依赖 Qt，两端共用。** 桌面侧原先用的是 `thread/pool.py` 的 `GlobalThreadPoolTask`
（`QThreadPool.globalInstance()`），但 `download/task/manager.py` 是 WebUI 必然要用的，
它不能拖着 Qt。

与 `QThreadPool.globalInstance()` 的一个实际差别：**这里是独立的池，不与分片下载线程争抢**。
桌面侧的分片下载仍走 QThreadPool，WebUI 侧的字节搬运在 aria2 进程里，
两边都不会因为「建任务」这种短活挤掉下载线程。

线程不是 daemon 的，解释器退出时 `concurrent.futures` 的 atexit 钩子会等它们结束。
桌面版的退出走 `os._exit()`（见 main.py 的 shutdown_process），根本到不了 atexit，
所以不会因此挂住；WebUI 侧走正常退出，这里的任务都是短活，等一下无妨。
"""

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Optional
import logging
import threading

logger = logging.getLogger(__name__)

# 建任务、二次解析这类活是 IO 密集且数量有限的，池子不需要大。
# 太大反而会在批量添加时同时打出几十个请求
MAX_WORKERS = 4

_executor: Optional[ThreadPoolExecutor] = None
_lock = threading.Lock()

def _get_executor() -> ThreadPoolExecutor:
    global _executor

    if _executor is None:
        with _lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers = MAX_WORKERS, thread_name_prefix = "background")

    return _executor

def submit(func: Callable, *args: Any, **kwargs: Any) -> Future:
    """提交任务并拿到 Future。需要结果或要等它完成时用这个"""
    return _get_executor().submit(func, *args, **kwargs)

def run(func: Callable, *args: Any, **kwargs: Any) -> None:
    """
    即发即忘

    **异常在这里就地记日志**：不这么做的话，异常会被吞在没人看的 Future 里，
    表现为「点了添加任务但什么都没发生」，且日志里一片干净
    """
    def wrapper():
        try:
            func(*args, **kwargs)

        except Exception:
            logger.exception("后台任务执行失败：%s", getattr(func, "__qualname__", repr(func)))

    _get_executor().submit(wrapper)

def shutdown(wait: bool = False, timeout: float = None) -> None:
    """
    关闭线程池

    wait = False 时只是不再接受新任务，已在跑的会继续 —— 退出流程不该被一个
    还在等网络超时的解析卡住
    """
    global _executor

    executor = _executor
    _executor = None

    if executor is None:
        return

    try:
        if timeout is not None:
            # Python 3.9+ 才有 cancel_futures，用它把还没开始的任务丢掉
            executor.shutdown(wait = wait, cancel_futures = True)

        else:
            executor.shutdown(wait = wait)

    except Exception:
        logger.exception("关闭后台线程池时出错")
