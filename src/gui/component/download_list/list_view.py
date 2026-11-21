from PySide6.QtGui import QPainter, QColor, QFontMetrics
from PySide6.QtCore import QModelIndex, Qt, QTimer
from PySide6.QtWidgets import QProgressDialog

from qfluentwidgets import ListView, RoundMenu, Action, FluentIcon, isDarkTheme, setFont

from .item_delegate import DownloadItemDelegate
from .model import DownloadListModel
from .proxy_model import DownloadListProxyModel

from gui.component.widget.smooth_scroll import applySmoothScroll

from util.download.downloader.manager import downloader_manager
from util.download.task.info import TaskInfo
from util.parse.episode.tree import Attribute

from util.common.enum import DownloadStatus, ToastNotificationCategory
from util.common.icon import ExtendedFluentIcon
from util.common.signal_bus import signal_bus
from util.common.config import config

from typing import List

class DownloadListView(ListView):
    def __init__(self, parent = None):
        super().__init__(parent)

        applySmoothScroll(self)

        self._emptyTextTip = ""
        self._noMatchTextTip = self.tr("No matching tasks")
        self._auto_manage_concurrent = False
        self._auto_update_visible_area = False
        self._auto_update_count_badge = False
        self._auto_manage_pending = False
        self._in_batch_cancel = False

        self._in_adding_queried_tasks = False
        self._metadata_progress = None

        self._source_model = DownloadListModel([], self)
        self._model = DownloadListProxyModel(self)
        self._model.setSourceModel(self._source_model)

        self._delegate = DownloadItemDelegate(self)
        self._delegate.contextMenuRequested.connect(self.showContextMenu)

        self.setModel(self._model)
        self.setItemDelegate(self._delegate)
        self.setSelectionMode(ListView.SelectionMode.SingleSelection)
        self.setSelectRightClickedRow(True)

        self.setUniformItemSizes(True)

    def showContextMenu(self, index, pos):
        menu = RoundMenu(parent = self)

        task_info: TaskInfo = index.data(Qt.ItemDataRole.UserRole)

        match task_info.Download.status:
            case DownloadStatus.COMPLETED:
                menu.addAction(self._create_action(FluentIcon.SEARCH, self.tr("Re-parse"), lambda: self.onReparseTask(task_info)))
                if task_info.Episode.attribute & Attribute.VIDEO_BIT and task_info.Episode.bvid:
                    menu.addAction(self._create_action(FluentIcon.UPDATE, self.tr("Refresh Metadata"), lambda: self.onRefreshMetadata([task_info])))

            case DownloadStatus.QUEUED | DownloadStatus.PAUSED:
                menu.addAction(self._create_action(FluentIcon.PLAY, self.tr("Resume"), lambda: self.onTogglePauseResumeTask(index, task_info)))

            case DownloadStatus.DOWNLOADING:
                menu.addAction(self._create_action(FluentIcon.PAUSE, self.tr("Pause"), lambda: self.onTogglePauseResumeTask(index, task_info)))

        menu.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Re-download"), lambda: self.onRedownloadTask(index, task_info)))

        #menu.addAction(self._create_action(FluentIcon.EDIT, self.tr("Edit download options"), lambda: self.onEditDownloadOptions(index, task_info)))

        menu.addSeparator()

        menu.addAction(self._create_action(FluentIcon.DELETE, self.tr("Delete"), lambda: self.onCancelTask(index, task_info)))

        menu.exec(pos)

    def isEmpty(self):
        return self._model.rowCount() == 0
    
    def setEmptyTextTip(self, text: str):
        self._emptyTextTip = text

    def setAutoManageConcurrentTasks(self, auto_manage: bool):
        self._auto_manage_concurrent = auto_manage

    def setAutoUpdateCountBadge(self, auto_update: bool):
        self._auto_update_count_badge = auto_update

    def enableSorting(self, default_key: str = None, ascending: bool = True):
        self._model.enableSorting(default_key, ascending)

    def connectUpdateDataSignal(self):
        self._model.connectUpdateDataSignal()

    def setFilterText(self, text: str):
        self._model.setFilterText(text)

    def setStatusFilter(self, statuses):
        self._model.setStatusFilter(statuses)

    def setMediaTypeFilter(self, media_types):
        self._model.setMediaTypeFilter(media_types)

    def isFiltering(self):
        return self._model.isFiltering()

    def paintEvent(self, e):
        if self.isEmpty():
            if isDarkTheme():
                textColor = QColor(255, 255, 255)
            else:
                textColor = QColor(0, 0, 0)

            painter = QPainter(self.viewport())
            painter.setPen(textColor)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            setFont(painter, 14)

            # 列表里其实有任务、只是全被筛掉时不能照旧显示「没有任务」，否则像是任务丢了
            text = self._noMatchTextTip if self._source_model.rowCount() else self._emptyTextTip

            fm = QFontMetrics(self.font())
            text_width = fm.horizontalAdvance(text)
            text_height = fm.height()

            x = (self.viewport().width() - text_width) // 2
            y = (self.viewport().height() + text_height) // 2

            painter.drawText(x, y, text)

        else:
            return super().paintEvent(e)

    def addTask(self, task_info_list: List[TaskInfo]):
        self._model.appendRows(task_info_list)

        if self._auto_update_count_badge:
            # 更新下载数量徽章
            signal_bus.download.update_downloading_count.emit(self._source_model.rowCount())
    
    def removeTask(self, task_info: TaskInfo):
        self._model.removeTask(task_info)

        downloader_manager.remove(task_info.Basic.task_id)

        if self._auto_manage_concurrent and not self._in_batch_cancel:
            self._model.manageConcurrentDownloads()

        if self._auto_update_count_badge:
            # 更新下载数量徽章
            count = self._source_model.rowCount()

            signal_bus.download.update_downloading_count.emit(count)

            if count == 0 and config.get(config.show_notification):
                # 如果没有正在下载的任务了，发射下载完成的通知信号
                downloader_manager.show_notification()

    def _beginAddQueriedTasks(self):
        self._in_adding_queried_tasks = True

    def _endAddQueriedTasks(self):
        self._in_adding_queried_tasks = False

    def batch_cancel(self):
        self._in_batch_cancel = True

        try:
            self._model.batch_cancel()
        finally:
            self._in_batch_cancel = False

        if self._auto_manage_concurrent:
            self._schedule_auto_manage_concurrent_downloads()

    def _schedule_auto_manage_concurrent_downloads(self):
        if self._auto_manage_pending:
            return

        self._auto_manage_pending = True

        def run_auto_manage():
            self._auto_manage_pending = False
            self._model.manageConcurrentDownloads()

        # self 作为 context：闭包没有可识别的接收者，控件先一步销毁时
        # 不带 context 的回调仍会执行，然后打在已经析构的 model 上
        QTimer.singleShot(0, self, run_auto_manage)

    def onTogglePauseResumeTask(self, index: QModelIndex, task_info: TaskInfo):
        # 与 model 交互以暂停下载任务
        index.model().togglePauseResume(task_info)

    def onCancelTask(self, index: QModelIndex, task_info: TaskInfo):
        # 与 model 交互以取消下载任务
        index.model().cancelDownload(task_info)

    def onRedownloadTask(self, index: QModelIndex, task_info: TaskInfo):
        # 与 model 交互以重新下载任务
        if task_info.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
            # 合并和转换过程中的任务不允许直接重新下载
            signal_bus.toast.show.emit(ToastNotificationCategory.WARNING, "", self.tr("Tasks being processed by FFmpeg cannot be redownloaded"))

            return
        
        signal_bus.toast.show.emit(ToastNotificationCategory.INFO, "", self.tr("Selected task will be redownloaded"))

        index.model().redownload(task_info)

    def onReparseTask(self, task_info: TaskInfo):
        signal_bus.parse.parse_url.emit(task_info.Episode.url)

    def refreshVisibleMetadata(self):
        self.onRefreshMetadata(self._model.visibleTasks())

    def onRefreshMetadata(self, tasks: list[TaskInfo]):
        from gui.dialog.misc.refresh_metadata import RefreshMetadataDialog
        from util.parse.additional.metadata_refresh import MetadataRefreshWorker, can_refresh_metadata
        from util.thread.async_ import AsyncTask

        if self._metadata_progress is not None:
            self._metadata_progress.show()
            return

        tasks = [task for task in tasks if can_refresh_metadata(task)]
        if not tasks:
            signal_bus.toast.show.emit(ToastNotificationCategory.INFO, "", self.tr("No completed videos to refresh"))
            return

        dialog = RefreshMetadataDialog(len(tasks), self.window())
        if not dialog.exec():
            return

        worker = MetadataRefreshWorker(tasks, *dialog.options)
        progress = QProgressDialog(self.tr("Refreshing video metadata…"), self.tr("Stop after current video"), 0, len(tasks), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.canceled.connect(lambda: worker.cancel())
        worker.progress.connect(progress.setValue)
        worker.result.connect(self.onMetadataRefreshResult)

        self._metadata_progress = progress
        progress.show()
        AsyncTask.run(worker)

    def onMetadataRefreshResult(self, succeeded: int, failed: int, error: str):
        progress = self._metadata_progress
        pending = progress.maximum() - succeeded - failed
        progress.hide()
        progress.deleteLater()
        self._metadata_progress = None

        message = self.tr("Updated: {succeeded} · Failed: {failed} · Unprocessed: {pending}").format(
            succeeded = succeeded, failed = failed, pending = pending
        )
        if error:
            message = f"{message}\n{error}"
        category = ToastNotificationCategory.WARNING if failed or pending else ToastNotificationCategory.SUCCESS
        signal_bus.toast.show_long_message.emit(category, self.tr("Metadata Refresh"), message)

    def onEditDownloadOptions(self, index: QModelIndex, task_info: TaskInfo):
        pass

    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)
        
        return action
    
    @property
    def sort_by_key(self):
        return self._model._sort_by_key

    @property
    def sort_ascending(self):
        return self._model._ascending

    @property
    def status_filter(self):
        return self._model.status_filter

    @property
    def media_type_filter(self):
        return self._model.media_type_filter
