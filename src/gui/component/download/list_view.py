from PySide6.QtGui import QPainter, QColor, QFontMetrics
from PySide6.QtCore import QTimer

from qfluentwidgets import ListView, RoundMenu, Action, FluentIcon, isDarkTheme

from gui.component.download.item_delegate import DownloadItemDelegate
from gui.component.download.model import DownloadListModel

from util.download.downloader.manager import downloader_manager
from util.common.signal_bus import signal_bus
from util.download.task.info import TaskInfo

from typing import List

class DownloadListView(ListView):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._emptyTextTip = ""
        self._auto_manage_concurrent = False
        self._auto_update_visible_area = False
        self._auto_update_count_badge = False

        self._model = DownloadListModel([], self)
        delegate = DownloadItemDelegate(self)
        delegate.contextMenuRequested.connect(self.showContextMenu)

        self.setModel(self._model)
        self.setItemDelegate(delegate)
        self.setSelectionMode(ListView.SelectionMode.SingleSelection)
        self.setSelectRightClickedRow(True)

        self.setUniformItemSizes(True)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.updateVisibleArea)

    def showContextMenu(self, index, pos):
        menu = RoundMenu(parent = self)

        menu.addAction(Action(FluentIcon.PLAY, "继续", parent = self))
        menu.addAction(Action(FluentIcon.DELETE, "删除", parent = self))

        menu.exec(pos)

    def isEmpty(self):
        return len(self._model._task_list) == 0
    
    def setEmptyTextTip(self, text: str):
        self._emptyTextTip = text

    def setAutoManageConcurrentTasks(self, auto_manage: bool):
        self._auto_manage_concurrent = auto_manage

    def setAutoUpdateVisibleArea(self, auto_update: bool):
        self._auto_update_visible_area = auto_update

        # 根据设置启动或停止定时器
        if auto_update:
            self.update_timer.start(1000)
        else:
            self.update_timer.stop()

    def setAutoUpdateCountBadge(self, auto_update: bool):
        self._auto_update_count_badge = auto_update

    def connectUpdateDataSignal(self):
        self._model.connectUpdateDataSignal()

    def updateVisibleArea(self):
        # 只更新可见区域的下载项的信息
        rect = self.viewport().rect()
        top_index = self.indexAt(rect.topLeft())
        bottom_index = self.indexAt(rect.bottomLeft())

        if top_index.isValid() and bottom_index.isValid():
            self._model.updateRows(top_index.row(), bottom_index.row())

        elif top_index.isValid():
            self._model.updateRows(top_index.row(), top_index.row())

        elif bottom_index.isValid():
            self._model.updateRows(bottom_index.row(), bottom_index.row())

    def paintEvent(self, e):
        if self.isEmpty():
            if isDarkTheme():
                textColor = QColor(255, 255, 255)
            else:
                textColor = QColor(0, 0, 0)

            painter = QPainter(self.viewport())
            painter.setPen(textColor)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

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

        if self._auto_manage_concurrent:
            downloader_manager.add_downloader_list(task_info_list)

            self._model.manageConcurrentDownloads()

        if self._auto_update_count_badge:
            # 更新下载数量徽章
            signal_bus.download.update_downloading_count.emit(self._model.rowCount())
    
    def removeTask(self, task_info: TaskInfo):
        row = self._model.getRow(task_info)
        
        self._model.removeRow(row)

        if self._auto_manage_concurrent:
            downloader_manager.remove_downloader(task_info.Basic.task_id)

            self._model.manageConcurrentDownloads()

        if self._auto_update_count_badge:
            # 更新下载数量徽章
            signal_bus.download.update_downloading_count.emit(self._model.rowCount())
    