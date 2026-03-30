from PySide6.QtGui import QPainter, QColor, QFontMetrics
from PySide6.QtCore import QModelIndex, Qt

from qfluentwidgets import ListView, RoundMenu, Action, FluentIcon, isDarkTheme, setFont

from gui.component.download.item_delegate import DownloadItemDelegate
from gui.component.download.model import DownloadListModel

from util.common.enum import DownloadStatus, ToastNotificationCategory
from util.download.downloader.manager import downloader_manager
from util.common import signal_bus, ExtendedFluentIcon, config
from util.download.task.info import TaskInfo

from typing import List

class DownloadListView(ListView):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._emptyTextTip = ""
        self._auto_manage_concurrent = False
        self._auto_update_visible_area = False
        self._auto_update_count_badge = False

        self._in_adding_queried_tasks = False

        self._model = DownloadListModel([], self)
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

        if task_info.Download.status in [DownloadStatus.QUEUED, DownloadStatus.PAUSED]:
            resume_action = Action(FluentIcon.PLAY, self.tr("Resume"), parent = self)
            resume_action.triggered.connect(lambda: self.onTogglePauseResumeTask(index, task_info))
            menu.addAction(resume_action)

        if task_info.Download.status in [DownloadStatus.DOWNLOADING]:
            pause_action = Action(FluentIcon.PAUSE, self.tr("Pause"), parent = self)
            pause_action.triggered.connect(lambda: self.onTogglePauseResumeTask(index, task_info))
            menu.addAction(pause_action)

        delete_action = Action(FluentIcon.DELETE, self.tr("Delete"), parent = self)
        delete_action.triggered.connect(lambda: self.onCancelTask(index, task_info))

        restart_action = Action(ExtendedFluentIcon.RETRY, self.tr("Redownload"), parent = self)
        restart_action.triggered.connect(lambda: self.onRedownloadTask(index, task_info))

        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(restart_action)

        menu.exec(pos)

    def isEmpty(self):
        return len(self._model._task_list) == 0
    
    def setEmptyTextTip(self, text: str):
        self._emptyTextTip = text

    def setAutoManageConcurrentTasks(self, auto_manage: bool):
        self._auto_manage_concurrent = auto_manage

    def setAutoUpdateCountBadge(self, auto_update: bool):
        self._auto_update_count_badge = auto_update

    def connectUpdateDataSignal(self):
        self._model.connectUpdateDataSignal()

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

            fm = QFontMetrics(self.font())
            text_width = fm.horizontalAdvance(self._emptyTextTip)
            text_height = fm.height()

            x = (self.viewport().width() - text_width) // 2
            y = (self.viewport().height() + text_height) // 2

            painter.drawText(x, y, self._emptyTextTip)

        else:
            return super().paintEvent(e)

    def addTask(self, task_info_list: List[TaskInfo]):
        self._model.appendRows(task_info_list)

        if not self._in_adding_queried_tasks:
            self._model.manageConcurrentDownloads()

        if self._auto_update_count_badge:
            # 更新下载数量徽章
            signal_bus.download.update_downloading_count.emit(self._model.rowCount())
    
    def removeTask(self, task_info: TaskInfo):
        row = self._model.getRow(task_info)
        
        self._model.removeRow(row)

        if self._auto_manage_concurrent:
            downloader_manager.remove(task_info.Basic.task_id)

            self._model.manageConcurrentDownloads()

        if self._auto_update_count_badge:
            # 更新下载数量徽章
            count = self._model.rowCount()

            signal_bus.download.update_downloading_count.emit(count)

            if count == 0 and config.get(config.show_notification):
                # 如果没有正在下载的任务了，发射下载完成的通知信号
                downloader_manager.show_notification()

    def _beginAddQueriedTasks(self):
        self._in_adding_queried_tasks = True

    def _endAddQueriedTasks(self):
        self._in_adding_queried_tasks = False

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
    