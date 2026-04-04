from qfluentwidgets import ExpandGroupSettingCard, PushButton, FluentIcon, PushSettingCard

from gui.component.setting.widget import SettingSwitchButton, SettingComboBox

from util.common import config, ExtendedFluentIcon, Directory

class DownloadPathSettingCard(PushSettingCard):
    def __init__(self, parent_window, save = True, parent = None):
        super().__init__(self.tr("Choose folder"), FluentIcon.FOLDER, self.tr("Download Path"), "path", parent)

        self.parent_window = parent_window
        self.save = save
        self.path = ""

        self.set_path(config.get(config.download_path))

        self.clicked.connect(self.on_change_download_path)

    def set_path(self, path: str):
        self.path = path
        disk_space_info = Directory.calc_disk_space(path)

        self.setContent(
            self.tr("{path} ({free} available)").format(
                path = path,
                free = disk_space_info.get("free") if disk_space_info else "null"
            ))
        
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
        self.attach_cover_group = self.addGroup("", self.tr("Embed cover"), self.tr("Embed the downloaded cover into the video file"), self.attach_cover_switch)

        self.attach_cover_group.setEnabled(config.get(config.download_cover))
        self.download_switch.checkedChanged.connect(self.on_toggle_attach_cover)

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
            self.tr("Numbering type"),
            self.tr("Select the source for {number} variable"),
            self.numbering_type_choice
        )
        self.starting_number_group = self.addGroup(
            "",
            self.tr("Starting number"),
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

        self.addGroup("", self.tr("FFmpeg source"), self.tr("Select the FFmpeg executable to use"), self.source_choice)
        self.custom_group = self.addGroup("", self.tr("Custom FFmpeg path"), "", self.custom_btn)

        self.custom_group.setEnabled(self.source_choice.currentIndex() == 2)

class DownloadFormatCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.DOCUMENT, self.tr("Download Format"), self.tr("Configure output format settings for downloaded files"), parent)

        self.m4a_to_mp3_switch = SettingSwitchButton(config.m4a_to_mp3, self)

        self.addGroup(FluentIcon.MUSIC, self.tr("Convert M4A to MP3"), self.tr("Only applies when downloading audio-only streams. Disabled if video is also selected."), self.m4a_to_mp3_switch)

class ParseListSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.LIST, self.tr("Parse List"), self.tr("Adjust settings for the parse list"), parent)

        self.auto_check_all_switch = SettingSwitchButton(config.auto_check_all, parent = self)

        self.custom_header_btn = PushButton(self.tr("Customize…"), self)

        self.addGroup("", self.tr("Auto-select All"), self.tr("Automatically select all items after parsing"), self.auto_check_all_switch)
        self.addGroup("", self.tr("Customize Displayed Columns"), self.tr("Customize the columns displayed in the parse list and their order"), self.custom_header_btn)

class ConfigFileSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.FILE_SETTINGS, self.tr("Config File"), self.tr("Import or export configuration files"), parent)

        self.import_btn = PushButton(self.tr("Browse..."), self)
        self.export_btn = PushButton(self.tr("Browse..."), self)
        self.open_dir_btn = PushButton(self.tr("Open"), self)

        self.addGroup("", self.tr("Import Config"), self.tr("Import settings from a configuration file"), self.import_btn)
        self.addGroup("", self.tr("Export Config"), self.tr("Export settings to a configuration file"), self.export_btn)
        self.addGroup("", self.tr("Open Config Directory"), "", self.open_dir_btn)

        self.open_dir_btn.clicked.connect(self.on_open_config_directory)

    def on_open_config_directory(self):
        Directory.open_directory_in_explorer(str(config.file.parent))

class SpeedLimitSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.FAST_DOWNLOAD, self.tr("Speed Limit"), self.tr("Configure download speed limit"), parent)

        self.enable_speed_limit_switch = SettingSwitchButton(config.speed_limit_enabled, parent = self)
        self.speed_limit_rate_btn = PushButton(self.tr("Customize…"), parent = self)

        self.addGroup("", self.tr("Enable Speed Limit"), self.tr("Limit the speed of each download task"), self.enable_speed_limit_switch)
        self.speed_limit_rate_group = self.addGroup("", self.tr("Speed Limit Rate"), "", self.speed_limit_rate_btn)

        self.set_current_speed_limit_rate(config.get(config.speed_limit_rate))

        self.speed_limit_rate_group.setEnabled(config.get(config.speed_limit_enabled))
        self.enable_speed_limit_switch.checkedChanged.connect(lambda checked: self.speed_limit_rate_group.setEnabled(checked))

    def set_current_speed_limit_rate(self, rate: int):
        self.speed_limit_rate_group.setContent(self.tr("Current rate: {rate} MB/s").format(rate = rate))