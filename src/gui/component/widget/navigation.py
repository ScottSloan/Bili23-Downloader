from PySide6.QtCore import Qt, QRect, QPoint, QRectF, QMargins, QSize, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QCursor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from qfluentwidgets import FlyoutViewBase, NavigationPushButton, FluentIcon, setFont, isDarkTheme, drawIcon

from util.common import ExtendedFluentIcon, config

from typing import Union

class NavigationFlyoutMenuItem(QWidget):
    clicked = Signal()

    def __init__(self, icon: Union[str, QIcon, FluentIcon], text: str, parent = None):
        super().__init__(parent)

        self.isPressed = False
        self.isEnter = False

        self.lightTextColor = QColor(0, 0, 0)
        self.darkTextColor = QColor(255, 255, 255)

        self._icon = icon
        self._text = text

        setFont(self)

    def sizeHint(self):
        return QSize(200, 36)

    def enterEvent(self, e):
        self.isEnter = True

        self.update()

    def leaveEvent(self, e):
        self.isEnter = False
        self.isPressed = False

        self.update()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)

        self.isPressed = True
        self.update()

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)

        self.isPressed = False
        self.update()

        self.clicked.emit(True)

    def click(self):
        self.clicked.emit(True)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.setPen(Qt.PenStyle.NoPen)

        if self.isPressed:
            painter.setOpacity(0.7)

        if not self.isEnabled():
            painter.setOpacity(0.4)

        c = 255 if isDarkTheme() else 0
        m = self._margins()
        pl, pr = m.left(), m.right()
        globalRect = QRect(self.mapToGlobal(QPoint()), self.size())

        if ((self.isEnter and globalRect.contains(QCursor.pos()))) and self.isEnabled():
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)

        drawIcon(self._icon, painter, QRectF(11.5+pl, 10, 16, 16))

        painter.setFont(self.font())
        painter.setPen(self.textColor())

        left = 44 + pl if not self.icon().isNull() else pl + 16
        painter.drawText(QRectF(left, 0, self.width()-13-left-pr, self.height()), Qt.AlignVCenter, self.text())

    def _margins(self):
        return QMargins(0, 0, 0, 0)
    
    def text(self):
        return self._text
    
    def textColor(self):
        return self.darkTextColor if isDarkTheme() else self.lightTextColor
    
    def icon(self):
        return self._icon.icon()

class NavigationFlyoutMenu(FlyoutViewBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.viewLayout = QVBoxLayout(self)
        self.viewLayout.setContentsMargins(5, 8, 5, 8)
        self.viewLayout.setSpacing(5)

        self.setMaximumWidth(200)

    def addWidget(self, widget: NavigationPushButton):
        self.viewLayout.addWidget(widget)

        widget.clicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, checked):
        self.hide()

class FavoriteFlyoutMenu(NavigationFlyoutMenu):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_menu()

    def init_menu(self):
        for entry in config.user_favorite_list:
            title = entry.get("title", "")

            widget = NavigationFlyoutMenuItem(ExtendedFluentIcon.FAVORITE, title, parent = self)

            self.addWidget(widget)

        watch_later_widget = NavigationFlyoutMenuItem(ExtendedFluentIcon.CLOCK, self.tr("稍后再看"), parent = self)

        self.addWidget(watch_later_widget)
