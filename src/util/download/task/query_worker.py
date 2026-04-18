from PySide6.QtCore import QObject, Signal, Slot

from util.common.enum import DownloadStatus

from .manager import task_manager
from .info import TaskInfo

from typing import List
import logging

logger = logging.getLogger(__name__)

class QueryWorker(QObject):
    success = Signal(list, list)
    error = Signal(str)
    finished = Signal()

    def __init__(self):
        super().__init__()

    @Slot()
    def run(self):
        try:
            self.query()

        except Exception as e:
            logger.exception("从数据库中查询下载任务失败")

            self.error.emit(str(e))

        finally:
            self.finished.emit()

    def query(self):
        downloading_tasks = task_manager.query()
        completed_tasks = task_manager.query(completed = True)

        downloading_tasks = self.get_task_list(downloading_tasks, update_status = True)
        completed_tasks = self.get_task_list(completed_tasks, update_status = False)

        self.success.emit(downloading_tasks, completed_tasks)

    def get_task_list(self, task_info_list: List[TaskInfo], update_status = True):
        task_list = []

        for task_info in task_info_list:
            if update_status:
                if task_info.Download.status in [DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING, DownloadStatus.PARSING]:
                    task_info.Download.status = DownloadStatus.PAUSED

                if task_info.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING, DownloadStatus.ADDITIONAL_PROCESSING]:
                    # 统一为 PAUSED 状态
                    task_info.Download.status = DownloadStatus.PAUSED

            task_list.append(task_info)

        return task_list
