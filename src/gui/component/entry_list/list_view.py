from PySide6.QtCore import QSize, Qt, Signal

from qfluentwidgets import ListView, RoundMenu, Action, FluentIcon

from .poster_item_delegate import PosterListItemDelegate
from .entry_item_delegate import EntryListItemDelegate
from ..view_model import ContextMenuListViewBase
from .model import EntryListModel

import webbrowser

class EntryListView(ContextMenuListViewBase):
    parse = Signal(object, object)

    def __init__(self, is_poster: bool, parent = None):
        super().__init__(parent)

        self._emptyTextTip = self.tr("No entries")

        self._model = EntryListModel([], self)
        self._delegate = PosterListItemDelegate(self) if is_poster else EntryListItemDelegate(self)
        self._delegate.contextMenuRequested.connect(self.showContextMenu)

        self.setModel(self._model)
        self.setItemDelegate(self._delegate)
        self.setSelectionMode(ListView.SelectionMode.SingleSelection)
        self.setSelectRightClickedRow(True)

        self.setUniformItemSizes(True)

    def add_entry_list(self, entry_list: list):
        for entry in entry_list:
            self._model.appendRow(entry)

    def updateGeometries(self):
        super().updateGeometries()
        
        # QListView 开启按像素滚动且 UniformItemSizes 时
        # 会自动计算高度导致单次滚动跨度过大 (一滚就是一整个 Poster 的高度)
        # 这里重写使得像素滚动能保持在一个较小、更顺滑的距离
        self.verticalScrollBar().setSingleStep(35)

    def set_cover_size(self, size: QSize):
        self._model._cover_size = size
        
    def setWrappingView(self):
        # 启用多行显示，实现流式布局
        self.setWrapping(True)
        self.setFlow(ListView.Flow.LeftToRight)
        self.setResizeMode(ListView.ResizeMode.Adjust)

    def showContextMenu(self, index, pos):
        menu = RoundMenu(parent = self)

        entry = index.data(Qt.ItemDataRole.UserRole)

        menu.addAction(self._create_action(FluentIcon.SEARCH, self.tr("Parse"), lambda: self.onParse(entry)))
        menu.addAction(self._create_action(FluentIcon.GLOBE, self.tr("Open in Browser"), lambda: self.onOpenInBrowser(entry)))

        menu.exec(pos)

    def onParse(self, entry: dict):
        self.parse.emit(self.currentIndex(), entry)

    def onOpenInBrowser(self, entry: dict):
        url = entry.get("url")

        webbrowser.open(url)

