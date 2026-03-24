from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot
from PySide6.QtWidgets import QAbstractItemView

from util.download.downloader.manager import downloader_manager
from util.download.cover.manager import cover_manager
from util.download.task.manager import task_manager
from util.common.signal_bus import signal_bus
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

    def getRow(self, task_info: TaskInfo):
        try:
            return self._task_list.index(task_info)
        
        except ValueError:
            return -1

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

    def updateRows(self, start_row: int, end_row: int):
        for row in range(start_row, end_row + 1):
            index = self.index(row)

            self.dataChanged.emit(index, index)

    def removeRow(self, row, parent = QModelIndex()):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(parent, row, row)

            del self._task_list[row]

            self.endRemoveRows()

            return True
        
        return False

    def togglePauseResume(self, task_info: TaskInfo):
        # 在暂停与继续之间切换

        # 在此处实现懒加载，get不存在时会自动创建 Downloader 实例并加入管理器
        downloader = downloader_manager.get(task_info, create_if_not_exists = True) 

        match task_info.Download.status:
            case DownloadStatus.QUEUED:
                # 启动下载
                downloader.start()

            case DownloadStatus.DOWNLOADING:
                # 暂停下载
                downloader.pause()

                self.manageConcurrentDownloads()

            case DownloadStatus.PAUSED:
                # 继续下载
                downloader.resume()

            case DownloadStatus.FFMPEG_QUEUED:
                # 启动合并
                downloader.start_merge()

            case DownloadStatus.FAILED | DownloadStatus.FFMPEG_FAILED:
                # 重试下载
                downloader.retry()

        self.onUpdateData(task_info)

    def cancelDownload(self, task_info: TaskInfo):
        match task_info.Download.status:
            case DownloadStatus.COMPLETED:
                task_manager.delete(task_info, completed = True)

                self.removeRow(self.getRow(task_info))

            case DownloadStatus.DOWNLOADING:
                downloader_manager.wait(task_info, lambda: task_manager.cancel(task_info))

            case DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                # 合并和转换中的任务不允许取消
                return

            case _:
                task_manager.cancel(task_info)

    def batchStart(self):
        for task in self._task_list:
            if task.Download.status in [DownloadStatus.PAUSED, DownloadStatus.FFMPEG_FAILED, DownloadStatus.FAILED]:
                # 从暂停状态变为等待状态，由 manage_concurrent_downloads 统一调度
                task.Download.status = DownloadStatus.QUEUED

                self.onUpdateData(task)

        self.manageConcurrentDownloads()

    def batchPause(self):
        for task in self._task_list:
            if task.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED]:
                task.Download.status = DownloadStatus.PAUSED
                downloader = downloader_manager.get(task, create_if_not_exists = False)

                downloader.pause()

                self.onUpdateData(task)

    def batch_cancel(self):
        self.beginResetModel()

        for task in list(self._task_list):
            if task.Download.status not in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
                # 只有非合并中的任务才允许取消
                self.cancelDownload(task)

        self.endResetModel()

    def manageConcurrentDownloads(self):
        # 自动调度同时下载的任务数量

        while True:
            downloads = [item for item in self._task_list if item.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PARSING]]
            queued = [item for item in self._task_list if item.Download.status == DownloadStatus.QUEUED]

            if len(downloads) >= config.get(config.download_parallel) or not queued:
                break

            next_task = queued.pop(0)
            self.togglePauseResume(next_task)
        
        self.manageConcurrentMerges()

    def manageConcurrentMerges(self):
        # 自动调度同时合并的任务数量
        # 为避免多个合并任务同时进行导致高频资源占用，每次只允许一个合并任务进行，其他等待合并的任务都处于等待合并状态，由 manage_concurrent_merges 统一调度

        while True:
            merging = [item for item in self._task_list if item.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]]
            merge_queued = [item for item in self._task_list if item.Download.status == DownloadStatus.FFMPEG_QUEUED]

            if len(merging) >= 1 or not merge_queued:
                break

            next_task = merge_queued.pop(0)
            self.togglePauseResume(next_task)

    def connectUpdateDataSignal(self):
        signal_bus.download.update_downloading_item.connect(self.onUpdateData)

    def onUpdateData(self, task_info: TaskInfo):
        row = self.getRow(task_info)

        if row != -1 and self.isRowInVisibleArea(row):
            model_index = self.index(row)

            self.dataChanged.emit(model_index, model_index)

    def isRowInVisibleArea(self, row: int):
        # 判断指定行是否在可见区域内
        view: QAbstractItemView = self.parent()

        if view:
            viewport = view.viewport()
            item_rect = view.visualRect(self.index(row))

            return viewport.rect().intersects(item_rect)

        return False
