from .config import config
from .event import Event

from threading import Lock

class SignalBus:
    """
    跨层通信的主干

    util/ 层不直接引用 GUI，一律通过这里通知界面。

    2026-09 由 Qt Signal 换成纯 Python 的 Event（见 event.py），调用形态不变：
    connect / disconnect / emit 三个方法与原来一致，因此调用方无需改动。
    回调落在哪个线程由 util/thread/dispatch 决定 —— 桌面侧投递回 GUI 线程，
    服务端侧推进事件队列。
    """
    class ToastNotification:
        def __init__(self):
            # 用于在 MainWindow 中显示 Toast 通知
            # (ToastNotificationCategory, title: str, content: str)
            self.show = Event("toast.show")

            self.show_long_message = Event("toast.show_long_message")

            self.sys_show = Event("toast.sys_show")

    class Parse:
        def __init__(self):
            # (title: str, category_name: str, root_node, current_episode_data)
            self.update_parse_list = Event("parse.update_parse_list")
            # (category_name: str, count: int)
            self.update_parse_list_count = Event("parse.update_parse_list_count")

            # 自动解析、互动视频探查等场景下，向已有的解析列表追加节点。
            # 解析线程不得直接改动解析列表所使用的树，只能通过本事件把新节点交给 GUI 线程挂载
            self.append_parse_list_nodes = Event("parse.append_parse_list_nodes")

            # 按顺序尝试的媒体信息预览候选项。首选项取不到媒体信息（多为充电专属、付费等
            # 无权限的视频）时自动换下一个，全部失败才提示用户。
            # 用户手动指定某一项时只传该项，失败即提示
            # (candidates: list, show_toast: bool)
            self.preview_init = Event("parse.preview_init")
            self.preview_finish = Event("parse.preview_finish")

            # (quality_id: int, codec_id: int, callback)
            self.query_video_info = Event("parse.query_video_info")
            # (quality_id: int, callback)
            self.query_audio_info = Event("parse.query_audio_info")

            self.update_column_settings = Event("parse.update_column_settings")
            self.update_preview_info = Event("parse.update_preview_info")

            # (url: str)
            self.parse_url = Event("parse.parse_url")

            # (keyword: str)
            self.search_keyword = Event("parse.search_keyword")

            # (info: dict)
            self.show_interactive_video_dialog = Event("parse.show_interactive_video_dialog")

    class Download:
        def __init__(self):
            # 第三个参数为本次任务的下载选项覆盖，传 None 表示全部沿用全局设置
            # (episode_list: list, show_toast: bool, options: dict | None)
            self.create_task = Event("download.create_task")

            self.show_duplicate_download_dialog = Event("download.show_duplicate_download_dialog")
            # (task_title: str)
            self.show_skip_duplicate_download_toast = Event("download.show_skip_duplicate_download_toast")

            # (task_info_list: list)
            self.add_to_downloading_list = Event("download.add_to_downloading_list")
            self.auto_manage_concurrent_downloads = Event("download.auto_manage_concurrent_downloads")
            self.add_to_completed_list = Event("download.add_to_completed_list")

            self.remove_from_downloading_list = Event("download.remove_from_downloading_list")
            self.remove_from_completed_list = Event("download.remove_from_completed_list")

            # (sort_by: str, ascending: bool)
            self.sort_downloading_list = Event("download.sort_downloading_list")
            self.sort_completed_list = Event("download.sort_completed_list")

            # (count: int)
            self.update_downloading_count = Event("download.update_downloading_count")
            self.update_downloading_item = Event("download.update_downloading_item")

            self.start_next_task = Event("download.start_next_task")

    class Login:
        def __init__(self):
            # 用于登录相关的事件
            self.start_server = Event("login.start_server")
            self.stop_server = Event("login.stop_server")

            self.send_sms = Event("login.send_sms")

            # (pixmap | bytes)
            self.update_avatar = Event("login.update_avatar")

    class Update:
        def __init__(self):
            # (silent: bool)
            self.check = Event("update.check")
            # (info: dict)
            self.show_dialog = Event("update.show_dialog")

    class Interface:
        def __init__(self):
            # (enabled: bool)
            self.mica_effect_changed = Event("interface.mica_effect_changed")

    def __init__(self):
        self.toast = self.ToastNotification()
        self.parse = self.Parse()
        self.download = self.Download()
        self.login = self.Login()
        self.update = self.Update()
        self.interface = self.Interface()

        self.pending_signals = []  # 存储在主窗口初始化完成前发出的事件，格式为 (event, args, kwargs)

        self._lock = Lock() # 用于保护待发送列表的线程锁

    def emit_signal(self, signal, *args, **kwargs):
        if config.main_window_ready:
            # 初始化完成，直接发送
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
        # 主窗口初始化完成后调用，发送所有待发送的事件
        config.main_window_ready = True

        with self._lock:
            for signal, args, kwargs in self.pending_signals:
                signal.emit(*args, **kwargs)

            self.pending_signals.clear()

signal_bus = SignalBus()
