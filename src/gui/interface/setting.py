from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog
from PySide6.QtCore import Qt

from qfluentwidgets import (
    ScrollArea, SettingCardGroup, PushSettingCard, ComboBoxSettingCard, MSFluentWindow, MessageBox, FluentIcon, 
    setTheme, setThemeColor
)

from gui.component.setting import (
    PrioritySettingCard, DanmakuSettingCard, SubtitleSettingCard, CoverSettingCard, MetadataSettingCard, CDNSettingCard, ProxySettingCard,
    FFmpegSettingCard, NumberSettingCard, DownloadFormatCard, DownloadPathSettingCard, ParsingSettingCard, WindowBehaviorSettingCard,
    DownloadHandlingSettingCard, DownloadConcurrencySettingCard, PersonalizationCard, CheckUpdateSettingCard, OtherAdvancedSettingCard
)

from util.common.data import video_quality_map, audio_quality_map, video_codec_map
from util.common.enum import ToastNotificationCategory
from util.common.style_sheet import StyleSheet
from util.common.signal_bus import signal_bus
from util.common.translator import Translator
from util.common.config import config

from pathlib import Path

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

        self.personalization_card = PersonalizationCard(self.main_window, self)
        self.scaling_card = ComboBoxSettingCard(config.display_scaling, FluentIcon.ZOOM, self.tr("Display Scaling"), self.tr("Adjust the scaling of the application interface"), ["100%", "125%", "150%", "175%", "200%", self.tr("System default")], self)
        self.language_card = ComboBoxSettingCard(config.language, FluentIcon.LANGUAGE, self.tr("Language"), self.tr("Choose the display language of the application"), ["简体中文", "繁體中文", "English", self.tr("System default")], self)

        # Behavior
        self.behavior_group = SettingCardGroup(self.tr("Behavior"), self)

        self.parse_list_card = ParsingSettingCard(self)
        self.window_behavior_group = WindowBehaviorSettingCard(self)
        self.download_handling_card = DownloadHandlingSettingCard(self.main_window, parent = self)
        
        # Download
        self.download_group = SettingCardGroup(self.tr("Download"), self)

        self.download_path_card = DownloadPathSettingCard(self.main_window, save = True, parent = self)
        self.download_currency_card = DownloadConcurrencySettingCard(self)
        self.priority_setting_card = PrioritySettingCard(self.main_window, parent = self)
        self.download_format_card = DownloadFormatCard(self)

        # Additional
        self.additional_group = SettingCardGroup(self.tr("Danmaku, Subtitles, Cover, and Metadata"), self)

        self.danmaku_setting_card = DanmakuSettingCard(parent = self)
        self.subtitle_setting_card = SubtitleSettingCard(parent = self)
        self.cover_setting_card = CoverSettingCard(parent = self)
        self.metadata_setting_card = MetadataSettingCard(parent = self)

        # File Naming
        self.file_naming_group = SettingCardGroup(self.tr("File naming"), self)

        self.naming_convention_setting_card = PushSettingCard(self.tr("Customize…"), FluentIcon.DOCUMENT, self.tr("Naming Convention"), self.tr("Customize the naming convention for downloaded files"), self)
        self.numbering_setting_card = NumberSettingCard(self.main_window, self)

        # Advanced
        self.advanced_group = SettingCardGroup(self.tr("Advanced"), self)

        self.cdn_card = CDNSettingCard(self)
        self.ffmpeg_card = FFmpegSettingCard(self.main_window, self)
        self.proxy_card = ProxySettingCard(self)
        self.log_card = PushSettingCard(self.tr("View Logs"), FluentIcon.BOOK_SHELF, self.tr("Logs"), self.tr("View application logs"), self)
        self.other_card = OtherAdvancedSettingCard(self.main_window, self)

        # Software Update
        self.update_group = SettingCardGroup(self.tr("Updates"), self)

        self.check_update_card = CheckUpdateSettingCard(self)

        # Interface
        self.interface_group.addSettingCard(self.personalization_card)
        self.interface_group.addSettingCard(self.scaling_card)
        self.interface_group.addSettingCard(self.language_card)

        # Behavior
        self.behavior_group.addSettingCard(self.parse_list_card)
        self.behavior_group.addSettingCard(self.window_behavior_group)
        self.behavior_group.addSettingCard(self.download_handling_card)

        # Download
        self.download_group.addSettingCard(self.download_path_card)
        self.download_group.addSettingCard(self.download_currency_card)
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
        self.advanced_group.addSettingCard(self.log_card)
        self.advanced_group.addSettingCard(self.other_card)

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
        config.appRestartSig.connect(self.show_restart_message)
        self.personalization_card.accentColorChanged.connect(setThemeColor)
        self.personalization_card.mica_effect_switch.checkedChanged.connect(signal_bus.interface.mica_effect_changed)

        # Behavior
        self.parse_list_card.custom_parse_list_btn.clicked.connect(self.on_custom_parse_list_column)
        self.parse_list_card.custom_monitor_clipboard_btn.clicked.connect(self.on_custom_monitor_clipboard)
        self.parse_list_card.custom_auto_select_btn.clicked.connect(self.on_custom_auto_select)
        self.window_behavior_group.stay_on_top_switch.checkedChanged.connect(self.on_change_stay_on_top)

        # Download
        self.download_currency_card.download_speed_limit_btn.clicked.connect(self.on_custom_speed_limit_settings)
        self.priority_setting_card.video_quality_btn.clicked.connect(self.on_adjust_video_quality_priority)
        self.priority_setting_card.audio_quality_btn.clicked.connect(self.on_adjust_audio_quality_priority)
        self.priority_setting_card.video_codec_btn.clicked.connect(self.on_adjust_video_codec_priority)
        self.danmaku_setting_card.custom_style_btn.clicked.connect(self.on_custom_danmaku_style)
        self.subtitle_setting_card.language_btn.clicked.connect(self.on_custom_subtitles_language)
        self.subtitle_setting_card.custom_style_btn.clicked.connect(self.on_custom_subtitles_style)

        # File Naming
        self.naming_convention_setting_card.clicked.connect(self.on_custom_naming_rule)

        # Advanced
        self.cdn_card.custom_btn.clicked.connect(self.on_custom_cdn_server_list)
        self.ffmpeg_card.source_choice.currentIndexChanged.connect(self.on_change_ffmpeg_source)
        self.ffmpeg_card.custom_btn.clicked.connect(self.on_change_ffmpeg_path)
        self.proxy_card.custom_btn.clicked.connect(self.on_custom_proxy)
        self.log_card.clicked.connect(self.on_view_logs)

        # Update
        self.check_update_card.check_now_btn.clicked.connect(self.on_check_update)

    def on_custom_parse_list_column(self):
        from ..dialog.setting.parse_list import ParseListSettingsDialog

        dialog = ParseListSettingsDialog(self.main_window)

        if dialog.exec():
            self.main_window.parse_interface.parse_list.setAlternatingRowColors(config.get(config.parse_list_alternate_row_color))

    def on_custom_monitor_clipboard(self):
        from ..dialog.setting.monitor_clipboard import MonitorClipboardDialog

        dialog = MonitorClipboardDialog(self.main_window)
        dialog.exec()

    def on_custom_auto_select(self):
        from ..dialog.setting.auto_select import AutoSelectDialog

        dialog = AutoSelectDialog(self.main_window)
        dialog.exec()

    def on_change_stay_on_top(self, checked: bool):
        self.main_window.setStayOnTop(checked)

    def on_custom_speed_limit_settings(self):
        from ..dialog.setting.speed_limit import SpeedLimitSettingDialog

        dialog = SpeedLimitSettingDialog(self.main_window)
        dialog.exec()

    def on_adjust_video_quality_priority(self):
        from ..dialog.setting.priority import PriorityDialog

        map_reversed = {v: Translator.VIDEO_QUALITY(k) for k, v in video_quality_map.items()}

        dialog = PriorityDialog(map_reversed, config.get(config.video_quality_priority), self.main_window)

        if dialog.exec():
            config.set(config.video_quality_priority, dialog.config_value)

    def on_adjust_audio_quality_priority(self):
        from ..dialog.setting.priority import PriorityDialog

        map_reversed = {v: Translator.AUDIO_QUALITY(k) for k, v in audio_quality_map.items()}

        dialog = PriorityDialog(map_reversed, config.get(config.audio_quality_priority), self.main_window)

        if dialog.exec():
            config.set(config.audio_quality_priority, dialog.config_value)

    def on_adjust_video_codec_priority(self):
        from ..dialog.setting.priority import PriorityDialog

        map_reversed = {v: k for k, v in video_codec_map.items()}

        dialog = PriorityDialog(map_reversed, config.get(config.video_codec_priority), self.main_window)

        if dialog.exec():
            config.set(config.video_codec_priority, dialog.config_value)

    def on_custom_danmaku_style(self):
        from ..dialog.setting.danmaku_style import DanmakuStyleDialog

        dialog = DanmakuStyleDialog(self.main_window)
        dialog.exec()

    def on_custom_subtitles_language(self):
        from ..dialog.setting.subtitles_language import SubtitlesLanguageDialog

        dialog = SubtitlesLanguageDialog(self.main_window)
        dialog.exec()

    def on_custom_subtitles_style(self):
        from ..dialog.setting.subtitles_style import SubtitlesStyleDialog

        dialog = SubtitlesStyleDialog(self.main_window)
        dialog.exec()

    def on_custom_naming_rule(self):
        from ..dialog.setting.rule_list import RuleListDialog

        dialog = RuleListDialog(self.main_window)
        dialog.exec()

    def on_custom_cdn_server_list(self):
        from ..dialog.setting.cdn_server import CDNServerDialog

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
        from ..dialog.setting.proxy import ProxyDialog

        dialog = ProxyDialog(self.main_window)
        dialog.exec()

    def on_view_logs(self):
        from ..dialog.log import LogViewerDialog

        dialog = LogViewerDialog(self.main_window)
        dialog.show()

    def on_check_update(self):
        signal_bus.update.check.emit(True)

    def show_restart_message(self):
        signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Configuration takes effect after restart"))
