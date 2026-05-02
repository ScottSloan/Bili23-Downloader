from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtCore import QTimer

from qfluentwidgets import ExpandGroupSettingCard, PushButton, FluentIcon, PushSettingCard, qconfig, ColorDialog, PrimaryPushButton

from .widget import SettingSwitchButton, SettingComboBox, SettingSlider

from util.common import config, ExtendedFluentIcon, Directory, isWin11
from util.thread import GlobalThreadPoolTask

class PersonalizationCard(ExpandGroupSettingCard):
    accentColorChanged = Signal(QColor)

    def __init__(self, main_window, parent = None):
        super().__init__(FluentIcon.PALETTE, self.tr("Personalization"), self.tr("Customize the app theme, colors, and visual effects"), parent)

        self.main_window = main_window

        self.theme_choice = SettingComboBox(config.themeMode, [self.tr("Light"), self.tr("Dark"), self.tr("System default")], parent = self)

        self.accent_color_btn = PushButton(self.tr("Customize…"), self)
        self.accent_color_btn.clicked.connect(self.__showColorDialog)

        self.mica_effect_switch = SettingSwitchButton(config.mica_effect, parent = self)
        self.mica_effect_switch.setChecked(config.get(config.mica_effect))

        self.addGroup("", self.tr("Theme"), self.tr("Select the application theme"), self.theme_choice)
        self.addGroup("", self.tr("Accent Color"), self.tr("Customize the accent color used in the application"), self.accent_color_btn)
        mica_widget = self.addGroup("", self.tr("Mica Effect"), self.tr("Apply translucent Mica effect (Windows 11 only)"), self.mica_effect_switch)

        mica_widget.setEnabled(isWin11())

    def __showColorDialog(self):
        """ show color dialog """
        w = ColorDialog(
            qconfig.get(config.themeColor), self.tr("Choose color"), self.main_window, enableAlpha = True)
        w.colorChanged.connect(self.__onCustomColorChanged)
        w.exec()

    def __onCustomColorChanged(self, color):
        """ custom color changed slot """
        qconfig.set(config.themeColor, color)
        self.accentColorChanged.emit(color)

class DownloadPathSettingCard(PushSettingCard):
    diskSpaceReady = Signal(str, object)

    def __init__(self, parent_window, save = True, parent = None):
        super().__init__(self.tr("Choose folder"), FluentIcon.FOLDER, self.tr("Download Path"), "path", parent)

        self.parent_window = parent_window
        self.save = save
        self.path = ""

        self.set_path(config.get(config.download_path), update_space = False)

        self.diskSpaceReady.connect(self.on_disk_space_ready)
        QTimer.singleShot(0, self.refresh_disk_space)

        self.clicked.connect(self.on_change_download_path)

    def set_path(self, path: str, update_space: bool = True):
        self.path = path

        if update_space:
            self.refresh_disk_space()
        else:
            self.setContent(path)

    def refresh_disk_space(self):
        path = self.path

        def worker():
            self.diskSpaceReady.emit(path, Directory.calc_disk_space(path))

        GlobalThreadPoolTask.run_func(worker)

    def on_disk_space_ready(self, path: str, disk_space_info):
        if path != self.path:
            return

        if disk_space_info:
            self.setContent(
                self.tr("{path} ({free} available)").format(
                    path = self.path,
                    free = disk_space_info.get("free")
                )
            )
        else:
            self.setContent(self.path)
        
    def on_change_download_path(self):
        path = Directory.browse_directory(self.parent_window, self.tr("Choose folder"), config.get(config.download_path))

        if self.save:
            config.set(config.download_path, path)
        
        self.set_path(path)

class PrioritySettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.SETTING, self.tr("Video, Audio, and Codec Priority"), self.tr("Customize download priority settings"), parent)

        self.video_quality_btn = PushButton(self.tr("Customize…"), self)
        self.audio_quality_btn = PushButton(self.tr("Customize…"), self)
        self.video_codec_btn = PushButton(self.tr("Customize…"), self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup(FluentIcon.VIDEO, self.tr("Video Quality Priority"), "", self.video_quality_btn)
        self.addGroup(FluentIcon.MUSIC, self.tr("Audio Quality Priority"), "", self.audio_quality_btn)
        self.addGroup(FluentIcon.CODE, self.tr("Codec Priority"), "", self.video_codec_btn)

class DanmakuSettingCard(ExpandGroupSettingCard):
    def __init__(self, full_mode = True, parent = None):
        super().__init__(ExtendedFluentIcon.COMMENT, self.tr("Danmaku Download Settings"), self.tr("Adjust danmaku download settings"), parent)

        self.download_switch = SettingSwitchButton(config.download_danmaku, parent = self)

        self.type_choice = SettingComboBox(config.danmaku_type, ["xml", "ass", "json"], parent = self)
        self.type_choice.setFixedWidth(120)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Download Danmaku"), "", self.download_switch)
        self.addGroup("", self.tr("Danmaku Format"), "", self.type_choice)

        if full_mode:
            self.custom_style_btn = PushButton(self.tr("Customize…"), self)
            
            self.addGroup("", self.tr("Danmaku Style"), self.tr("Only effective for ASS format danmaku"), self.custom_style_btn)

class SubtitleSettingCard(ExpandGroupSettingCard):
    def __init__(self, full_mode = True, parent = None):
        super().__init__(ExtendedFluentIcon.SUBTITLES, self.tr("Subtitle Download Settings"), self.tr("Adjust subtitle download settings"), parent)

        self.download_switch = SettingSwitchButton(config.download_subtitle, parent = self)

        self.type_choice = SettingComboBox(config.subtitle_type, ["srt", "lrc", "txt", "ass", "json"], parent = self)
        self.type_choice.setFixedWidth(120)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Download Subtitles"), "", self.download_switch)
        self.addGroup("", self.tr("Subtitle Format"), "", self.type_choice)

        if full_mode:
            self.language_btn = PushButton(self.tr("Customize…"), self)
            self.custom_style_btn = PushButton(self.tr("Customize…"), self)

            self.addGroup("", self.tr("Subtitle Language"), "", self.language_btn)
            self.addGroup("", self.tr("Subtitle Style"), self.tr("Only effective for ASS format subtitles"), self.custom_style_btn)

class CoverSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.PHOTO, self.tr("Cover Download Settings"), self.tr("Adjust cover download settings"), parent)

        self.download_switch = SettingSwitchButton(config.download_cover, parent = self)

        self.type_choice = SettingComboBox(config.cover_type, ["jpg", "png", "avif", "webp"], parent = self)
        self.type_choice.setFixedWidth(120)

        self.attach_cover_switch = SettingSwitchButton(config.attach_cover, parent = self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Download Cover"), "", self.download_switch)
        self.addGroup("", self.tr("Cover Format"), "", self.type_choice)
        self.attach_cover_group = self.addGroup("", self.tr("Embed Cover"), self.tr("Embed the downloaded cover into the video file"), self.attach_cover_switch)

        self.attach_cover_group.setEnabled(config.get(config.download_cover) and not self.type_choice.currentText() == "avif")
        self.download_switch.checkedChanged.connect(self.on_toggle_attach_cover)
        self.type_choice.currentIndexChanged.connect(self.on_change_cover_format)

    def on_change_cover_format(self, index: int):
        # avif 格式不支持作为封面嵌入，如果用户选择了 avif 作为封面格式，则禁用嵌入封面选项
        is_avif = index == 2

        if is_avif and self.attach_cover_switch.isChecked():
            self.attach_cover_switch.setChecked(False)

        self.attach_cover_group.setEnabled(not is_avif)

    def on_toggle_attach_cover(self, checked: bool):
        self.attach_cover_group.setEnabled(checked)

        if not checked:
            self.attach_cover_switch.setChecked(False)

class MetadataSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.DOCUMENT, self.tr("Metadata Download Settings"), self.tr("Adjust metadata download settings"), parent)

        self.download_switch = SettingSwitchButton(config.download_metadata, parent = self)

        self.type_choice = SettingComboBox(config.metadata_type, ["nfo", "json"], parent = self)
        self.type_choice.setFixedWidth(120)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Download Metadata"), "", self.download_switch)
        self.addGroup("", self.tr("Metadata Format"), "", self.type_choice)

class NumberSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.NUMBERS, self.tr("Numbering"), self.tr("Configure how the {number} variable is formatted"), parent)

        self.numbering_type_choice = SettingComboBox(
            config.numbering_type,
            [
                self.tr("Start from specified number (per batch)"),
                self.tr("Global sequential numbering"),
                self.tr("Use list order (1, 2, 3…)")
            ],
            parent = self
        )
        self.starting_number_btn = PushButton(self.tr("Customize…"), self)

        self.addGroup(
            "",
            self.tr("Numbering Type"),
            self.tr("Select the source for {number} variable"),
            self.numbering_type_choice
        )
        self.starting_number_group = self.addGroup(
            "",
            self.tr("Starting Number"),
            self.get_starting_number_content(config.get(config.starting_number)),
            self.starting_number_btn
        )
        
        self.numbering_type_choice.currentIndexChanged.connect(lambda index: self.starting_number_group.setEnabled(index == 0))

        self.starting_number_group.setEnabled(self.numbering_type_choice.currentIndex() == 0)

    def on_change_numbering_type(self, type_index: int):
        self.starting_number_group.setEnabled(type_index == 0)

        # 重置当前起始数字，避免在切换编号类型后出现不符合预期的数字
        config.current_starting_number = None

    def set_current_starting_number(self, value: int):
        config.set(config.starting_number, value)

        self.starting_number_group.setContent(self.get_starting_number_content(value))

        config.current_starting_number = None

    def get_starting_number_content(self, value: int):
        return self.tr("Set initial number for per-batch. Current: {current}").format(current = value)

class CDNSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.CLOUD_DOWNLOAD, self.tr("CDN Settings"), self.tr("Adjust CDN settings used for downloading"), parent)

        self.prefer_server_provider_switch = SettingSwitchButton(config.prefer_cdn_server_provider, parent = self)

        self.custom_btn = PushButton(self.tr("Customize…"), self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Prefer Service Provider CDN"), self.tr("Prefer CDN provided by cloud service providers to improve download stability"), self.prefer_server_provider_switch)
        self.addGroup("", self.tr("Customize Service Provider CDN"), self.tr("Customize the list and priority of service provider CDNs"), self.custom_btn)

class ProxySettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.SERVER, self.tr("Proxy Settings"), self.tr("Adjust proxy server settings used for parsing and downloading"), parent)

        self.enable_proxy_switch = SettingSwitchButton(config.proxy_enabled, parent = self)

        self.custom_btn = PushButton(self.tr("Configure…"), self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Use Proxy Server"), "", self.enable_proxy_switch)
        self.addGroup("", self.tr("Configure Proxy Server"), "", self.custom_btn)

class FFmpegSettingCard(ExpandGroupSettingCard):
    def __init__(self, main_window, parent = None):
        super().__init__(FluentIcon.SETTING, self.tr("FFmpeg Settings"), self.tr("Configure FFmpeg used for merging and converting videos"), parent)

        self.main_window = main_window

        self.source_choice = SettingComboBox(config.ffmpeg_source, [self.tr("Bundled (with app)"), self.tr("System PATH"), self.tr("Custom path")], parent = self)
        self.custom_btn = PushButton(self.tr("Browse…"), self)

        self.addGroup("", self.tr("FFmpeg Source"), self.tr("Select the FFmpeg executable to use"), self.source_choice)
        self.custom_group = self.addGroup("", self.tr("Custom FFmpeg Path"), "", self.custom_btn)

        self.custom_group.setEnabled(self.source_choice.currentIndex() == 2)

class DownloadFormatCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.DOCUMENT, self.tr("Download Format"), self.tr("Configure output format settings for downloaded files"), parent)

        self.video_container_choice = SettingComboBox(config.video_container, ["mp4", "mkv"], parent = self)
        self.m4a_to_mp3_switch = SettingSwitchButton(config.m4a_to_mp3, self)

        self.addGroup(FluentIcon.VIDEO, self.tr("Output Container Format"), self.tr("Choose the container format for the final output video file"), self.video_container_choice)
        self.addGroup(FluentIcon.MUSIC, self.tr("Convert M4A to MP3"), self.tr("Only applies when downloading audio-only streams. Disabled if video is also selected."), self.m4a_to_mp3_switch)

class ParsingSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.SEARCH, self.tr("Parsing Settings"), self.tr("Configure clipboard monitoring, parse history, and parse list options"), parent)

        self.monitor_clipboard_switch = SettingSwitchButton(config.monitor_clipboard, parent = self)
        self.parse_history_switch = SettingSwitchButton(config.parse_history, parent = self)

        self.custom_header_btn = PushButton(self.tr("Configure…"), self)

        self.addGroup("", self.tr("Monitor Clipboard"), self.tr("Automatically start parsing when a link is copied"), self.monitor_clipboard_switch)
        self.addGroup("", self.tr("Save Parse History"), self.tr("Save the history of parsed links"), self.parse_history_switch)
        self.addGroup("", self.tr("Parse List Settings"), self.tr("Customize the display and behavior of the parse list"), self.custom_header_btn)

class ConfigFileSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.FILE_SETTINGS, self.tr("Config File"), self.tr("Import or export configuration files"), parent)

        self.import_btn = PushButton(self.tr("Browse..."), self)
        self.import_btn.setMinimumWidth(90)
        self.export_btn = PushButton(self.tr("Browse..."), self)
        self.export_btn.setMinimumWidth(90)
        self.reset_btn = PushButton(self.tr("Reset"), self)
        self.reset_btn.setMinimumWidth(90)
        self.open_dir_btn = PushButton(self.tr("Open"), self)
        self.open_dir_btn.setMinimumWidth(90)

        self.addGroup("", self.tr("Import Config"), self.tr("Import settings from a configuration file"), self.import_btn)
        self.addGroup("", self.tr("Export Config"), self.tr("Export settings to a configuration file"), self.export_btn)
        self.addGroup("", self.tr("Reset Config"), self.tr("Reset all settings to default values"), self.reset_btn)
        self.addGroup("", self.tr("Open Config Directory"), "", self.open_dir_btn)

        self.open_dir_btn.clicked.connect(self.on_open_config_directory)

    def on_open_config_directory(self):
        Directory.open_directory_in_explorer(str(config.file.parent))

class WindowBehaviorSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.APPLICATION_WINDOW, self.tr("Window Behavior"), self.tr("Adjust the behavior of the main window during startup, runtime, and shutdown"), parent)

        self.silent_start_switch = SettingSwitchButton(config.silent_start, parent = self)
        self.stay_on_top_switch = SettingSwitchButton(config.stay_on_top, parent = self)
        self.when_close_action_choice = SettingComboBox(config.when_close_window, [self.tr("Exit the program"), self.tr("Minimize to system tray"), self.tr("Always ask")], parent = self)

        self.addGroup("", self.tr("Silent Start"), self.tr("Start the application without showing the main window"), self.silent_start_switch)
        self.addGroup("", self.tr("Stay on Top"), self.tr("Keep the window always on top of the desktop"), self.stay_on_top_switch)
        self.addGroup("", self.tr("Close the Main Window"), self.tr("Choose the action when closing the main window"), self.when_close_action_choice)

class DownloadHandlingSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.DOWNLOAD, self.tr("Download Handling"), self.tr("Configure download prompts, notifications, and file conflict handling"), parent)

        self.show_download_options_dialog_switch = SettingSwitchButton(config.show_download_options_dialog, parent = self)
        self.show_notification_switch = SettingSwitchButton(config.show_notification, parent = self)
        self.file_conflict_resolution_choice = SettingComboBox(config.file_conflict_resolution, [self.tr("Auto-rename"), self.tr("Overwrite")], parent = self)

        self.addGroup("", self.tr("Show Download Options Dialog"), self.tr("Show a dialog before starting the download to customize settings for this task"), self.show_download_options_dialog_switch)
        self.addGroup("", self.tr("Show Notifications"), self.tr("Show notifications when downloads complete"), self.show_notification_switch)
        self.addGroup("", self.tr("File Conflict Resolution"), self.tr("Choose the action when a file with the same name already exists"), self.file_conflict_resolution_choice)

class DownloadConcurrencySettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.FAST_DOWNLOAD, self.tr("Download Concurrency"), self.tr("Adjust per-task threads, concurrent downloads, and speed limits"), parent)

        self.download_thread_slider = SettingSlider(config.download_thread, self)
        self.download_parallel_slider = SettingSlider(config.download_parallel, self)

        self.download_speed_limit_btn = PushButton(self.tr("Configure…"), self)

        self.addGroup("", self.tr("Number of Threads"), self.tr("Adjust the number of threads used per task (default: 4)"), self.download_thread_slider)
        self.addGroup("", self.tr("Number of Parallel Downloads"), self.tr("Adjust the number of tasks downloaded simultaneously (default: 1)"), self.download_parallel_slider)
        self.addGroup("", self.tr("Speed Limit Settings"), self.tr("Configure speed limit settings for downloads"), self.download_speed_limit_btn)

class CheckUpdateSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.UPDATE, self.tr("Check for Updates"), self.tr("Check if a new version is available"), parent)

        self.check_now_btn = PrimaryPushButton(self.tr("Check Now"), self)
        self.include_prerelease_switch = SettingSwitchButton(config.include_prerelease, parent = self)

        self.card.addWidget(self.check_now_btn)

        self.addGroup("", self.tr("Include Prerelease Versions"), self.tr("Include prerelease versions in update checks (may be unstable)"), self.include_prerelease_switch)