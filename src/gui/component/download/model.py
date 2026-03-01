from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot

from util.download.cover.manager import cover_manager
from util.download.cover.cache import CoverCache
from util.download.task.info import TaskInfo
from util.common.enum import DownloadStatus
from util.common.config import config

from typing import List, Dict, Set

class DownloadListModel(QAbstractListModel):    
    def __init__(self, task_list: list, parent = None):
        super().__init__(parent)

        self._task_list: List[TaskInfo] = task_list
        self.cover_waiting_rows: Dict[str, Set[int]] = {}

    def rowCount(self, parent = QModelIndex()):
        return len(self._task_list)
    
    def data(self, index: QModelIndex, role = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return
        
        task_info = self._task_list[index.row()]
        
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return task_info["task_id"]
            
            case Qt.ItemDataRole.UserRole:
                return task_info
    
    def queryRowCover(self, cover_id: str, cover_url: str, row: int):
        # 由委托发起查询封面请求

        cahce = cover_manager.getCache(cover_id)

        # 命中缓存，直接返回
        if cahce:
            return cahce

        # 记录等待该cover_id的所有row
        waiting_set = self.cover_waiting_rows.setdefault(cover_id, set())

        if row not in waiting_set:
            waiting_set.add(row)

            # 只在首次请求时启动worker
            if len(waiting_set) == 1:                
                cover_manager.request(self, cover_id, cover_url)

        return cover_manager.placeholder()

    @Slot(str)
    def updateRowCover(self, cover_id: str):
        # 更新所有等待该cover_id的行
        if cover_id in self.cover_waiting_rows:

            rows = self.cover_waiting_rows[cover_id]

            for row in rows:
                index = self.index(row)
                self.dataChanged.emit(index, index)

            del self.cover_waiting_rows[cover_id]

    def appendRow(self, task_info: TaskInfo):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row)

        self._task_list.append(task_info)

        self.endInsertRows()

    def appendRows(self, task_info_list: List[TaskInfo]):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row + len(task_info_list) - 1)

        self._task_list.extend(task_info_list)

        self.endInsertRows()

    def manageConcurrentDownloads(self):
        # 自动调度同时下载的任务数量

        while True:
            downloads = [item for item in self._task_list if item.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PARSING]]
            queued = [item for item in self._task_list if item.Download.status == DownloadStatus.QUEUED]

            if len(downloads) >= config.get(config.download_parallel) or not queued:
                break

            next_task = queued.pop(0)
            self.on_pause_resume(next_task)
        
        self.manageConcurrentMerges()

    def manageConcurrentMerges(self):
        # 自动调度同时合并的任务数量
        # 为避免多个合并任务同时进行导致高频资源占用，每次只允许一个合并任务进行，其他等待合并的任务都处于等待合并状态，由 manage_concurrent_merges 统一调度

        while True:
            merging = [item for item in self._task_list if item.Download.status == DownloadStatus.MERGING]
            merge_queued = [item for item in self._task_list if item.Download.status == DownloadStatus.MERGE_QUEUED]

            if len(merging) >= 1 or not merge_queued:
                break

            next_task = merge_queued.pop(0)
            self.on_pause_resume(next_task)
