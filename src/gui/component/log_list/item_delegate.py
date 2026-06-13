from PySide6.QtCore import QModelIndex, Qt, QRect, QSize
from PySide6.QtWidgets import QStyleOptionViewItem
from PySide6.QtGui import QPainter, QColor

from qfluentwidgets import isDarkTheme

from ..view_model import ContextMenuDelegateBase

class LogListItemDelegate(ContextMenuDelegateBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.uiRect = UIRect()

    def sizeHint(self, option, index):
        return QSize(400, 100)
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        painter.setClipping(True)
        painter.setClipRect(option.rect)

        self._checkHoverRow(option, index)

        background_rect = option.rect.adjusted(0, 0, 0, -10)  # 调整背景矩形，留出底部空间，产生分割效果

        self._drawBackground(painter, background_rect, index)
        self._drawPressedBackground(painter, background_rect, index)

        self._paintItemUI(painter, option, index)

        painter.restore()

    def _paintItemUI(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        record: dict = index.data(Qt.ItemDataRole.UserRole)

        if isDarkTheme():
            timestampColor = QColor(208, 209, 211)
        else:
            timestampColor = QColor(120, 120, 120)

        # 绘制indicator
        level = record.get("level", "DEBUG")

        indicatorColor = self._get_indicator_color(level)
        indicatorRect = self.uiRect.getIndicatorRect(option)
        self._drawIndicator(painter, indicatorRect, indicatorColor)

        # 绘制时间戳
        timestampRect = self.uiRect.getTimestampRect(option)
        self._drawTextBase(painter, timestampRect, record.get("timestamp", ""), timestampColor, 14)

        # 绘制日志级别
        levelRect = self.uiRect.getLevelRect(timestampRect, option)
        self._drawTextBase(painter, levelRect, level, indicatorColor, 14)

        # 绘制记录器名称
        name = "{name} ({callsite})".format(name = record.get("name", ""), callsite = record.get("callsite", ""))
        nameRect = self.uiRect.getNameRect(levelRect, option)
        self._drawTextBase(painter, nameRect, name, timestampColor, 14)

        # 绘制日志消息        
        messageRect = self.uiRect.getMessageRect(timestampRect, option)
        self._drawText(painter, messageRect, record.get("message", ""))

    def _get_indicator_color(self, level: str) -> QColor:
        dark_palette = {
            "DEBUG": QColor(180, 180, 180),
            "INFO": QColor(90, 170, 255),
            "WARNING": QColor(255, 178, 102),
            "ERROR": QColor(255, 102, 102),
        }

        light_palette = {
            "DEBUG": QColor(96, 96, 96),
            "INFO": QColor(0, 102, 170),
            "WARNING": QColor(204, 102, 0),
            "ERROR": QColor(204, 0, 0),
        }

        palette = dark_palette if isDarkTheme() else light_palette
        return palette.get(level, QColor(180, 180, 180) if isDarkTheme() else QColor(96, 96, 96))

class UIRect:
    def __init__(self):
        self.margin = 10
        self.spacer = 20

    def getIndicatorRect(self, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top() + 2
        left = self.margin + option.rect.left() + 4

        return QRect(left, top, 16, 16)

    def getTimestampRect(self, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()
        left = self.margin + option.rect.left() + 30

        return QRect(left, top, 128, 24)
    
    def getLevelRect(self, timestampRect: QRect, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()
        left = timestampRect.right() + self.spacer

        return QRect(left, top, 70, 24)
    
    def getNameRect(self, levelRect: QRect, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()
        left = levelRect.right() + self.spacer

        return QRect(left, top, 500, 24)
    
    def getMessageRect(self, timestampRect: QRect, option: QStyleOptionViewItem):
        top = timestampRect.bottom() + self.margin / 2
        left = self.margin + option.rect.left() + 5

        return QRect(left, top, option.rect.width() - 2 * self.margin, 48)
