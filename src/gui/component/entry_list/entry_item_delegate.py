from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle
from PySide6.QtCore import QModelIndex, Qt, QSize, QRect, QEvent
from PySide6.QtGui import QPainter, QPixmap

from gui.component.download_list.item_delegate import FluentStyledItemDelegate

class EntryListItemDelegate(QStyledItemDelegate, FluentStyledItemDelegate):
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

    def sizeHint(self, option, index):
        return QSize(0, 92)

    def _paintItemUI(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        entry = index.data(Qt.ItemDataRole.UserRole)

        coverRect = self.uiRect.getCoverRect(option)
        self._drawCover(painter, coverRect, index, entry)

        titleRect = self.uiRect.getTitleRect(coverRect, option)
        self._drawText(painter, titleRect, entry["title"])

        countRect = self.uiRect.getCountRect(titleRect, option)
        self._drawDescriptionText(painter, countRect, "共 {count} 项".format(count = entry["count"]))

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

        return QRect(self.margin, top, 128, 72)
    
    def getTitleRect(self, coverRect: QRect, option: QStyleOptionViewItem):
        left = coverRect.right() + self.spacer
        top = coverRect.top() + 2

        width = option.rect.width() - 150

        return QRect(left, top, width, 20)
    
    def getCountRect(self, titleRect: QRect, option: QStyleOptionViewItem):
        left = titleRect.left()
        top = option.rect.bottom() - titleRect.height() - self.margin - 2

        return QRect(left, top, 100, 20)
    