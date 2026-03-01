from PySide6.QtGui import QColor, QPixmap

from qfluentwidgets import (
    AvatarWidget, BodyLabel, CaptionLabel, HyperlinkButton, FlyoutViewBase, MessageBox, isDarkTheme
)

from util.common.enum import ToastNotificationCategory
from util.common.signal_bus import signal_bus
from util.common.config import config

class ProfileCard(FlyoutViewBase):
    """
    展示用户信息的组件。
    """
    def __init__(self, logout_callback, parent = None):
        super().__init__(parent)

        self.logout_callback = logout_callback
        self.main_window = parent

        self.init_UI()

    def init_UI(self):
        self.avatar = AvatarWidget(config.user_avatar_pixmap, self)
        self.avatar.setRadius(24)

        self.uname_lab = BodyLabel(config.user_uname, self)

        color = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)

        self.uid_lab = CaptionLabel(f"UID: {config.user_uid}", self)
        self.uid_lab.setStyleSheet('QLabel{color: ' + color.name() + '}')

        self.logout_btn = HyperlinkButton(self)
        self.logout_btn.setText(self.tr("Logout"))

        self.avatar.move(12, 10)
        self.uname_lab.move(74, 12)
        self.uid_lab.move(74, 31)
        self.logout_btn.move(62, 48)

        self.setFixedSize(250, 90)

        self.connect_signals()

    def connect_signals(self):
        self.logout_btn.clicked.connect(self.on_logout)

    def on_logout(self):
        self.close()

        dialog = MessageBox(self.tr("Log Out"), self.tr("Are you sure you want to log out? This will also clear locally stored cookies."), self.main_window)

        if dialog.exec():
            self.logout_callback()

            signal_bus.login.update_avatar.emit(QPixmap(":/bili23/image/noface.jpg"))
            signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Successfully logged out"))
        