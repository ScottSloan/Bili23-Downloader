from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from qfluentwidgets import ListView, RoundMenu, FluentIcon

from ..dialog import MessageBox
from ..view_model import ContextMenuListViewBase
from .item_delegate import LogListItemDelegate
from .proxy_model import LogListProxyModel
from .model import LogListModel

class LogListView(ContextMenuListViewBase):
    def __init__(self, parent_window, parent = None):
        super().__init__(parent)

        self.parent_window = parent_window

        self._emptyTextTip = self.tr("No logs")

        self._source_model = LogListModel([], self)
        self._model = LogListProxyModel(self)
        self._model.setSourceModel(self._source_model)

        self._delegate = LogListItemDelegate(self)
        self._delegate.itemClicked.connect(lambda index, record: self.onViewDetails(record))
        self._delegate.contextMenuRequested.connect(self.showContextMenu)

        self.setModel(self._model)
        self.setItemDelegate(self._delegate)
        self.setSelectionMode(ListView.SelectionMode.SingleSelection)
        self.setSelectRightClickedRow(True)

        self.setUniformItemSizes(True)

    def updateGeometries(self):
        super().updateGeometries()

        self.verticalScrollBar().setSingleStep(30)

    def setLevelFilter(self, level: str):
        self._model.setLevelFilter(level)

    def setFilterText(self, text: str):
        self._model.setFilterText(text)

    def showContextMenu(self, index, pos):
        menu = RoundMenu(parent = self)

        record = index.data(Qt.ItemDataRole.UserRole)

        menu.addAction(self._create_action(FluentIcon.VIEW, self.tr("View Details"), lambda: self.onViewDetails(record)))
        menu.addAction(self._create_action(FluentIcon.COPY, self.tr("Copy"), lambda: self.onCopy(record)))

        menu.exec(pos)
    
    def onCopy(self, record: dict):
        # 复制日志内容到剪贴板
        content = "[{timestamp}] - {name} - {level} - {callsite}: {message}".format(
            **record
        )
        
        clipboard = QApplication.clipboard()
        clipboard.setText(content)

    def onViewDetails(self, record: dict):
        content = self.tr("Timestamp: {timestamp}\nLevel: {level}\nName: {name} ({callsite})\n\nMessage: \n{message}").format(
            **record
        )

        dialog = MessageBox(
            title = self.tr("Log Details"),
            content = content,
            parent = self.parent_window
        )
        dialog.hideCancelButton()

        dialog.exec()