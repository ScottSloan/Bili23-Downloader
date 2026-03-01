from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog
from PySide6.QtCore import Qt

from qfluentwidgets import (
    ScrollArea, SettingCardGroup, OptionsSettingCard, CustomColorSettingCard, PushSettingCard, RangeSettingCard, SwitchSettingCard,
    ComboBoxSettingCard, PrimaryPushSettingCard, MSFluentWindow, MessageBox, FluentIcon, setTheme, setThemeColor
)

from gui.component.setting.card import (
    PrioritySettingCard, DanmakuSettingCard, SubtitleSettingCard, CoverSettingCard, MetadataSettingCard, CDNSettingCard, ProxySettingCard,
    NamingConventionSettingCard, FFmpegSettingCard, NumberSettingCard, DownloadFormatCard, DownloadPathSettingCard
)
from gui.dialog.setting import (
    PriorityDialog, UserAgentDialog, ProxyDialog, CDNServerDialog, SubtitlesLanguageDialog, SubtitlesStyleDialog, DanmakuStyleDialog,
    StartingNumberDialog
)

from util.common.data import video_quality_map, audio_quality_map, video_codec_map
from util.common.enum import ToastNotificationCategory
from util.common.icon import ExtendedFluentIcon
from util.common.style_sheet import StyleSheet
from util.common.signal_bus import signal_bus
from util.common.translator import Translator
from util.common.config import config

