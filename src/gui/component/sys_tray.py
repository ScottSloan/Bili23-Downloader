from PySide6.QtWidgets import QSystemTrayIcon, QWidget

from qfluentwidgets import SystemTrayMenu, Action

from util.common.enum import ToastNotificationCategory
from util.common.signal_bus import signal_bus

class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setIcon(parent.windowIcon())
        self.setToolTip(parent.windowTitle())

        self.menu = SystemTrayMenu(parent = parent)

        self.menu.addAction(Action("显示主界面", triggered = self.on_show_main_window))
        self.menu.addSeparator()
        self.menu.addAction(Action("暂停所有下载"))
        self.menu.addSeparator()
        self.menu.addAction(Action("退出", triggered = self.on_exit))

        self.setContextMenu(self.menu)

    def on_show_main_window(self):
        signal_bus.toast.sys_show.emit(ToastNotificationCategory.INFO, "ikun", "你干嘛哎哟~")

        # self.parent().show()
        # self.parent().raise_()
        # self.parent().activateWindow()

    def on_exit(self):
        self.parent().close()

    def show_message(self, category: ToastNotificationCategory, title: str, message: str):
        match category:
            case ToastNotificationCategory.SUCCESS:
                icon = QSystemTrayIcon.MessageIcon.Information

            case ToastNotificationCategory.ERROR:
                icon = QSystemTrayIcon.MessageIcon.Critical

            case ToastNotificationCategory.WARNING:
                icon = QSystemTrayIcon.MessageIcon.Warning

            case ToastNotificationCategory.INFO:
                icon = QSystemTrayIcon.MessageIcon.Information

        self.showMessage(title, message, icon)

    
