from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QPixmap

from util.common.enum import ToastNotificationCategory

class SignalBus:
    class ToastNotification(QObject):
        # 用于在 MainWindow 中显示 Toast 通知
        show = Signal(ToastNotificationCategory, str, str)

        show_long_message = Signal(str, str)

        sys_show = Signal(ToastNotificationCategory, str, str)

    class Parse(QObject):
        update_parse_list = Signal(object, object)

        preview_init = Signal(dict)
        query_video_info = Signal(int, int, object)
        query_audio_info = Signal(int, object)

        update_column_settings = Signal()

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

    class Update(QObject):
        check = Signal(bool)
        show_dialog = Signal(dict)

    class Interface(QObject):
        mica_effect_changed = Signal(bool)

    def __init__(self):
        self.toast = self.ToastNotification()
        self.parse = self.Parse()
        self.download = self.Download()
        self.login = self.Login()
        self.update = self.Update()
        self.interface = self.Interface()

signal_bus = SignalBus()