class SettingInterface(ScrollArea):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.main_window: MSFluentWindow = parent

        self.setObjectName("SettingInterface")

        self.init_UI()

    def init_UI(self):
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")

        self.expand_layout = QVBoxLayout(self.scroll_widget)

        # Interface
        self.interface_group = SettingCardGroup(self.tr("Interface"), self)

        self.theme_card = OptionsSettingCard(config.themeMode, FluentIcon.BRUSH, self.tr("Theme"), self.tr("Adjust the appearance of the application"), [self.tr("Light"), self.tr("Dark"), self.tr("Follow system setting")], self)
        self.theme_color_card = CustomColorSettingCard(config.themeColor, FluentIcon.PALETTE, self.tr("Theme color"), self.tr("Adjust the theme color of the application"), self)
        self.language_card = ComboBoxSettingCard(config.language, FluentIcon.LANGUAGE, self.tr("Language"), self.tr("Choose the display language of the application"), ["简体中文", "繁體中文", "English", self.tr("Follow system setting")], self)

        # Behavior
        self.behavior_group = SettingCardGroup(self.tr("Behavior"), self)

        self.stay_on_top_card = SwitchSettingCard(ExtendedFluentIcon.PIN, self.tr("Stay on top"), self.tr("Keep the window always on top of the desktop"), config.stay_on_top, self)
        self.listen_clipboard_card = SwitchSettingCard(ExtendedFluentIcon.CLIPBOARD, self.tr("Listen to clipboard"), self.tr("Automatically start parsing when a link is copied"), config.listen_clipboard, self)
        self.show_download_options_dialog_card = SwitchSettingCard(ExtendedFluentIcon.OPTIONS, self.tr("Show download options dialog"), self.tr("Show a dialog before starting the download to customize settings for this task"), config.show_download_options_dialog, self)
        self.when_close_window_card = ComboBoxSettingCard(config.when_close_window, ExtendedFluentIcon.EXIT, self.tr("When closing window"), self.tr("Choose the action when closing the application window"), [self.tr("Exit application"), self.tr("Minimize to tray"), self.tr("Always ask")], self)

        # Download
        self.download_group = SettingCardGroup(self.tr("Download"), self)

        self.download_path_card = DownloadPathSettingCard(self.main_window, save = True, parent = self)
        self.download_thread_card = RangeSettingCard(config.download_thread, ExtendedFluentIcon.FAST_DOWNLOAD, self.tr("Number of threads"), self.tr("Adjust the number of threads used per task (default: 4)"), self)
        self.download_parallel_card = RangeSettingCard(config.download_parallel, FluentIcon.DOWNLOAD, self.tr("Number of parallel downloads"), self.tr("Adjust the number of tasks downloaded simultaneously (default: 1)"), self)
        self.show_notification_card = SwitchSettingCard(FluentIcon.RINGER, self.tr("Show notifications"), self.tr("Show notifications when downloads complete or fail"), config.show_notification, self)
        self.priority_setting_card = PrioritySettingCard(self)
        self.download_format_card = DownloadFormatCard(self)

        # Additional
        self.additional_group = SettingCardGroup(self.tr("Danmaku, Subtitles, Cover, and Metadata"), self)

        self.danmaku_setting_card = DanmakuSettingCard(parent = self)
        self.subtitle_setting_card = SubtitleSettingCard(parent = self)
        self.cover_setting_card = CoverSettingCard(parent = self)
        self.metadata_setting_card = MetadataSettingCard(parent = self)

        # File Naming
        self.file_naming_group = SettingCardGroup(self.tr("File Naming"), self)

        self.naming_convention_setting_card = NamingConventionSettingCard(self.main_window, self)
        self.numbering_setting_card = NumberSettingCard(self)

        # Advanced
        self.advanced_group = SettingCardGroup(self.tr("Advanced"), self)

        self.cdn_card = CDNSettingCard(self)
        self.ffmpeg_card = FFmpegSettingCard(self.main_window, self)
        self.proxy_card = ProxySettingCard(self)
        self.user_agent_card = PushSettingCard(self.tr("Customize…"), FluentIcon.GLOBE, "User-Agent", self.tr("Customize the User-Agent used for parsing and downloading"), self)

        # Software Update
        self.update_group = SettingCardGroup(self.tr("Updates"), self)

        self.check_update_card = PrimaryPushSettingCard(self.tr("Check for updates"), FluentIcon.UPDATE, self.tr("Check for updates"), self.tr("Check if a new version is available. Current version: {app_version}").format(app_version = config.app_version), self)

        # Interface
        self.interface_group.addSettingCard(self.theme_card)
        self.interface_group.addSettingCard(self.theme_color_card)
        self.interface_group.addSettingCard(self.language_card)

        # Behavior
        self.behavior_group.addSettingCard(self.stay_on_top_card)
        self.behavior_group.addSettingCard(self.listen_clipboard_card)
        self.behavior_group.addSettingCard(self.show_download_options_dialog_card)
        self.behavior_group.addSettingCard(self.when_close_window_card)

        # Download
        self.download_group.addSettingCard(self.download_path_card)
        self.download_group.addSettingCard(self.download_thread_card)
        self.download_group.addSettingCard(self.download_parallel_card)
        self.download_group.addSettingCard(self.show_notification_card)
        self.download_group.addSettingCard(self.priority_setting_card)
        self.download_group.addSettingCard(self.download_format_card)

        # Additional
        self.additional_group.addSettingCard(self.danmaku_setting_card)
        self.additional_group.addSettingCard(self.subtitle_setting_card)
        self.additional_group.addSettingCard(self.cover_setting_card)
        self.additional_group.addSettingCard(self.metadata_setting_card)

        # File Naming Convention
        self.file_naming_group.addSettingCard(self.naming_convention_setting_card)
        self.file_naming_group.addSettingCard(self.numbering_setting_card)

        # Advanced
        self.advanced_group.addSettingCard(self.cdn_card)
        self.advanced_group.addSettingCard(self.ffmpeg_card)
        self.advanced_group.addSettingCard(self.proxy_card)
        self.advanced_group.addSettingCard(self.user_agent_card)

        # Software Update
        self.update_group.addSettingCard(self.check_update_card)

        self.expand_layout.setSpacing(28)
        self.expand_layout.setContentsMargins(30, 10, 30, 0)
        self.expand_layout.addWidget(self.interface_group)
        self.expand_layout.addWidget(self.behavior_group)
        self.expand_layout.addWidget(self.download_group)
        self.expand_layout.addWidget(self.additional_group)
        self.expand_layout.addWidget(self.file_naming_group)
        self.expand_layout.addWidget(self.advanced_group)
        self.expand_layout.addWidget(self.update_group)
        self.expand_layout.addSpacing(20)
        self.expand_layout.addStretch(1)

        self.resize(500, 200)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidget(self.scroll_widget)
        self.setWidgetResizable(True)

        StyleSheet.SETTING_INTERFACE.apply(self)

        self.connect_signals()

    def connect_signals(self):
        # Interface
        config.themeChanged.connect(setTheme)
        self.theme_color_card.colorChanged.connect(lambda color: setThemeColor(color))
        config.appRestartSig.connect(self.show_restart_message)

        # Behavior
        self.stay_on_top_card.checkedChanged.connect(self.on_change_stay_on_top)

        # Download
        self.priority_setting_card.video_quality_btn.clicked.connect(self.on_adjust_video_quality_priority)
        self.priority_setting_card.audio_quality_btn.clicked.connect(self.on_adjust_audio_quality_priority)
        self.priority_setting_card.video_codec_btn.clicked.connect(self.on_adjust_video_codec_priority)
        self.danmaku_setting_card.custom_style_btn.clicked.connect(self.on_custom_danmaku_style)
        self.subtitle_setting_card.language_btn.clicked.connect(self.on_custom_subtitles_language)
        self.subtitle_setting_card.custom_style_btn.clicked.connect(self.on_custom_subtitles_style)

        # File Naming
        self.numbering_setting_card.starting_number_btn.clicked.connect(self.on_custom_starting_number)

        # Advanced
        self.cdn_card.custom_btn.clicked.connect(self.on_custom_cdn_server_list)
        self.ffmpeg_card.source_choice.currentIndexChanged.connect(self.on_change_ffmpeg_source)
        self.ffmpeg_card.custom_btn.clicked.connect(self.on_change_ffmpeg_path)
        self.proxy_card.custom_btn.clicked.connect(self.on_custom_proxy)
        self.user_agent_card.clicked.connect(self.on_custom_user_agent)

    def on_change_stay_on_top(self, checked: bool):
        self.main_window.setStayOnTop(checked)

    def on_adjust_video_quality_priority(self):
        map_reversed = {v: Translator.VIDEO_QUALITY(k) for k, v in video_quality_map.items()}

        dialog = PriorityDialog(map_reversed, config.get(config.video_quality_priority), self.main_window)

        if dialog.exec():
            config.set(config.video_quality_priority, dialog.get_config_value())

    def on_adjust_audio_quality_priority(self):
        map_reversed = {v: Translator.AUDIO_QUALITY(k) for k, v in audio_quality_map.items()}

        dialog = PriorityDialog(map_reversed, config.get(config.audio_quality_priority), self.main_window)

        if dialog.exec():
            config.set(config.audio_quality_priority, dialog.get_config_value())

    def on_adjust_video_codec_priority(self):
        map_reversed = {v: k for k, v in video_codec_map.items()}

        dialog = PriorityDialog(map_reversed, config.get(config.video_codec_priority), self.main_window)

        if dialog.exec():
            config.set(config.video_codec_priority, dialog.get_config_value())

    def on_custom_danmaku_style(self):
        dialog = DanmakuStyleDialog(self.main_window)
        dialog.exec()

    def on_custom_subtitles_language(self):
        dialog = SubtitlesLanguageDialog(self.main_window)
        dialog.exec()

    def on_custom_subtitles_style(self):
        dialog = SubtitlesStyleDialog(self.main_window)
        dialog.exec()

    def on_custom_starting_number(self):
        dialog = StartingNumberDialog(self)

        if dialog.exec():
            self.numbering_setting_card.set_current_starting_number(dialog.starting_number_spin.value())

    def on_custom_cdn_server_list(self):
        dialog = CDNServerDialog(self.main_window)
        dialog.exec()

    def on_change_ffmpeg_source(self, index: int):
        if index == 0 and not config.bundle_ffmpeg_exist:
            dialog = MessageBox(
                self.tr("Bundled FFmpeg not found"),
                self.tr("The bundled FFmpeg executable is missing. Please switch to 'System PATH' or specify a custom path."),
                self.main_window
            )

            dialog.hideCancelButton()

            if dialog.exec():
                self.ffmpeg_card.source_choice.setCurrentIndex(1)

        self.ffmpeg_card.custom_group.setEnabled(index == 2)

    def on_change_ffmpeg_path(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select FFmpeg executable"),
            config.get(config.custom_ffmpeg_path),
            self.tr("FFmpeg executable ({executable})").format(executable = config.ffmpeg_executable)
        )
        
        if not file_path:
            return
        
        config.set(config.custom_ffmpeg_path, file_path)
        self.ffmpeg_card.custom_group.setContent(file_path)

    def on_custom_proxy(self):
        dialog = ProxyDialog(self.main_window)
        dialog.exec()

    def on_custom_user_agent(self):
        dialog = UserAgentDialog(self.main_window)
        dialog.exec()

    def show_restart_message(self):
        signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Configuration takes effect after restart"))
