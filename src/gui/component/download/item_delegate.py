from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
from PySide6.QtCore import QSize, QModelIndex, Qt, QRect, QEvent, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPixmap, QFont, QMouseEvent

from qfluentwidgets import FluentIcon, ThemeColor, Theme, isDarkTheme, drawIcon

from util.download.task.info import TaskInfo

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

    def _drawProgressBar(self, painter: QPainter, rect: QRect, value: int):
        if isDarkTheme():
            backgroundColor = QColor(255, 255, 255, 155)
        else:
            backgroundColor = QColor(0, 0, 0, 155)

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

    def _drawPixmap(self, painter: QPainter, rect: QRect, pixmap: QPixmap):
        painter.drawPixmap(rect, pixmap)

    def _drawText(self, painter: QPainter, rect: QRect, text: str):
        if isDarkTheme():
            textColor = QColor(255, 255, 255)
        else:
            textColor = QColor(0, 0, 0)

        painter.setFont(self._getFont(10))
        painter.setPen(textColor)

        painter.drawText(rect, text)

    def _drawDescriptionText(self, painter: QPainter, rect: QRect, text: str):
        if isDarkTheme():
            textColor = QColor(206, 206, 206)
        else:
            textColor = QColor(96, 96, 96)

        painter.setFont(self._getFont(10))
        painter.setPen(textColor)

        painter.drawText(rect, text)

    def _getFont(self, size: int):
        font = QApplication.font()
        font.setPointSize(size)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        return font

    def _reverseIconColor(self, icon):
        theme = Theme.DARK if not isDarkTheme() else Theme.LIGHT
        return icon.icon(theme)

