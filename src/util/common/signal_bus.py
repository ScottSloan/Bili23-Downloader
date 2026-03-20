from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QPixmap

from util.common.enum import ToastNotificationCategory

class SignalBus:
    class ToastNotification(QObject):
        # 用于在 MainWindow 中显示 Toast 通知
        show = Signal(ToastNotificationCategory, str, str)

    class Parse(QObject):
        update_episode_list = Signal(dict)

        preview_init = Signal(dict)
        query_video_info = Signal(int, int, object)
        query_audio_info = Signal(int, object)

    class Download(QObject):
        create_task = Signal(list)

        add_to_downloading_list = Signal(list)
        add_to_completed_list = Signal(list)

        remove_from_downloading_list = Signal(object)
        remove_from_completed_list = Signal(object)

        update_downloading_count = Signal(int)
        update_downloading_item = Signal(object)

        start_next_task = Signal()

    class Login(QObject):
        # 用于登录相关的信号
        start_server = Signal()
        stop_server = Signal()

        send_sms = Signal()

        update_avatar = Signal(QPixmap)

    def __init__(self):
        self.toast = self.ToastNotification()
        self.parse = self.Parse()
        self.download = self.Download()
        self.login = self.Login()

signal_bus = SignalBus()