from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle
from PySide6.QtCore import QModelIndex, Qt, QSize, QRect, QEvent
from PySide6.QtGui import QPainter, QPixmap

from gui.component.download_list.item_delegate import FluentStyledItemDelegate

class PosterListItemDelegate(QStyledItemDelegate, FluentStyledItemDelegate):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.uiRect = UIRect()

        self._placeholderPixmap = QPixmap(":/bili23/image/placeholder.png")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        painter.setClipping(True)
        painter.setClipRect(option.rect)

        self._checkHoverRow(option, index)

        self._drawBackground(painter, option, index)

        self._paintItemUI(painter, option, index)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        return QSize(0, 184)

    def _paintItemUI(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        entry = index.data(Qt.ItemDataRole.UserRole)

        coverRect = self.uiRect.getCoverRect(option)
        self._drawCover(painter, coverRect, index, entry)

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

    def _checkHoverRow(self, option: QStyleOptionViewItem, index: QModelIndex):
        if option.state & QStyle.StateFlag.State_MouseOver:
            self.hoverRow = index.row()

        elif self.hoverRow == index.row():
            self.hoverRow = -1

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            return self._pressEvent(option, index, event)

        return super().editorEvent(event, model, option, index)
    
    def _pressEvent(self, option: QStyleOptionViewItem, index: QModelIndex, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index.model().itemClicked.emit(index, index.data(Qt.ItemDataRole.UserRole))

            return True

        return False

    def _queryCover(self, cover_id: str, cover_url: str, index: QModelIndex):
        # 由委托发起查询封面请求
        return index.model().queryRowCover(cover_id, cover_url, index.row())

    def _drawCover(self, painter, rect, index, entry):
        # 先绘制占位图
        self._drawPlaceholderPixmap(painter, rect, self._placeholderPixmap)

        if cover_id := entry.get("cover_id"):
            self._drawPixmap(painter, rect, self._queryCover(cover_id, entry["cover"], index))

class UIRect:
    def __init__(self):
        self.margin = 10
        self.spacer = 20

    def getCoverRect(self, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()

        return QRect(self.margin, top, 123, 164)

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
    