from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QPixmap

from .enum import ToastNotificationCategory
from .config import config

from threading import Lock

class SignalBus:
    class ToastNotification(QObject):
        # 用于在 MainWindow 中显示 Toast 通知
        show = Signal(ToastNotificationCategory, str, str)

        show_long_message = Signal(str, str)

        sys_show = Signal(ToastNotificationCategory, str, str)

    class Parse(QObject):
        update_parse_list = Signal(str, str, object, object)

        preview_init = Signal(dict)
        query_video_info = Signal(int, int, object)
        query_audio_info = Signal(int, object)

        update_column_settings = Signal()
        update_preview_info = Signal()

        parse_url = Signal(str)

        search_keyword = Signal(str)

    class Download(QObject):
        create_task = Signal(list)

        add_to_downloading_list = Signal(list)
        auto_manage_concurrent_downloads = Signal()
        add_to_completed_list = Signal(list)

        remove_from_downloading_list = Signal(object)
        remove_from_completed_list = Signal(object)

        sort_downloading_list = Signal(str, bool)
        sort_completed_list = Signal(str, bool)

        update_downloading_count = Signal(int)
        update_downloading_item = Signal(object)

        start_next_task = Signal()

    class Login(QObject):
        # 用于登录相关的信号
        start_server = Signal()
        stop_server = Signal()

        send_sms = Signal()

        update_avatar = Signal(object)

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

        self.pending_signals = []  # 存储在主窗口初始化完成前发出的信号，格式为 (signal, args, kwargs)

        self._lock = Lock() # 用于保护待发送列表的线程锁

    def emit_signal(self, signal, *args, **kwargs):
        if config.main_window_ready:
            # 初始化完成，直接发送信号
            signal.emit(*args, **kwargs)
        else:
            # 否则加入待发送列表。使用线程锁保证多线程安全
            with self._lock:
                # 双重检查，防止在获取锁的过程中主窗口已初始化完成
                if config.main_window_ready:
                    signal.emit(*args, **kwargs)
                else:
                    self.pending_signals.append((signal, args, kwargs))

    def emit_pending_signals(self):
        # 主窗口初始化完成后调用，发送所有待发送的信号
        config.main_window_ready = True

        with self._lock:
            for signal, args, kwargs in self.pending_signals:
                signal.emit(*args, **kwargs)
            
            self.pending_signals.clear()

signal_bus = SignalBus()