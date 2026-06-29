from PySide6.QtCore import QThreadPool, QRunnable

from collections.abc import Callable
from typing import Any
import logging

pool = QThreadPool.globalInstance()
logger = logging.getLogger(__name__)


class GlobalThreadPoolTask:
    @staticmethod
    def run(runnable: QRunnable) -> None:
        pool.start(runnable)

    @staticmethod
    def run_func(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        class FuncRunnable(QRunnable):
            def run(self):
                try:
                    func(*args, **kwargs)

                except Exception:
                    logger.exception("后台任务触发异常： %s", getattr(func, "__qualname__", repr(func)))

        pool.start(FuncRunnable())
