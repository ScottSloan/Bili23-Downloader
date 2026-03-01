from PySide6.QtGui import QPainter, QColor, QFontMetrics

from qfluentwidgets import ListView, RoundMenu, Action, FluentIcon

from gui.component.download.item_delegate import DownloadItemDelegate
from gui.component.download.model import DownloadListModel

from util.download.task.info import TaskInfo

from typing import List

class DownloadListView(ListView):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._emptyTextTip = ""
        self._auto_manage_concurrent = False

        self._model = DownloadListModel([], self)
        delegate = DownloadItemDelegate(self)
        delegate.contextMenuRequested.connect(self.showContextMenu)

        self.setModel(self._model)
        self.setItemDelegate(delegate)
        self.setSelectionMode(ListView.SelectionMode.SingleSelection)
        self.setSelectRightClickedRow(True)

        self.setUniformItemSizes(True)

    def showContextMenu(self, index, pos):
        menu = RoundMenu(parent = self)

        menu.addAction(Action(FluentIcon.PLAY, "继续", parent = self))
        menu.addAction(Action(FluentIcon.DELETE, "删除", parent = self))

        menu.exec(pos)

    def isEmpty(self):
        return len(self._model._task_list) == 0
    
    def setEmptyTextTip(self, text: str):
        self._emptyTextTip = text

    def setAutoManageConcurrent(self, auto_manage: bool):
        self._auto_manage_concurrent = auto_manage

    def paintEvent(self, e):
        if self.isEmpty():
            painter = QPainter(self.viewport())
            painter.setPen(QColor(255, 255, 255))
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            fm = QFontMetrics(self.font())
            text_width = fm.horizontalAdvance(self._emptyTextTip)
            text_height = fm.height()

            x = (self.viewport().width() - text_width) // 2
            y = (self.viewport().height() + text_height) // 2

            painter.drawText(x, y, self._emptyTextTip)

        else:
            return super().paintEvent(e)

    def add_task(self, task_info_list: List[TaskInfo]):
        self._model.appendRows(task_info_list)

        if self._auto_manage_concurrent:
            # self._model.manage_concurrent_downloads()
            pass
