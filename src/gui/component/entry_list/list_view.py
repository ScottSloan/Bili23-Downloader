from PySide6.QtGui import QPainter, QColor, QFontMetrics
from PySide6.QtCore import QSize

from qfluentwidgets import ListView, isDarkTheme, setFont

from gui.component.entry_list.poster_item_delegate import PosterListItemDelegate
from gui.component.entry_list.entry_item_delegate import EntryListItemDelegate
from gui.component.entry_list.model import EntryListModel

class EntryListView(ListView):
    def __init__(self, is_poster: bool, parent = None):
        super().__init__(parent)

        self._emptyTextTip = self.tr("No entries")

        self._model = EntryListModel([], self)
        self._delegate = PosterListItemDelegate(self) if is_poster else EntryListItemDelegate(self)

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

    def isEmpty(self):
        return self._model.rowCount() == 0

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
