from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPixmap, QPainterPath
from PySide6.QtCore import QModelIndex, Qt, QRect, Signal, QPoint

from qfluentwidgets import isDarkTheme, setFont, drawIcon, ThemeColor, Theme

from typing import List

class FluentStyledItemDelegate:
    def __init__(self):
        self.hoverRow = -1
        self.pressedRow = -1
        self.selectedRows = set()

    def setHoverRow(self, row: int):
        pass

    def setPressedRow(self, row: int):
        self.pressedRow = row

    def setSelectedRows(self, indexes: List[QModelIndex]):
        self.selectedRows.clear()

        for index in indexes:
            self.selectedRows.add(index.row())
            if index.row() == self.pressedRow:
                self.pressedRow = -1

    def _drawBackground(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.setPen(Qt.PenStyle.NoPen)

        isHover = self.hoverRow == index.row()
        isPressed = self.pressedRow == index.row()
        isDark = isDarkTheme()

        c = 255 if isDark else 0
        alpha = 0

        if index.row() not in self.selectedRows:
            if isPressed:
                alpha = 9 if isDark else 6
            elif isHover:
                alpha = 12
        else:
            if isPressed:
                alpha = 15 if isDark else 9
            elif isHover:
                alpha = 25
            else:
                alpha = 17

        if index.data(Qt.ItemDataRole.BackgroundRole):
            painter.setBrush(index.data(Qt.ItemDataRole.BackgroundRole))
        else:
            painter.setBrush(QColor(c, c, c, alpha))

        painter.drawRoundedRect(option.rect, 5, 5)

    def _drawPrimaryButton(self, painter: QPainter, rect: QRect, icon, hover = False):
        if hover:
            if isDarkTheme():
                primaryColor = ThemeColor.DARK_1.color()
            else:
                primaryColor = ThemeColor.LIGHT_1.color()
        else:
            primaryColor = ThemeColor.PRIMARY.color()

        borderColor = ThemeColor.LIGHT_1.color()
        icon = self._reverseIconColor(icon)

        self._drawButtonBase(painter, rect, primaryColor, borderColor, icon)

    def _drawButton(self, painter: QPainter, rect: QRect, icon, hover = False):
        if isDarkTheme():
            if hover:
                primaryColor = QColor(255, 255, 255, 21)
            else:
                primaryColor = QColor(255, 255, 255, 15)

            borderColor = QColor(255, 255, 255, 13)
        else:
            if hover:
                primaryColor = QColor(249, 249, 249, 128)
            else:
                primaryColor = QColor(255, 255, 255, 178)

            borderColor = QColor(255, 255, 255, 19)

        self._drawButtonBase(painter, rect, primaryColor, borderColor, icon)

    def _drawButtonBase(self, painter: QPainter, rect: QRect, primaryColor: QColor, borderColor: QColor, icon):
        painter.setPen(Qt.PenStyle.NoPen)

        # 绘制边框
        painter.setBrush(borderColor)
        painter.drawRoundedRect(rect, 5, 5)

        # 绘制背景
        painter.setBrush(primaryColor)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 5, 5)

        # 绘制图标
        drawIcon(icon, painter, rect.adjusted(8, 8, -8, -8))

    def _drawProgressBar(self, painter: QPainter, rect: QRect, value: int, error = False, paused = False):
        if isDarkTheme():
            backgroundColor = QColor(255, 255, 255, 155)
        else:
            backgroundColor = QColor(0, 0, 0, 155)

        if error:
            barColor = QColor(255, 153, 164) if isDarkTheme() else QColor(196, 43, 28)
        elif paused:
            barColor = QColor(252, 225, 0) if isDarkTheme() else QColor(157, 93, 0)
        else:
            barColor = ThemeColor.PRIMARY.color()

        # 绘制背景
        painter.setPen(backgroundColor)
        painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())

        # 绘制进度
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(barColor)

        w = int(value / 100 * rect.width())
        r = rect.height() / 4

        painter.drawRoundedRect(rect.left(), rect.top() - 2, w, r, 1, 1)

    def _drawPixmap(self, painter: QPainter, rect: QRect, option: QStyleOptionViewItem, pixmap: QPixmap, isPlaceholder = False):
        if isPlaceholder:
            # 占位图背景
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(227, 229, 231))

            painter.drawRoundedRect(rect, 5, 5)

        else:
            # 绘制圆角图片
            path = QPainterPath()
            path.addRoundedRect(rect, 5, 5)

            painter.setClipPath(path)

        painter.drawPixmap(rect, pixmap)

        painter.setClipRect(option.rect)

    def _drawText(self, painter: QPainter, rect: QRect, text: str):
        if isDarkTheme():
            textColor = QColor(255, 255, 255)
        else:
            textColor = QColor(0, 0, 0)

        setFont(painter, 14)

        font = painter.font()

        metrics = QFontMetrics(font)
        elided_title = metrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())

        painter.setFont(font)
        painter.setPen(textColor)

        painter.drawText(rect, elided_title)

    def _drawDescriptionText(self, painter: QPainter, rect: QRect, text: str, error = False):
        if error:
            textColor = QColor(255, 153, 164) if isDarkTheme() else QColor(196, 43, 28)
        else:
            textColor = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)

        setFont(painter, 14)

        font = painter.font()

        metrics = QFontMetrics(font)
        elided_text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())

        painter.setFont(font)
        painter.setPen(textColor)
        # 自动换行并左对齐、垂直居中
        painter.drawText(rect, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_text)

    def _getFont(self, size: int):
        font = QApplication.font()
        font.setPointSize(size)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        return font

    def _reverseIconColor(self, icon):
        theme = Theme.DARK if not isDarkTheme() else Theme.LIGHT
        return icon.icon(theme)

class CoverQueryDelegateBase(QStyledItemDelegate, FluentStyledItemDelegate):
    """
    具有异步封面显示功能的委托基类
    """

    contextMenuRequested = Signal(QModelIndex, QPoint)

    def __init__(self, parent = None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        painter.setClipping(True)
        painter.setClipRect(option.rect)

        self._checkHoverRow(option, index)

        self._drawBackground(painter, option, index)

        self._paintItemUI(painter, option, index)

        painter.restore()

    def _checkHoverRow(self, option: QStyleOptionViewItem, index: QModelIndex):
        if option.state & QStyle.StateFlag.State_MouseOver:
            self.hoverRow = index.row()

        elif self.hoverRow == index.row():
            self.hoverRow = -1

    def _queryCover(self, cover_id: str, cover_url: str, index: QModelIndex):
        # 由委托发起查询封面请求
        return index.model().queryRowCover(cover_id, cover_url, index.row())
    
    def _drawCover(self, painter: QPainter, rect: QRect, option: QStyleOptionViewItem, index: QModelIndex, cover_id: str, cover_url: str):
        # 先绘制占位图
        pixmap, isPlaceholder = self._queryCover(cover_id, cover_url, index)

        self._drawPixmap(painter, rect, option, pixmap, isPlaceholder)
