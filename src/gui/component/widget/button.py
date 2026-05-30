from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QSize

from qfluentwidgets import (
    PrimaryPushButton, IndeterminateProgressRing, ToolTipFilter, TransparentTogglePushButton, PrimarySplitPushButton,
    SwitchButton, BodyLabel
)
from qfluentwidgets import ToolButton as _ToolButton, TransparentToolButton as _TransparentToolButton

class IndeterminateProgressPushButton(PrimaryPushButton):
    """
    将 PrimaryPushButton 和 IndeterminateProgressRing 组合，实现类似 IndeterminateProgressPushButton 效果。
    """
    def __init__(self, text = "", parent = None):
        super().__init__(parent)

        self._text = text

        self.setText(text)

        self.spinner = IndeterminateProgressRing(self)
        self.spinner.setStrokeWidth(3)
        self.spinner.setFixedSize(20, 20)
        self.spinner.setCustomBarColor(Qt.GlobalColor.white, Qt.GlobalColor.black)
        self.spinner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.spinner.hide()

        self._center_spinner()

    def _center_spinner(self):
        dec_size = QSize(20, 20)

        x = (self.width() - dec_size.width()) // 2
        y = (self.height() - dec_size.height()) // 2

        self.spinner.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self._center_spinner()

    def setIndeterminateState(self, state: bool):
        """
        是否显示不确定进度环
        """

        if state:
            self.spinner.show()

            self.setText("")

        else:
            self.spinner.hide()

            self.setText(self._text)

class IndeterminateProgressSplitPushButton(PrimarySplitPushButton):
    """
    将 PrimarySplitPushButton 和 IndeterminateProgressRing 组合，实现类似 IndeterminateProgressPushButton 效果。
    """
    def __init__(self, text = "", parent = None):
        super().__init__(parent)

        self._text = text

        self.setText(text)

        self.spinner = IndeterminateProgressRing(self)
        self.spinner.setStrokeWidth(3)
        self.spinner.setFixedSize(20, 20)
        self.spinner.setCustomBarColor(Qt.GlobalColor.white, Qt.GlobalColor.black)
        self.spinner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.spinner.hide()

        self._center_spinner()

    def _center_spinner(self):
        dec_size = QSize(20, 20)

        x = (self.button.width() - dec_size.width()) // 2
        y = (self.button.height() - dec_size.height()) // 2

        self.spinner.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self._center_spinner()

    def setIndeterminateState(self, state: bool):
        """
        是否显示不确定进度环
        """

        if state:
            self.spinner.show()

            self.setText("")

        else:
            self.spinner.hide()

            self.setText(self._text)

class ToolButton(_ToolButton):
    """
    增加了 Tooltip 显示的 ToolButton。
    """
    def setToolTip(self, arg__1):
        super().setToolTip(arg__1)

        self.setToolTipDuration(3000)

        self.installEventFilter(ToolTipFilter(self))

class TransparentToolButton(_TransparentToolButton):
    """
    增加了 Tooltip 显示的 TransparentToolButton。
    """
    def setToolTip(self, arg__1):
        super().setToolTip(arg__1)

        self.setToolTipDuration(3000)

        self.installEventFilter(ToolTipFilter(self))

class PagerNumberButton(TransparentTogglePushButton):
    def __init__(self, text: str, number: int, parent = None):
        super().__init__(parent)

        self.setText(text)
        self.setFixedHeight(30)

        self.number = number

class LabelSwitchButton(QWidget):
    def __init__(self, text: str, parent = None):
        super().__init__(parent)

        self.label = BodyLabel(text, self)
        self.switch = SwitchButton(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.label)
        layout.addSpacing(5)
        layout.addWidget(self.switch)
