from PySide6.QtCore import QModelIndex, Qt, QSize, QRect, QEvent
from PySide6.QtWidgets import QStyleOptionViewItem
from PySide6.QtGui import QPainter, QPixmap

from gui.component.view_model import CoverQueryDelegateBase

class EntryListItemDelegate(CoverQueryDelegateBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.uiRect = UIRect()

        self._placeholderPixmap = QPixmap(":/bili23/image/placeholder.png")

    def sizeHint(self, option, index):
        return QSize(295, 92)

    def _paintItemUI(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        entry: dict = index.data(Qt.ItemDataRole.UserRole)

        coverRect = self.uiRect.getCoverRect(option)
        self._drawCover(painter, coverRect, option, index, entry.get("cover_id"), entry.get("cover"))

        titleRect = self.uiRect.getTitleRect(coverRect, option)
        self._drawText(painter, titleRect, entry["title"])

        countRect = self.uiRect.getCountRect(titleRect, option)
        self._drawDescriptionText(painter, countRect, self.tr("{count} items").format(count = entry["count"]))

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            return self._pressEvent(option, index, event)

        return super().editorEvent(event, model, option, index)
    
    def _pressEvent(self, option: QStyleOptionViewItem, index: QModelIndex, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index.model().itemClicked.emit(index, index.data(Qt.ItemDataRole.UserRole))

            return True
        
        if event.button() == Qt.MouseButton.RightButton:
            # 右键点击，弹出上下文菜单
            self.contextMenuRequested.emit(index, event.globalPos())

            return True

        return False

class UIRect:
    def __init__(self):
        self.margin = 10
        self.spacer = 20

    def getCoverRect(self, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()
        left = self.margin + option.rect.left()

        return QRect(left, top, 128, 72)
    
    def getTitleRect(self, coverRect: QRect, option: QStyleOptionViewItem):
        left = coverRect.right() + self.spacer
        top = coverRect.top() + 2

        width = option.rect.width() - 150

        return QRect(left, top, width, 20)
    
    def getCountRect(self, titleRect: QRect, option: QStyleOptionViewItem):
        left = titleRect.left()
        top = option.rect.bottom() - titleRect.height() - self.margin - 2

        return QRect(left, top, 100, 20)
    