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
    # 下载中列表不关心这个信号；已完成列表在分页模式下用它更新总数
    taskRemoved = Signal(int)

    # 数据库已落盘的真正删除。redownload（移到下载中）也会走 removeRow，
    # 但那条路径下库里记录还在，此刻重载会让刚移除的行又出现。这个信号只由
    # cancelDownload / batch_cancel 的 COMPLETED 分支在 wait=True 落盘后发射
    taskPermanentlyDeleted = Signal(int)

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

        # 分页模式的显式标记。用单独的布尔而不是 _pagination_sort_key is not None 判断：
        # 排序键理论上可能为 None，用布尔可以排除这条歧义路径
        self._pagination_mode = False
        self._pagination_sort_key = None
        self._pagination_sort_ascending = True

        # 分页模式下空列表时靠这个标志决定显示「无匹配」还是「无任务」。
        # 非分页模式走 proxy 的 isFiltering()
        self._is_filtering = False

        self._source_model = DownloadListModel([], self)
        # 所有删除路径最终都落到 source model 的 removeRow / removeTasks
        self._source_model.row_removed.connect(self._on_source_row_removed)
        # 真正落盘的删除单独转发，供分页模式重载补位
        self._source_model.task_permanently_deleted.connect(self.taskPermanentlyDeleted.emit)

        self._model = DownloadListProxyModel(self)
        self._model.setSourceModel(self._source_model)

        self._delegate = DownloadItemDelegate(self)
        self._delegate.contextMenuRequested.connect(self.showContextMenu)

        self.setModel(self._model)
        self.setItemDelegate(self._delegate)
        self.setSelectionMode(ListView.SelectionMode.SingleSelection)
        self.setSelectRightClickedRow(True)

        self.setUniformItemSizes(True)

    def _on_source_row_removed(self, count: int):
        self.taskRemoved.emit(count)

    def setPaginationSortState(self, key: str, ascending: bool):
        # 分页模式下由 DownloadInterface 在排序变化 / 启动时注入
        self._pagination_mode = True
        self._pagination_sort_key = key
        self._pagination_sort_ascending = bool(ascending)

    def setFiltering(self, filtering: bool):
        # 分页模式下 search / 媒体筛选无结果时列表也为空，靠这个标志决定显示
        # 「无匹配」还是「无任务」。非分页模式走 proxy 的 isFiltering()
        if self._is_filtering != filtering:
            self._is_filtering = filtering
            self.viewport().update()

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
        # 分页模式下关键词与媒体筛选都下推到 SQLite，存在 DownloadInterface，
        # 未设置到 proxy；这里把 setFiltering 注入的 _is_filtering 也纳入判断，
        # 避免「有筛选但 isFiltering 返回 False」让 _clear_all_completed 误判
        return self._is_filtering or self._model.isFiltering()

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

            # 分页模式下 rowCount 只是当前页行数，靠 setFiltering 注入的标志判断；
            # 非分页模式（下载中列表）直接用 proxy 的 isFiltering()。
            # 分页模式下关键词和媒体筛选都下推到 SQLite，proxy 的 isFiltering()
            # 恒为 False，必须把 _is_filtering 也纳入
            if self._pagination_mode:
                is_filtering = self._is_filtering or self._model.isFiltering()
            else:
                is_filtering = self._model.isFiltering()

            text = self._noMatchTextTip if is_filtering else self._emptyTextTip

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
            signal_bus.download.update_downloading_count.emit(self._source_model.rowCount())

    def removeTask(self, task_info: TaskInfo):
        self._model.removeTask(task_info)

        downloader_manager.remove(task_info.Basic.task_id)

        if self._auto_manage_concurrent and not self._in_batch_cancel:
            self._model.manageConcurrentDownloads()

        if self._auto_update_count_badge:
            count = self._source_model.rowCount()

            signal_bus.download.update_downloading_count.emit(count)

            if count == 0 and config.get(config.show_notification):
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

        QTimer.singleShot(0, self, run_auto_manage)

    def onTogglePauseResumeTask(self, index: QModelIndex, task_info: TaskInfo):
        index.model().togglePauseResume(task_info)

    def onCancelTask(self, index: QModelIndex, task_info: TaskInfo):
        index.model().cancelDownload(task_info)

    def onRedownloadTask(self, index: QModelIndex, task_info: TaskInfo):
        if task_info.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
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
        if self._pagination_mode:
            return self._pagination_sort_key

        return self._model._sort_by_key

    @property
    def sort_ascending(self):
        if self._pagination_mode:
            return self._pagination_sort_ascending

        return self._model._ascending

    @property
    def status_filter(self):
        return self._model.status_filter

    @property
    def media_type_filter(self):
        return self._model.media_type_filter