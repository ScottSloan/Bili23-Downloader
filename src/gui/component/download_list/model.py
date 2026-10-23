from PySide6.QtCore import QModelIndex, Qt, QSize
from PySide6.QtWidgets import QAbstractItemView

from util.download.downloader.manager import downloader_manager
from util.download.task.manager import task_manager
from util.download.task.info import TaskInfo
from util.common.signal_bus import signal_bus
from util.common.enum import DownloadStatus
from util.common.config import config

from ..view_model import CoverQueryModelBase

from typing import List


class DownloadListModel(CoverQueryModelBase):
    def __init__(self, task_list: list, parent=None):
        super().__init__(parent)

        self._cover_size = QSize(144, 80)
        self._task_list: List[TaskInfo] = task_list

        self._row_by_task_id: dict[str, int] = {}
        self._managing_concurrent = False
        self._managing_merges = False

        self._rebuild_row_index()

    def _get_task_id(self, task_info: TaskInfo):
        return task_info.Basic.task_id

    def _rebuild_row_index(self):
        self._row_by_task_id = {
            task_info.Basic.task_id: row
            for row, task_info in enumerate(self._task_list)
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._task_list)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return

        task_info = self._task_list[index.row()]

        match role:
            case Qt.ItemDataRole.DisplayRole:
                return task_info.Basic.task_id

            case Qt.ItemDataRole.UserRole:
                return task_info

    def getRow(self, task_info: TaskInfo):
        return self._row_by_task_id.get(self._get_task_id(task_info), -1)

    def appendRow(self, task_info: TaskInfo):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row)

        self._task_list.append(task_info)

        self.endInsertRows()

        self._row_by_task_id[task_info.Basic.task_id] = row

    def appendRows(self, task_info_list: List[TaskInfo]):
        if not task_info_list:
            return

        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row + len(task_info_list) - 1)

        self._task_list.extend(task_info_list)

        self.endInsertRows()

        for row, task_info in enumerate(self._task_list):
            self._row_by_task_id[task_info.Basic.task_id] = row

    def updateRows(self, start_row: int, end_row: int):
        for row in range(start_row, end_row + 1):
            if not self.isRowInVisibleArea(row):
                continue

            index = self.index(row)

            self.dataChanged.emit(index, index)

    def removeRow(self, row, parent=QModelIndex()):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(parent, row, row)

            del self._task_list[row]

            self.endRemoveRows()

            self._rebuild_row_index()

            return True

        return False

    def setPageTasks(self, task_info_list: List[TaskInfo]):
        # 分页模式下整页替换：行号全部变化，必须 reset
        self.beginResetModel()

        self._task_list[:] = task_info_list

        self.endResetModel()

        self._rebuild_row_index()

    def removeTasks(self, task_info_list: List[TaskInfo]):
        # 批量移除。逐行调用 removeRow 时每次都要重建行索引，整体为 O(n²)，
        # 此处一次性过滤并重建，整体为 O(n)。
        task_id_set = {self._get_task_id(task_info) for task_info in task_info_list}

        if not task_id_set:
            return

        self.beginResetModel()

        self._task_list[:] = [
            task_info for task_info in self._task_list
            if self._get_task_id(task_info) not in task_id_set
        ]

        self.endResetModel()

        self._rebuild_row_index()

    def togglePauseResume(self, task_info: TaskInfo):
        # 在暂停与继续之间切换

        # 在此处实现懒加载，get不存在时会自动创建 Downloader 实例并加入管理器
        downloader = downloader_manager.get(task_info, create_if_not_exists=True)

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
                # 数据库删除交由写线程处理，界面立即移除该行
                task_manager.delete(task_info, completed=True)

                self.removeRow(self.getRow(task_info))

            case DownloadStatus.DOWNLOADING:
                downloader_manager.wait(task_info, lambda: task_manager.cancel_async(task_info))

            case DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                # 合并和转换中的任务不允许取消
                return

            case _:
                task_manager.cancel_async(task_info)

    def batchStart(self, task_list: List[TaskInfo] = None):
        # task_list 为 None 时作用于整个列表；列表筛选生效时由代理模型传入当前可见的任务
        for task in self._targetTasks(task_list):
            if task.Download.status in [DownloadStatus.PAUSED, DownloadStatus.FFMPEG_FAILED, DownloadStatus.FAILED]:
                # 从暂停状态变为等待状态，由 manage_concurrent_downloads 统一调度
                task.Download.status = DownloadStatus.QUEUED

                self.onUpdateData(task)

        self.manageConcurrentDownloads()

    def batchPause(self, task_list: List[TaskInfo] = None):
        for task in self._targetTasks(task_list):
            if task.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED]:
                task.Download.status = DownloadStatus.PAUSED
                downloader = downloader_manager.get(task, create_if_not_exists=False)

                if downloader:
                    downloader.pause()

                self.onUpdateData(task)

    def batch_cancel(self, task_list: List[TaskInfo] = None):
        # 已完成的任务走批量路径：一次数据库删除 + 一次界面刷新。
        # 逐条处理时每条都要独立提交事务并重建行索引，任务较多时会长时间卡住界面。
        completed_tasks = []
        remaining_tasks = []

        for task in list(self._targetTasks(task_list)):
            match task.Download.status:
                case DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                    # 只有非合并中的任务才允许取消
                    continue

                case DownloadStatus.COMPLETED:
                    completed_tasks.append(task)

                case _:
                    remaining_tasks.append(task)

        if completed_tasks:
            task_manager.delete_many(completed_tasks, completed=True)

            self.removeTasks(completed_tasks)

        for task in remaining_tasks:
            self.cancelDownload(task)

    def _targetTasks(self, task_list: List[TaskInfo] = None):
        return self._task_list if task_list is None else task_list

    def manageConcurrentDownloads(self):
        # 启动任务时可能同步走完整个流程并反过来再次触发调度。
        # 单次扫描的实现依赖本地计数，需要屏蔽重入，避免超出并发上限。
        # 被跳过的那次调度由 auto_manage_concurrent_downloads 信号在事件循环中补上。
        if self._managing_concurrent:
            return

        self._managing_concurrent = True

        try:
            self._manageConcurrentDownloads()

        finally:
            self._managing_concurrent = False

    def _manageConcurrentDownloads(self):
        # 自动调度同时下载的任务数量。
        # 原实现每启动一个任务就重新扫描一遍列表，整体为 O(n²)，此处改为单次扫描后按需启动。
        limit = config.get(config.download_parallel)

        active_count = 0
        queued_tasks = []

        for item in self._task_list:
            match item.Download.status:
                case DownloadStatus.DOWNLOADING | DownloadStatus.PARSING:
                    active_count += 1

                case DownloadStatus.QUEUED:
                    queued_tasks.append(item)

        for task in queued_tasks:
            if active_count >= limit:
                break

            self.togglePauseResume(task)

            # 启动后任务可能直接跳到合并阶段，此时不占用下载并发额度
            if task.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PARSING]:
                active_count += 1

        self.manageConcurrentMerges()

    def manageConcurrentMerges(self):
        # 与下载调度同理，屏蔽重入
        if self._managing_merges:
            return

        self._managing_merges = True

        try:
            self._manageConcurrentMerges()

        finally:
            self._managing_merges = False

    def _manageConcurrentMerges(self):
        # 自动调度同时合并的任务数量
        # 为避免多个合并任务同时进行导致高频资源占用，每次只允许一个合并任务进行，其他等待合并的任务都处于等待合并状态，由 manage_concurrent_merges 统一调度

        merging_count = 0
        merge_queued_tasks = []

        for item in self._task_list:
            match item.Download.status:
                case DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                    merging_count += 1

                case DownloadStatus.FFMPEG_QUEUED:
                    merge_queued_tasks.append(item)

        for task in merge_queued_tasks:
            if merging_count >= 1:
                break

            self.togglePauseResume(task)

            # 无需调用 ffmpeg 的任务会同步完成，不占用合并额度
            if task.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
                merging_count += 1

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

        if view and view.isVisible():
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
            downloader.pause()

        elif task_info.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
            # 合并和转换中的任务不允许重新下载
            return

        task_manager.reset(task_info)
        self.onUpdateData(task_info)

        self.manageConcurrentDownloads()