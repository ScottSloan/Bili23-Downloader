from PySide6.QtCore import QModelIndex, Qt, QSize
from PySide6.QtWidgets import QAbstractItemView

from gui.component.view_model.model_base import CoverQueryModelBase

from util.download.downloader.manager import downloader_manager
from util.download.task.manager import task_manager
from util.download.task.info import TaskInfo
from util.common.enum import DownloadStatus
from util.common import signal_bus, config

from typing import List

class DownloadListModel(CoverQueryModelBase):    
    def __init__(self, task_list: list, parent = None):
        super().__init__(parent)

        self._cover_size = QSize(144, 80)
        self._task_list: List[TaskInfo] = task_list

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
    
    def getRow(self, task_info: TaskInfo):
        task_id = task_info.Basic.task_id
        for i, task in enumerate(self._task_list):
            if task.Basic.task_id == task_id:
                return i
        return -1

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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"togglePauseResume - task_info.cookie_file: {task_info.cookie_file}")
        
        downloader = downloader_manager.get(task_info, create_if_not_exists = True) 

        match task_info.Download.status:
            case DownloadStatus.QUEUED:
                # 启动下载 - 设置回调以更新 UI
                downloader.set_callbacks(
                    progress=lambda data: self._on_download_progress(task_info, data),
                    finish=lambda url: self._on_download_finish(task_info),
                    error=lambda msg: self._on_download_error(task_info, msg)
                )
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
                downloader.set_callbacks(
                    progress=lambda data: self._on_download_progress(task_info, data),
                    finish=lambda url: self._on_download_finish(task_info),
                    error=lambda msg: self._on_download_error(task_info, msg)
                )
                downloader.retry()

        self.onUpdateData(task_info)

    def _on_download_progress(self, task_info: TaskInfo, data: dict):
        """处理下载进度更新"""
        if data.get("status") == "downloading":
            percent_str = data.get("percent", "0%")
            try:
                percent = float(percent_str.replace("%", "").strip())
                task_info.Download.progress = percent
            except ValueError:
                pass
            task_info.Download.speed = data.get("speed", 0)
            task_info.Download.info_label = f"{data.get('speed_str', '')} - {data.get('eta', '')}"
        
        # 使用信号总线确保 UI 更新在主线程中执行
        signal_bus.download.update_downloading_item.emit(task_info)

    def _on_download_finish(self, task_info: TaskInfo):
        """处理下载完成"""
        task_info.Download.status = DownloadStatus.COMPLETED
        task_info.Download.progress = 100
        
        # 使用信号总线确保 UI 更新在主线程中执行
        signal_bus.download.update_downloading_item.emit(task_info)
        
        # 从下载列表移除，添加到完成列表
        signal_bus.download.remove_from_downloading_list.emit(task_info)
        signal_bus.download.add_to_completed_list.emit([task_info])
        
        # 保存到数据库的完成记录
        task_manager.mark_as_completed(task_info)
        
        self.manageConcurrentDownloads()

    def _on_download_error(self, task_info: TaskInfo, error_msg: str):
        """处理下载错误"""
        task_info.Download.status = DownloadStatus.FAILED
        task_info.Download.info_label = f"错误: {error_msg}"
        
        # 使用信号总线确保 UI 更新在主线程中执行
        signal_bus.download.update_downloading_item.emit(task_info)
        
        self.manageConcurrentDownloads()

    def cancelDownload(self, task_info: TaskInfo):
        import logging
        logger = logging.getLogger(__name__)
        
        match task_info.Download.status:
            case DownloadStatus.COMPLETED:
                logger.info(f"删除已完成任务: {task_info.Basic.task_id}, title={task_info.Basic.show_title}")
                task_manager.delete(task_info, completed = True)
                self.removeRow(self.getRow(task_info))
                logger.info(f"已从 UI 移除任务")

            case DownloadStatus.DOWNLOADING | DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                downloader_manager.wait(task_info, lambda: self._cancelAndRemove(task_info))

            case _:
                self._cancelAndRemove(task_info)

        # 更新下载数量徽章
        signal_bus.download.update_downloading_count.emit(self.rowCount())

    def _cancelAndRemove(self, task_info: TaskInfo):
        task_manager.cancel(task_info)
        row = self.getRow(task_info)
        if row != -1:
            self.removeRow(row)

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
        self.beginResetModel()

        for task in list(self._task_list):
            if task.Download.status not in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
                # 只有非合并中的任务才允许取消
                self.cancelDownload(task)

        self.endResetModel()
        
        # 确保所有任务都被移除
        self._task_list.clear()
        
        # 更新下载数量徽章
        signal_bus.download.update_downloading_count.emit(0)

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

    def redownload(self, task_info: TaskInfo):
        # 重新下载任务

        downloader = downloader_manager.get(task_info, create_if_not_exists=False)

        if task_info.Download.status == DownloadStatus.COMPLETED:
            # 已完成的任务需要从完成的列表中移动到正在下载的列表
            task_manager.reset(task_info)

            signal_bus.download.remove_from_completed_list.emit(task_info)

            task_manager.recreate(task_info)

            return

        elif task_info.Download.status == DownloadStatus.DOWNLOADING:
            if downloader:
                downloader.pause()

        elif task_info.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
            # 合并和转换中的任务不允许重新下载
            return

        task_manager.reset(task_info)
        self.onUpdateData(task_info)

        self.manageConcurrentDownloads()
