from PySide6.QtGui import QPainter, QColor, QFontMetrics
from PySide6.QtCore import QModelIndex, Qt, QTimer, Signal

from qfluentwidgets import ListView, RoundMenu, Action, FluentIcon, isDarkTheme, setFont

from .item_delegate import DownloadItemDelegate
from .model import DownloadListModel
from .proxy_model import DownloadListProxyModel

from gui.component.widget.smooth_scroll import applySmoothScroll

from util.download.downloader.manager import downloader_manager
from util.download.task.info import TaskInfo

from util.common.enum import DownloadStatus, ToastNotificationCategory
from util.common.icon import ExtendedFluentIcon
from util.common.signal_bus import signal_bus
from util.common.config import config

from typing import List


class DownloadListView(ListView):
    # 任务被移除时发射，参数为本次移除的数量。
    # 下载中列表不关心这个信号；已完成列表在分页模式下用它更新总数并重载当前页
    taskRemoved = Signal(int)

    def __init__(self, parent=None):
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

        # 分页模式下 proxy 不参与排序（_sorting 为 False，_sort_by_key 为 None），
        # 排序状态由外部（DownloadInterface）注入，供顶栏排序浮窗读取当前值。
        # 非分页模式保持 None，属性回落到 proxy 的真实状态
        self._pagination_sort_key = None
        self._pagination_sort_ascending = True

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

    def setPaginationSortState(self, key: str, ascending: bool):
        # 分页模式下由 DownloadInterface 在排序变化 / 启动时注入，
        # 使 sort_by_key / sort_ascending 能报告真实排序状态
        self._pagination_sort_key = key
        self._pagination_sort_ascending = bool(ascending)

    def showContextMenu(self, index, pos):
        menu = RoundMenu(parent=self)

        task_info: TaskInfo = index.data(Qt.ItemDataRole.UserRole)

        match task_info.Download.status:
            case DownloadStatus.COMPLETED:
                menu.addAction(
                    self._create_action(FluentIcon.SEARCH, self.tr("Re-parse"), lambda: self.onReparseTask(task_info)))

            case DownloadStatus.QUEUED | DownloadStatus.PAUSED:
                menu.addAction(self._create_action(FluentIcon.PLAY, self.tr("Resume"),
                                                   lambda: self.onTogglePauseResumeTask(index, task_info)))

            case DownloadStatus.DOWNLOADING:
                menu.addAction(self._create_action(FluentIcon.PAUSE, self.tr("Pause"),
                                                   lambda: self.onTogglePauseResumeTask(index, task_info)))

        menu.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Re-download"),
                                           lambda: self.onRedownloadTask(index, task_info)))

        # menu.addAction(self._create_action(FluentIcon.EDIT, self.tr("Edit download options"), lambda: self.onEditDownloadOptions(index, task_info)))

        menu.addSeparator()

        menu.addAction(
            self._create_action(FluentIcon.DELETE, self.tr("Delete"), lambda: self.onCancelTask(index, task_info)))

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
        removed = self._model.removeTask(task_info)

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

        # 只有真的移除了才通知，避免重复删除时把总数减错
        if removed:
            self.taskRemoved.emit(1)

    def _beginAddQueriedTasks(self):
        self._in_adding_queried_tasks = True

    def _endAddQueriedTasks(self):
        self._in_adding_queried_tasks = False

    def batch_cancel(self):
        before = self._source_model.rowCount()

        self._in_batch_cancel = True

        try:
            self._model.batch_cancel()
        finally:
            self._in_batch_cancel = False

        removed = before - self._source_model.rowCount()

        if removed > 0:
            self.taskRemoved.emit(removed)

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
            signal_bus.toast.show.emit(ToastNotificationCategory.WARNING, "",
                                       self.tr("Tasks being processed by FFmpeg cannot be redownloaded"))

            return

        signal_bus.toast.show.emit(ToastNotificationCategory.INFO, "", self.tr("Selected task will be redownloaded"))

        index.model().redownload(task_info)

    def onReparseTask(self, task_info: TaskInfo):
        signal_bus.parse.parse_url.emit(task_info.Episode.url)

    def onEditDownloadOptions(self, index: QModelIndex, task_info: TaskInfo):
        pass

    def _create_action(self, icon, text, slot):
        action = Action(icon=icon, text=text, parent=self)
        action.triggered.connect(slot)

        return action

    @property
    def sort_by_key(self):
        # 分页模式下 proxy 的 _sort_by_key 恒为 None，
        # 必须返回外部注入的值，顶栏排序浮窗才能选中真实项
        if self._pagination_sort_key is not None:
            return self._pagination_sort_key

        return self._model._sort_by_key

    @property
    def sort_ascending(self):
        if self._pagination_sort_key is not None:
            return self._pagination_sort_ascending

        return self._model._ascending

    @property
    def status_filter(self):
        return self._model.status_filter

    @property
    def media_type_filter(self):
        return self._model.media_type_filter