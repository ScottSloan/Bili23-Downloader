from PySide6.QtCore import QObject, Signal, Slot

from ...download.task.info import TaskInfo

from .runner import AdditionalRunner

import logging

logger = logging.getLogger(__name__)

class AdditionalParseWorker(QObject):
    """
    桌面侧的薄壳：把 `AdditionalRunner` 包成 `AsyncTask.run()` 认的 worker

    编排本身在 runner.py，不依赖 Qt，WebUI 走同一份 —— 两端产出的附加文件因此一致
    """

    success = Signal()
    error = Signal(str)
    finished = Signal()

    def __init__(self, task_info: TaskInfo):
        super().__init__()

        self.task_info = task_info

    @Slot()
    def run(self):
        try:
            AdditionalRunner(self.task_info).run()

            self.success.emit()

        except Exception as e:
            self.error.emit(str(e))

            logger.exception("附加文件解析失败")

        finally:
            self.finished.emit()
