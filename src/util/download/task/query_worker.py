from PySide6.QtCore import QObject, Signal, Slot

from ...common.enum import DownloadStatus

from .manager import task_manager
from .info import TaskInfo

from typing import List
import logging

logger = logging.getLogger(__name__)

class QueryWorker(QObject):
    # 第三个参数：已完成列表第一页的总数。
    # 把已完成列表第一页也纳入这个 worker，避免在 GUI 线程里做同步数据库查询。
    # 该 worker 只在启动时构造一次，翻页 / 搜索 / 筛选等后续请求仍由
    # DownloadInterface 单独同步处理，不会反复建 QThread。
    success = Signal(list, list, int)
    error = Signal(str)
    finished = Signal()

    def __init__(self, page_size: int, order_by: str, ascending: bool):
        super().__init__()

        self.page_size = page_size
        self.order_by = order_by
        self.ascending = ascending

    @Slot()
    def run(self):
        try:
            self.query()

            logger.info("从数据库中查询下载任务成功")

        except Exception as e:
            logger.exception("从数据库中查询下载任务失败")

            self.error.emit(str(e))

        finally:
            self.finished.emit()

    def query(self):
        downloading_tasks = task_manager.query()

        # 已完成列表第一页由这里一并取回，避免 DownloadInterface 在 GUI 线程里
        # 再做一次同步查询。参数在构造时由调用方传入（与界面当前的排序设置一致），
        # 关键词与媒体筛选在启动时都是空，翻页、搜索、筛选等后续请求仍由
        # DownloadInterface 单独处理。
        #
        # 数据库升级失败时 query_completed_page / count_completed 返回空 / 0，
        # 与 DownloadInterface._load_completed_page 的降级行为一致。
        completed_tasks = task_manager.query_completed_page(
            offset = 0,
            limit = self.page_size,
            order_by = self.order_by,
            ascending = self.ascending,
            keyword = "",
            media_types = frozenset(),
        )

        completed_total = task_manager.count_completed("", frozenset())

        downloading_tasks = self.get_task_list(downloading_tasks, update_status = True)

        self.success.emit(downloading_tasks, completed_tasks, completed_total)

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