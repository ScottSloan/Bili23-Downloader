from PySide6.QtCore import QModelIndex, Qt, QSize, QRect, QEvent
from PySide6.QtWidgets import QStyleOptionViewItem
from PySide6.QtGui import QPainter, QPixmap

from gui.component.view_model import CoverQueryDelegateBase

class PosterListItemDelegate(CoverQueryDelegateBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.uiRect = UIRect()

        self._placeholderPixmap = QPixmap(":/bili23/image/placeholder.png")

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        return QSize(295, 184)

    def _paintItemUI(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        entry: dict = index.data(Qt.ItemDataRole.UserRole)

        coverRect = self.uiRect.getCoverRect(option)
        self._drawCover(painter, coverRect, option, index, entry.get("cover_id"), entry.get("cover"))

        titleRect = self.uiRect.getTitleRect(coverRect, option)
        self._drawText(painter, titleRect, entry["title"])

        typeRect = self.uiRect.getTypeRect(titleRect, option)
        self._drawDescriptionText(painter, typeRect, entry["type"])

        newEPRect = self.uiRect.getNewEPRect(typeRect, option)
        self._drawDescriptionText(painter, newEPRect, entry["new_ep"])

        progressRect = self.uiRect.getProgressRect(newEPRect, option)
        self._drawDescriptionText(painter, progressRect, entry["progress"])

        descRect = self.uiRect.getDescRect(titleRect, option)
        self._drawDescriptionText(painter, descRect, entry["desc"])

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            return self._pressEvent(option, index, event)
        
        if event.button() == Qt.MouseButton.RightButton:
            # 右键点击，弹出上下文菜单
            self.contextMenuRequested.emit(index, event.globalPos())

            return True

        return super().editorEvent(event, model, option, index)
    
    def _pressEvent(self, option: QStyleOptionViewItem, index: QModelIndex, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index.model().itemClicked.emit(index, index.data(Qt.ItemDataRole.UserRole))

            return True

        return False

class UIRect:
    def __init__(self):
        self.margin = 10
        self.spacer = 20

    def getCoverRect(self, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()
        left = self.margin + option.rect.left()

        return QRect(left, top, 123, 164)

    def getTitleRect(self, coverRect: QRect, option: QStyleOptionViewItem):
        left = coverRect.right() + self.spacer
        top = coverRect.top() + 2

        width = option.rect.width() - 160

        return QRect(left, top, width, 20)
    
    def getTypeRect(self, titleRect: QRect, option: QStyleOptionViewItem):
        top = titleRect.bottom() + 70

        return QRect(titleRect.left(), top, titleRect.width(), 20)
    
    def getNewEPRect(self, typeRect: QRect, option: QStyleOptionViewItem):
        top = typeRect.bottom() + 5

        return QRect(typeRect.left(), top, typeRect.width(), 20)
    
    def getProgressRect(self, newEPRect: QRect, option: QStyleOptionViewItem):
        top = newEPRect.bottom() + 5

        return QRect(newEPRect.left(), top, newEPRect.width(), 20)
    
    def getDescRect(self, titleRect: QRect, option: QStyleOptionViewItem):
        top = titleRect.bottom() + 10

        return QRect(titleRect.left(), top, titleRect.width(), 40)
    