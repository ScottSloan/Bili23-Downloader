from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThreadPool, QRunnable

pool = QThreadPool.globalInstance()


class GlobalThreadPoolTask:
    @staticmethod
    def run(runnable: QRunnable) -> None:
        pool.start(runnable)

    @staticmethod
    def run_func(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        class FuncRunnable(QRunnable):
            def __init__(self):
                super().__init__()

            def run(self):
                func(*args, **kwargs)

        pool.start(FuncRunnable())