class DownloadItemDelegate(QStyledItemDelegate, FluentStyledItemDelegate):
    contextMenuRequested = Signal(QModelIndex, QPoint)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.uiRect = UIRect()

        self.ActionButtonHoveredRow = -1
        self.DeleteButtonHoveredRow = -1

    def sizeHint(self, option, index):
        return QSize(0, 100)
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        painter.setClipping(True)
        painter.setClipRect(option.rect)

        self._checkHoverRow(option, index)

        self._drawBackground(painter, option, index)

        self._paintItemUI(painter, option, index)

        painter.restore()

    def editorEvent(self, event: QEvent, model, option, index: QModelIndex):
        view = self.parent()

        if event.type() == QEvent.Type.MouseMove:
            self._buttonHoverEvent(option, index, event)
            view.update()

        if event.type() == QEvent.Type.Leave:
            self.hoverRow = -1
            view.update()

        if event.type() == QEvent.Type.MouseButtonRelease:
            return self._pressEvent(option, index, event)

        return super().editorEvent(event, model, option, index)

    def _paintItemUI(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        # 获取任务信息
        task_info: TaskInfo = index.data(Qt.ItemDataRole.UserRole)

        # 左侧封面、标题和信息
        coverRect = self.uiRect.getCoverRect(option)
        self._drawPixmap(painter, coverRect, self._queryCover(task_info.Basic.cover_id, task_info.Episode.cover, index))

        titleRect = self.uiRect.getTitleRect(coverRect, option)
        self._drawText(painter, titleRect, task_info.Basic.show_title)

        infoRect = self.uiRect.getInfoRect(titleRect, option)
        self._drawDescriptionText(painter, infoRect, "1080P 高清")

        sizeRect = self.uiRect.getSizeRect(infoRect)
        self._drawDescriptionText(painter, sizeRect, "256 MB/ 362MB")


        # 右侧进度条、状态
        progressBarRect = self.uiRect.getProgressBarRect(titleRect, option)
        self._drawProgressBar(painter, progressBarRect, task_info.Download.progress)

        statusRect = self.uiRect.getStatusRect(progressBarRect, infoRect, option)
        self._drawDescriptionText(painter, statusRect, "等待下载...")


        # 右侧控制和删除按钮
        actionButtonRect = self.uiRect.getActionButtonRect(option)
        self._drawPrimaryButton(painter, actionButtonRect, FluentIcon.PLAY, self.ActionButtonHoveredRow == index.row())

        deleteButtonRect = self.uiRect.getDeleteButtonRect(option)
        self._drawButton(painter, deleteButtonRect, FluentIcon.DELETE, self.DeleteButtonHoveredRow == index.row())
    
    def _checkHoverRow(self, option: QStyleOptionViewItem, index: QModelIndex):
        if option.state & QStyle.StateFlag.State_MouseOver:
            self.hoverRow = index.row()

        elif self.hoverRow == index.row():
            self.hoverRow = -1

    def _buttonHoverEvent(self, option: QStyleOptionViewItem, index: QModelIndex, event: QMouseEvent):
        pos = event.pos()

        actionButtonRect = self.uiRect.getActionButtonRect(option)
        deleteButtonRect = self.uiRect.getDeleteButtonRect(option)

        if actionButtonRect.contains(pos):
            self.ActionButtonHoveredRow = index.row()
        else:
            self.ActionButtonHoveredRow = -1

        if deleteButtonRect.contains(pos):
            self.DeleteButtonHoveredRow = index.row()
        else:
            self.DeleteButtonHoveredRow = -1

    def _pressEvent(self, option: QStyleOptionViewItem, index: QModelIndex, event: QMouseEvent):
        pos = event.pos()

        if event.button() == Qt.MouseButton.RightButton:
            # 右键点击，弹出上下文菜单
            self.contextMenuRequested.emit(index, event.globalPos())

            return True

        actionButtonRect = self.uiRect.getActionButtonRect(option)
        deleteButtonRect = self.uiRect.getDeleteButtonRect(option)

        if actionButtonRect.contains(pos):
            print("暂停")

            return True

        if deleteButtonRect.contains(pos):
            print("删除")

            return True

        return False

    def _queryCover(self, cover_id: str, cover_url: str, index: QModelIndex):
        # 由委托发起查询封面请求
        return index.model().queryRowCover(cover_id, cover_url, index.row())

class UIRect:
    def __init__(self):
        self.margin = 10
        self.spacer = self.margin * 2
        self.buttonSize = 32

    def getCoverRect(self, option: QStyleOptionViewItem):
        top = self.margin + option.rect.top()

        return QRect(self.margin, top, 144, 80)

    def getTitleRect(self, coverRect: QRect, option: QStyleOptionViewItem):
        left = coverRect.right() + self.spacer
        top = coverRect.top() + 5

        width = option.rect.width() - left - 250

        return QRect(left, top, width, 16)
    
    def getInfoRect(self, titleRect: QRect, option: QStyleOptionViewItem):
        left = titleRect.left()
        top = option.rect.bottom() - titleRect.height() - self.margin - 5

        return QRect(left, top, 125, 16)
    
    def getSizeRect(self, infoRect: QRect):
        left = infoRect.right() + self.spacer
        top = infoRect.top()

        return QRect(left, top, 125, 16)

    def getProgressBarRect(self, titleRect: QRect, option: QStyleOptionViewItem):
        left = option.rect.width() - self.margin - self.buttonSize * 2 - self.spacer * 3 - 200
        top = titleRect.top() + self.margin

        return QRect(left, top, 200, 16)
    
    def getStatusRect(self, progressBarRect: QRect, infoRect: QRect, option: QStyleOptionViewItem):
        left = progressBarRect.left()
        top = infoRect.top()

        return QRect(left, top, 200, 16)

    def getActionButtonRect(self, option: QStyleOptionViewItem):
        left = option.rect.width() - self.buttonSize * 2 - self.spacer * 2
        top = (option.rect.height() - self.buttonSize) / 2 + option.rect.top()

        return QRect(left, top, self.buttonSize, self.buttonSize)
    
    def getDeleteButtonRect(self, option: QStyleOptionViewItem):
        left = option.rect.width() - self.buttonSize - self.spacer * 2 + self.margin
        top = (option.rect.height() - self.buttonSize) / 2 + option.rect.top()

        return QRect(left, top, self.buttonSize, self.buttonSize)
