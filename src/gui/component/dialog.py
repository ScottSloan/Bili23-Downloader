from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QApplication
from PySide6.QtCore import Qt, QEventLoop, QSize
from PySide6.QtGui import QIcon

from qfluentwidgets import (
    MessageBoxBase, FluentWidgetTitleBar, PrimaryPushButton, PushButton, FluentWidget as _FluentWidget,
    PopUpAniStackedWidget, InfoBar, InfoBarPosition, MessageBox as _MessageBox
)
from .widget import PivotItem, Pivot, ScrollArea

from util.common.enum import ToastNotificationCategory
from util.common.style_sheet import StyleSheet
from util.common.config import config

class Base:
    def __init__(self):
        self.esc_close = True

    def set_esc_close(self, enable: bool):
        """
        设置是否允许通过按下 Esc 键来关闭对话框。
        """
        self.esc_close = enable

    def enable_delete_on_close(self):
        """
        设置对话框在关闭时自动删除自身，释放资源。
        """
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    def show_top_toast_message(self, category: ToastNotificationCategory, title: str, message: str):
        match category:
            case ToastNotificationCategory.INFO:
                func = InfoBar.info

            case ToastNotificationCategory.SUCCESS:
                func = InfoBar.success

            case ToastNotificationCategory.WARNING:
                func = InfoBar.warning

            case ToastNotificationCategory.ERROR:
                func = InfoBar.error

        func(
            title = title,
            content = message,
            isClosable = False,
            duration = 3000,
            position = InfoBarPosition.TOP,
            parent = self
        )

class DialogBase(Base, MessageBoxBase):
    """
    DialogBase 在原 MessageBoxBase 的基础上，添加以下功能：
    1.连接了 accepted 和 rejected 信号到 on_dialog_close 方法，使得在对话框被接受或拒绝时都能执行一些清理操作。
    2.提供 show_top_toast_message 方法，可以在对话框顶部显示一个 Toast 消息，方便在对话框内进行提示信息的展示。
    """
    def __init__(self, parent = None):
        Base.__init__(self)
        MessageBoxBase.__init__(self, parent)

        self.accepted.connect(self.on_dialog_close)
        self.rejected.connect(self.on_dialog_close)

        self.enable_delete_on_close()
        self._setup_stay_on_top()

    def on_dialog_close(self):
        """
        on_close 在对话框关闭时被调用，可以在这里执行一些清理操作。
        """
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and not self.esc_close:
            event.ignore()
        else:
            super().keyPressEvent(event)

    def _setup_stay_on_top(self):
        # 使对话框保持在所有窗口之上，确保用户注意到它。
        if config.get(config.stay_on_top):
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

class FluentWidget(_FluentWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

    def _init_common(self):
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))

        self.setMicaEffectEnabled(config.get(config.mica_effect))
        self.setStayOnTop(config.get(config.stay_on_top))

    def showEvent(self, event):
        parent_rect = self.parent().geometry()

        new_left = parent_rect.left() + (parent_rect.width() - self.size().width()) // 2
        new_top = parent_rect.top() + (parent_rect.height() - self.size().height()) // 2

        self.move(new_left, new_top)

        super().showEvent(event)

