from PySide6.QtCore import QModelIndex, Qt, QSize
from PySide6.QtWidgets import QAbstractItemView

from util.download import TaskInfo, task_manager, downloader_manager
from util.common.enum import DownloadStatus
from util.common import signal_bus, config

from ..view_model import CoverQueryModelBase

from typing import List

class DownloadListModel(CoverQueryModelBase):    
    def __init__(self, task_list: list, parent = None):
        super().__init__(parent)

        self._cover_size = QSize(144, 80)
        self._task_list: List[TaskInfo] = task_list

        self._sorting = False
        self._sort_by_key = None
        self._ascending = True

    def _get_task_id(self, task_info: TaskInfo):
        return task_info.Basic.task_id

    def _applyCurrentSort(self):
        if self._sorting and self._sort_by_key:
            self.sortBy(self._sort_by_key, self._ascending)

    def rowCount(self, parent = QModelIndex()):
        return len(self._task_list)
    
    def data(self, index: QModelIndex, role = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return
        
        task_info = self._task_list[index.row()]
        
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return task_info.Basic.task_id
            
            case Qt.ItemDataRole.UserRole:
                return task_info
    
    def getRow(self, task_info: TaskInfo):
        task_id = self._get_task_id(task_info)

        for row, item in enumerate(self._task_list):
            if item.Basic.task_id == task_id:
                return row

        return -1

    def appendRow(self, task_info: TaskInfo):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row)

        self._task_list.append(task_info)

        self.endInsertRows()

        self._applyCurrentSort()

    def appendRows(self, task_info_list: List[TaskInfo]):
        if not task_info_list:
            return

        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row + len(task_info_list) - 1)

        self._task_list.extend(task_info_list)

        self.endInsertRows()

        self._applyCurrentSort()

    def updateRows(self, start_row: int, end_row: int):
        for row in range(start_row, end_row + 1):
            if not self.isRowInVisibleArea(row):
                continue

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

                if downloader:
                    downloader.pause()

                self.onUpdateData(task)

    def batch_cancel(self):
        for task in list(self._task_list):
            if task.Download.status not in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
                # 只有非合并中的任务才允许取消
                self.cancelDownload(task)

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

        if row == -1:
            return

        if self.isRowInVisibleArea(row):

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

    def redownload(self, task_info: TaskInfo):
        # 重新下载任务

        downloader = downloader_manager.get(task_info, create_if_not_exists = False)

  
        if task_info.Download.status == DownloadStatus.COMPLETED:
            # 已完成的任务需要从完成的列表中移动到正在下载的列表
            task_manager.reset(task_info)

            signal_bus.download.remove_from_completed_list.emit(task_info)

            task_manager.recreate(task_info)

            return

        elif task_info.Download.status == DownloadStatus.DOWNLOADING:
            downloader.pause()

        elif task_info.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
            # 合并和转换中的任务不允许重新下载
            return

        task_manager.reset(task_info)
        self.onUpdateData(task_info)

        self.manageConcurrentDownloads()

    def sortBy(self, key: str, ascending: bool = True):
        # 排序列表
        if not self._sorting:
            return
        
        self._sort_by_key = key
        self._ascending = ascending

        reverse = not ascending

        self.layoutAboutToBeChanged.emit()

        match key:
            case "created_time":
                self._task_list.sort(key = lambda x: x.Basic.created_time, reverse = reverse)

            case "completed_time":
                self._task_list.sort(key = lambda x: x.Basic.completed_time, reverse = reverse)

            case "show_title":
                self._task_list.sort(key = lambda x: x.Basic.show_title, reverse = reverse)

            case "file_size":
                self._task_list.sort(key = lambda x: x.Download.total_size, reverse = reverse)

            case "progress":
                self._task_list.sort(key = lambda x: x.Download.progress, reverse = reverse)

        self.layoutChanged.emit()

        self.updateRows(0, self.rowCount() - 1)

    def enableSorting(self, default_key: str):
        # 启用排序功能
        self._sorting = True
        self._sort_by_key = default_key

        self._applyCurrentSort()
        