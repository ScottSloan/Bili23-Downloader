from PySide6.QtWidgets import QSystemTrayIcon, QWidget

from qfluentwidgets import SystemTrayMenu, Action

from util.common.enum import ToastNotificationCategory

import sys

class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setIcon(parent.windowIcon())
        self.setToolTip(parent.windowTitle())

        self.menu = SystemTrayMenu(parent = parent)

        self.menu.addAction(Action(self.tr("Show main window"), triggered = self.on_show_main_window))
        self.menu.addSeparator()
        self.menu.addAction(Action(self.tr("Exit"), triggered = self.on_exit))

        self.setContextMenu(self.menu)
        
        # 点击托盘图标时显示主窗口
        self.activated.connect(self.on_activated)

    def on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_show_main_window(reason)

    def on_show_main_window(self, reason: QSystemTrayIcon.ActivationReason = None):
            parent: QWidget = self.parent()
            parent._activate_window()

    def on_exit(self):
        self.on_show_main_window()
        
        sys.exit()

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

    