class FluentDialogBase(Base, _FluentWidget):
    """
    通过 FluentWidget 实现的模态对话框基类，提供了 Fluent 风格的标题栏和窗口效果。
    """
    def __init__(self, size: QSize, parent = None):
        Base.__init__(self)
        _FluentWidget.__init__(self, parent)

        self._size = size
        self._setup_title_bar()

        self.setMicaEffectEnabled(config.get(config.mica_effect))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStayOnTop(config.get(config.stay_on_top))

        self._event_loop = None
        self._result = False

    def _setup_title_bar(self):
        titleBar = FluentWidgetTitleBar(self)
        titleBar.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        titleBar.hBoxLayout.insertSpacing(0, 12)
        titleBar.setFixedHeight(36)

        titleBar.minBtn.hide()
        titleBar.maxBtn.hide()
        
        titleBar.setDoubleClickEnabled(False)

        #self.titleBar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self.setTitleBar(titleBar)

        self.titleBar.raise_()
        
    def _center_on_parent(self):
        parent_rect = QApplication.instance().window.geometry()

        new_left = parent_rect.left() + (parent_rect.width() - self._size.width()) // 2
        new_top = parent_rect.top() + (parent_rect.height() - self._size.height()) // 2

        self.move(new_left, new_top)

    def accept(self):
        self._result = True
        self.close()

    def reject(self):
        self._result = False
        self.close()

    def closeEvent(self, e):
        if self._event_loop and self._event_loop.isRunning():
            self._event_loop.quit()
        
        super().closeEvent(e)

    def showEvent(self, e):
        self._center_on_parent()

        super().showEvent(e)

    def exec(self):
        # 模拟实现模态对话框的 exec 方法
        self.show()

        # 将 QEventLoop 的父对象设为自己，避免独立事件循环导致的内存及生命周期问题
        self._event_loop = QEventLoop(self)
        self._event_loop.exec()

        # 保存结果并在稍后删除自身，避免在事件循环退出的第一时间删除 C++ 层对象导致崩溃
        res = self._result
        self.deleteLater()
        
        return res

class TopNavigationDialogBase(FluentDialogBase):
    """
    顶部导航对话框基类，适用于需要在对话框顶部显示导航栏的场景。
    """
    def __init__(self, size: QSize, parent = None):
        super().__init__(size, parent = None)

        self._setup_widget()

    def _setup_widget(self):
        self.pivot = Pivot(self)
        #self.pivot.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self.stackedWidget = PopUpAniStackedWidget(self)
        #self.stackedWidget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.stackedWidget.setContentsMargins(0, 0, 0, 0)

        self.okBtn = PrimaryPushButton(self.tr("OK"), self)
        self.okBtn.setMinimumWidth(80)
        self.okBtn.clicked.connect(self.accept)

        self.cancelBtn = PushButton(self.tr("Cancel"), self)
        self.cancelBtn.setMinimumWidth(80)
        self.cancelBtn.clicked.connect(self.reject)

        pivot_layout = QHBoxLayout()
        pivot_layout.setContentsMargins(0, 0, 0, 0)
        pivot_layout.addSpacing(5)
        pivot_layout.addWidget(self.pivot)
        pivot_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 5, 0, 0)
        button_layout.setSpacing(10)
        button_layout.addStretch()
        button_layout.addWidget(self.okBtn)
        button_layout.addWidget(self.cancelBtn)
        
        self.vboxLayout = QVBoxLayout(self)
        self.vboxLayout.setContentsMargins(10, 32, 10, 10)
        self.vboxLayout.setSpacing(5)
        self.vboxLayout.addLayout(pivot_layout)
        self.vboxLayout.addWidget(self.stackedWidget)
        self.vboxLayout.addLayout(button_layout)

        StyleSheet.FLUENT_DIALOG.apply(self.stackedWidget)

    def addItem(self, routeKey: str, text: str, icon, widget: QWidget):
        item = PivotItem(text, icon, self.pivot)
        item.setFontSize(13)

        self.pivot.addItem(
            routeKey,
            item,
            lambda: self.stackedWidget.setCurrentWidget(widget),
        )

        self.stackedWidget.addWidget(widget)

class MessageBox(_MessageBox):
    def __init__(self, title: str, content: str, parent: QWidget = None):
        super().__init__(title, content, parent)

        self.textLayout.removeWidget(self.contentLabel)

        self._scroll_area = ScrollArea(self.widget)
        self._scroll_area.setContentsMargins(0, 0, 0, 0)
        self._scroll_area._setScrollWidget(self.contentLabel, resizable = True)

        self.textLayout.addWidget(self._scroll_area)

        self.widget.setMaximumHeight(parent.height() * 0.8)

    def showEvent(self, e):
        content_width = self.contentLabel.rect().width()

        self._scroll_area.setMinimumWidth(content_width)

        super().showEvent(e)