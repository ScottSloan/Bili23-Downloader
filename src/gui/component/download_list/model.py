import logging

from PySide6.QtCore import QModelIndex, Qt, QSize, Signal
from PySide6.QtWidgets import QAbstractItemView

from util.download.downloader.manager import downloader_manager
from util.download.task.manager import task_manager
from util.download.task.info import TaskInfo
from util.common.signal_bus import signal_bus
from util.common.enum import DownloadStatus, ToastNotificationCategory
from util.common.config import config

from ..view_model import CoverQueryModelBase

from typing import List

logger = logging.getLogger(__name__)


class DownloadListModel(CoverQueryModelBase):
    # 行被删除后发射，参数为本次删除的数量。
    # 所有删除路径（cancelDownload、redownload、batch_cancel）最终都落到本模型的
    # removeRow 或 removeTasks，在这里发射可以覆盖全部
    row_removed = Signal(int)

    # 数据库已落盘的真正删除。redownload（移到下载中）也会走 removeRow，
    # 但那条路径下库里记录还在，此刻重载会让刚移除的行又出现。这个信号只由
    # cancelDownload / batch_cancel 的 COMPLETED 分支在 wait=True 落盘后发射，
    # 供分页条重载补位。参数为实际移除的行数（不是传入的任务数）
    task_permanently_deleted = Signal(int)

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

        start = self.rowCount()

        self.beginInsertRows(QModelIndex(), start, start + len(task_info_list) - 1)

        self._task_list.extend(task_info_list)

        self.endInsertRows()

        # 只有新追加的这几条行号是新增的，已有条目的行号不变。
        # 原实现遍历整个 _task_list 重建索引，每追加一条就是 O(n)，
        # 已完成列表累积到数万行时，每次下载完成都要走一遍全表
        for offset, task_info in enumerate(task_info_list):
            self._row_by_task_id[task_info.Basic.task_id] = start + offset

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

            self.row_removed.emit(1)

            return True

        return False

    def setPageTasks(self, task_info_list: List[TaskInfo]):
        # 分页模式下整页替换：行号全部变化，必须 reset
        self.beginResetModel()

        self._task_list[:] = task_info_list

        self.endResetModel()

        self._rebuild_row_index()

    def removeTasks(self, task_info_list: List[TaskInfo]) -> int:
        # 批量移除。逐行调用 removeRow 时每次都要重建行索引，整体为 O(n²)，
        # 此处一次性过滤并重建，整体为 O(n)。
        # 返回实际移除的行数：分页模式下 task_info_list 可能包含不在当前页的
        # 任务，与 len(task_info_list) 不同。调用方据此 emit 准确的删除数
        task_id_set = {self._get_task_id(task_info) for task_info in task_info_list}

        if not task_id_set:
            return 0

        before = len(self._task_list)

        self.beginResetModel()

        self._task_list[:] = [
            task_info for task_info in self._task_list
            if self._get_task_id(task_info) not in task_id_set
        ]

        self.endResetModel()

        self._rebuild_row_index()

        removed = before - len(self._task_list)

        if removed > 0:
            self.row_removed.emit(removed)

        return removed

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
                # wait=True：写完再移除，避免删完立即翻页又看到已删的记录。
                # 返回 False 说明写入失败（只读文件系统、磁盘满、写线程超时），
                # 保留界面行并 toast 提示，而不是静默失败
                if task_manager.delete(task_info, completed=True, wait=True):
                    # 只有真的在当前页移除了这一行才发 task_permanently_deleted。
                    # 分页模式下 task 理论上一定在当前页（用户右键的是可见行），
                    # 但 getRow 返回 -1 时 removeRow 会失败，此时不该触发补位重载
                    row = self.getRow(task_info)

                    if row != -1 and self.removeRow(row):
                        self.task_permanently_deleted.emit(1)

                else:
                    logger.error("删除下载任务失败，保留界面行: %s", task_info.Basic.task_id)

                    signal_bus.toast.show_long_message.emit(
                        ToastNotificationCategory.ERROR,
                        self.tr("Failed to delete download task"),
                        self.tr("The database write failed. Please try again.")
                    )

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
                    continue

                case DownloadStatus.COMPLETED:
                    completed_tasks.append(task)

                case _:
                    remaining_tasks.append(task)

        if completed_tasks:
            # wait=True：写完再移除 UI，避免「UI 已删、库里还在，翻页/重启又看到」。
            # 返回 False 说明写入失败，不移除界面行，保持与库一致。
            # 失败时 toast 提示，与单条删除保持一致，避免用户「点了没反应」
            if task_manager.delete_many(completed_tasks, completed=True, wait=True):
                # 用 removeTasks 的实际返回值而不是 len(completed_tasks)：
                # 分页模式下 completed_tasks 可能包含不在当前页的任务，
                # 两者数量可能不同
                removed = self.removeTasks(completed_tasks)

                if removed > 0:
                    self.task_permanently_deleted.emit(removed)

            else:
                logger.error("批量删除已完成任务失败，保留界面行")

                signal_bus.toast.show_long_message.emit(
                    ToastNotificationCategory.ERROR,
                    self.tr("Failed to delete download tasks"),
                    self.tr("The database write failed. Please try again.")
                )

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