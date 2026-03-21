from PySide6.QtCore import QTimer

from qfluentwidgets import ExpandGroupSettingCard, PushButton, MessageBox, FluentIcon, PushSettingCard
from qfluentwidgets.components.settings.expand_setting_card import GroupWidget

from gui.component.setting.widget import SettingSwitchButton, SettingComboBox, EntryItemWidget
from gui.dialog.setting.edit_convention import EditConventionDialog

from util.common.data import reversed_convention_type_map
from util.common.icon import ExtendedFluentIcon
from util.common.translator import Translator
from util.common.config import config
from util.common.io import Directory

from uuid import uuid4

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
        self.addGroup(FluentIcon.VIDEO, self.tr("Codec Priority"), "", self.video_codec_btn)

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

        self.type_choice = SettingComboBox(config.subtitle_type, ["srt", "lrc", "ass", "json"], parent = self)
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

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Download Cover"), "", self.download_switch)
        self.addGroup("", self.tr("Cover Format"), "", self.type_choice)

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

class NamingConventionSettingCard(ExpandGroupSettingCard):
    def __init__(self, main_window, parent = None):
        super().__init__(FluentIcon.DOCUMENT, self.tr("Naming Convention"), self.tr("Customize the naming convention for downloaded files"), parent = parent)

        self.main_window = main_window
        self.rule_list = []

        self.add_btn = PushButton(self.tr("Add Rule"), self)
        self.add_btn.clicked.connect(self.on_add_item)

        self.addWidget(self.add_btn)

        QTimer.singleShot(300, self.init_data)

    def init_data(self):
        rule_list = config.get(config.naming_rule_list).copy()

        for entry in rule_list:
            type_key = reversed_convention_type_map.get(entry.get("type"))
            type_str = Translator.CONVENTION_TYPE(type_key)

            self.add_item(entry, type_str)

        self.rule_list = rule_list.copy()

    def on_add_item(self):
        initial_data = {
            "id": str(uuid4()),
            "name": "",
            "type": 11,
            "rule": "",
            "default": False
        }

        dialog = EditConventionDialog(initial_data, self.main_window)

        if dialog.exec():
            rule_data = dialog.rule_data.copy()

            self.add_item(rule_data, dialog.type_str)

            if not self.isExpand:
                QTimer.singleShot(0, self.toggleExpand)

            config.set(config.naming_rule_list, self.rule_list)

    def on_edit_item(self, id: dict, group_widget: GroupWidget):
        dialog = EditConventionDialog(self.find_data(id), self.main_window)

        if dialog.exec():
            rule_data = dialog.rule_data.copy()

            self.update_data(rule_data)

            group_widget.titleLabel.setText(rule_data.get("name"))

            config.set(config.naming_rule_list, self.rule_list)

    def on_delete_item(self, id: dict, group_widget: GroupWidget):
        rule_data = self.find_data(id)

        if rule_data.get("default"):
            dialog = MessageBox(self.tr("Cannot delete default rule"), self.tr("Only non-default naming rules can be deleted."), self.main_window)
            dialog.hideCancelButton()
            
            dialog.exec()

            return
        
        dialog = MessageBox(self.tr("Delete Naming Rule"), self.tr("Are you sure you want to delete this naming rule?"), self.main_window)

        if dialog.exec():
            self.removeGroupWidget(group_widget)
            self.remove_data(id)

            group_widget.hide()
            group_widget.deleteLater()

            config.set(config.naming_rule_list, self.rule_list)

    def find_data(self, id: str):
        for entry in self.rule_list.copy():
            if entry.get("id") == id:
                return entry
            
    def update_data(self, data: dict):
        for entry in self.rule_list:
            if entry.get("id") == data.get("id"):
                entry = data

                break

        self.update_default(data.get("id"), entry.get("type"))

    def remove_data(self, id: str):
        for entry in self.rule_list:
            if entry.get("id") == id:
                self.rule_list.remove(entry)

                break

    def update_default(self, id: str, type: int):
        for entry in self.rule_list:
            if entry.get("type") == type:
                if entry.get("id") == id:
                    entry["default"] = True
                else:
                    entry["default"] = False

    def add_item(self, rule_data: dict, type_str: str):
        entry_widget = EntryItemWidget(self)
        name_key = rule_data.get("name")

        default_rule_names = Translator.DEFAULT_RULE_NAMES()

        if name_key in default_rule_names.keys():
            rule_data["name"] = default_rule_names.get(name_key)

        group_widget = self.addGroup("", rule_data.get("name"), type_str, entry_widget)
        self.rule_list.append(rule_data)

        entry_widget.edit_btn.clicked.connect(lambda: self.on_edit_item(rule_data.get("id"), group_widget))
        entry_widget.delete_btn.clicked.connect(lambda: self.on_delete_item(rule_data.get("id"), group_widget))

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

        self.zero_padding_switch = SettingSwitchButton(config.zero_padding, self)

        self.zero_padding_total_digital_choice = SettingComboBox(config.zero_padding_total_digits, ["2", "3", "4", "5"], parent = self)

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
        self.addGroup(
            "",
            self.tr("Zero-padding"),
            self.tr("Pad with leading zeros"),
            self.zero_padding_switch
        )
        padding_width_group = self.addGroup(
            "",
            self.tr("Padding width"),
            self.tr("Total digits (e.g., 001)"),
            self.zero_padding_total_digital_choice
        )

        self.numbering_type_choice.currentIndexChanged.connect(lambda index: self.starting_number_group.setEnabled(index == 0))
        self.zero_padding_switch.checkedChanged.connect(lambda checked: padding_width_group.setEnabled(checked))

        self.starting_number_group.setEnabled(self.numbering_type_choice.currentIndex() == 0)
        padding_width_group.setEnabled(self.zero_padding_switch.isChecked())

    def set_current_starting_number(self, value: int):
        config.set(config.starting_number, value)

        self.starting_number_group.setContent(self.get_starting_number_content(value))

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

        self.addGroup("", self.tr("Auto-select All"), self.tr("Automatically select all items after parsing"), self.auto_check_all_switch)
