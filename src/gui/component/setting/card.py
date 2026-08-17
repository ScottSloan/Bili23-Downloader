from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QFileDialog, QApplication, QWidget
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtGui import QColor

from qfluentwidgets import (
    PushButton, FluentIcon, PushSettingCard, qconfig, ColorDialog, PrimaryPushButton, setCustomStyleSheet,
    MessageBox, ExpandGroupSettingCard as _ExpandGroupSettingCard, HyperlinkLabel, DropDownPushButton,
    RoundMenu, Action
)
from qfluentwidgets.components.settings.expand_setting_card import GroupWidget as _GroupWidget

from .widget import SettingSwitchButton, SettingComboBox, SettingSlider
from ..widget.button import TransparentToolButton
from ..widget.spinbox import SpinBox

from util.common.enum import VideoContainer, ToastNotificationCategory
from util.common.config import config, isWin11, APPConfig
from util.thread.pool import GlobalThreadPoolTask
from util.common.icon import ExtendedFluentIcon
from util.common.io.directory import Directory
from util.common.translator import Translator
from util.common.signal_bus import signal_bus

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class GuideSettingCardBase:
    def showHyperLinkLabel(self, label: str):
        self.hyper_label = HyperlinkLabel(text = label, parent = self)

        self.contentLayout.addSpacing(5)
        self.contentLayout.addWidget(self.hyper_label, 0, Qt.AlignmentFlag.AlignLeft)
        self.contentLayout.addStretch()

        styleSheet = """
        HyperlinkLabel {
            font-size: 11px;
        }
        """
        setCustomStyleSheet(self.hyper_label, styleSheet, styleSheet)

    def showGuideMessageBox(self, title: str, content: str):
        from ..dialog import MessageBox
        
        dialog = MessageBox(
            title = title,
            content = content,
            parent = self.parent_window
        )
        dialog.hideCancelButton()

        dialog.show()

    def _initContentLayout(self, vBoxLayout: QVBoxLayout, contentLabel: QLabel):
        vBoxLayout.removeWidget(contentLabel)

        self.contentLayout = QHBoxLayout()
        self.contentLayout.setSpacing(0)
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.contentLayout.addWidget(contentLabel, 0, Qt.AlignmentFlag.AlignLeft)

        vBoxLayout.addLayout(self.contentLayout)

class GroupWidget(_GroupWidget, GuideSettingCardBase):
    def __init__(self, icon, title, content, widget, stretch = 0):
        super().__init__(icon, title, content, widget, stretch)

        self._initContentLayout(self.vBoxLayout, self.contentLabel)

class ExpandGroupSettingCard(_ExpandGroupSettingCard, GuideSettingCardBase):
    def __init__(self, icon, title, content = None, parent = None):
        super().__init__(icon, title, content, parent)

        self._initContentLayout(self.card.vBoxLayout, self.card.contentLabel)

    def addGroup(self, icon, title, content, widget, stretch = 0):
        group = GroupWidget(icon, title, content, widget, stretch)
        self.addGroupWidget(group)

        if hasattr(self, "parent_window"):
            group.parent_window = self.parent_window

        return group

class PersonalizationCard(ExpandGroupSettingCard):
    accentColorChanged = Signal(QColor)

    def __init__(self, parent_window, parent = None):
        super().__init__(FluentIcon.PALETTE, self.tr("Personalization"), self.tr("Customize the app theme, colors, and visual effects"), parent)

        self.parent_window = parent_window

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
            qconfig.get(config.themeColor), self.tr("Choose color"), self.parent_window, enableAlpha = True)
        w.colorChanged.connect(self.__onCustomColorChanged)
        w.exec()

    def __onCustomColorChanged(self, color):
        """ custom color changed slot """
        qconfig.set(config.themeColor, color)
        self.accentColorChanged.emit(color)

class DownloadPathSettingCard(PushSettingCard):
    diskSpaceReady = Signal(str, object)
    filesystemTypeReady = Signal(str, str)

    def __init__(self, parent_window, save = True, parent = None):
        super().__init__(self.tr("Choose folder"), FluentIcon.FOLDER, self.tr("Download Path"), "path", parent)

        self.parent_window = parent_window
        self.save = save
        self.path = ""

        self.set_path(config.get(config.download_path), update_space = False)

        self.diskSpaceReady.connect(self.on_disk_space_ready)
        self.filesystemTypeReady.connect(self.on_filesystem_type_ready)
        
        QTimer.singleShot(0, self.refresh_disk_space)

        self.clicked.connect(self.on_change_download_path)

    def set_path(self, path: str, update_space: bool = True):
        self.path = path

        if update_space:
            # 获取磁盘可用空间
            self.refresh_disk_space()

            # 检查文件系统类型
            self.check_filesystem_type()
        else:
            self.setContent(path)

    def refresh_disk_space(self):
        def worker():
            self.diskSpaceReady.emit(self.path, Directory.calc_disk_space(self.path))

        GlobalThreadPoolTask.run_func(worker)

    def check_filesystem_type(self):
        def worker():
            filesystem_type = Directory.get_filesystem_type(self.path)

            self.filesystemTypeReady.emit(self.path, filesystem_type)

        GlobalThreadPoolTask.run_func(worker)

    def on_disk_space_ready(self, path: str, disk_space_info: dict = None):
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

    def on_filesystem_type_ready(self, path: str, filesystem_type: str):
        if path != self.path or filesystem_type is None:
            return

        if filesystem_type.upper() in ["FAT32", "EXFAT", "VFAT", "MSDOS", "FAT", "FAT16", "FAT12", "MS-DOS"]:
            dialog = MessageBox(
                title = self.tr("The file system of the selected path does not support sparse files"),
                content = self.tr('The file system type of the currently selected download path is {fs}, which does not support sparse files.\n\nIf you continue, please disable the "Preallocate file space" option. (Settings → Behavior → Download Handling)').format(fs = filesystem_type),
                parent = self.parent_window
            )
            dialog.hideCancelButton()

            dialog.show()
        
    def on_change_download_path(self):
        path = Directory.browse_directory(self.parent_window, self.tr("Choose folder"), config.get(config.download_path))

        if path:
            if self.save:
                config.set(config.download_path, path)

            self.set_path(path)

        else:
            dialog = MessageBox(
                title = self.tr("Download Directory Inaccessible"),
                content = self.tr("The selected download directory is inaccessible or lacks write permission. Please check and choose a different directory."),
                parent = self.parent_window
            )
            dialog.hideCancelButton()

            dialog.show()

class PrioritySettingCard(ExpandGroupSettingCard):
    def __init__(self, parent_window, parent = None):
        super().__init__(FluentIcon.SETTING, self.tr("Video, Audio, and Codec Priority"), self.tr("Customize download priority settings"), parent)

        self.parent_window = parent_window

        self.video_quality_btn = PushButton(self.tr("Customize…"), self)
        self.audio_quality_btn = PushButton(self.tr("Customize…"), self)
        self.video_codec_btn = PushButton(self.tr("Customize…"), self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup(FluentIcon.VIDEO, self.tr("Video Quality Priority"), "", self.video_quality_btn)
        self.addGroup(FluentIcon.MUSIC, self.tr("Audio Quality Priority"), "", self.audio_quality_btn)
        self.addGroup(FluentIcon.CODE, self.tr("Codec Priority"), "", self.video_codec_btn)

        self.showHyperLinkLabel(self.tr("About Custom Priority Settings"))

        self.hyper_label.clicked.connect(lambda: self.showGuideMessageBox(self.tr("Instructions"), Translator.PRIORITY_GUIDE()))

class DanmakuSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.COMMENT, self.tr("Danmaku Download Settings"), self.tr("Adjust danmaku download settings"), parent)

        self.download_switch = SettingSwitchButton(config.download_danmaku, parent = self)

        self.type_choice = SettingComboBox(config.danmaku_type, ["xml", "ass", "json"], parent = self)
        self.type_choice.setFixedWidth(120)

        self.custom_style_btn = PushButton(self.tr("Customize…"), self)

        self.embed_switch = SettingSwitchButton(config.embed_danmaku, parent = self)
        self.delete_after_embed_switch = SettingSwitchButton(config.delete_danmaku_after_embed, parent = self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Download Danmaku"), "", self.download_switch)
        self.addGroup("", self.tr("Danmaku Format"), "", self.type_choice)
        self.addGroup("", self.tr("Danmaku Style"), self.tr("Only effective for ASS format danmaku"), self.custom_style_btn)
        self.embed_group = self.addGroup("", self.tr("Embed Danmaku"), self.tr("Embed danmaku into the video file as a subtitle track, only available when the format is ASS and the output container is MKV"), self.embed_switch)
        self.delete_after_embed_group = self.addGroup("", self.tr("Delete Danmaku After Embedding"), self.tr("Delete the original danmaku file after embedding it into the video file"), self.delete_after_embed_switch)

        self.update_embed_option_states()

        self.download_switch.checkedChanged.connect(self.update_embed_option_states)
        self.type_choice.currentIndexChanged.connect(self.update_embed_option_states)
        self.embed_switch.checkedChanged.connect(self.update_embed_option_states)

        # 输出容器格式在另一张卡片上，借 ConfigItem 自带的信号做跨卡片联动
        config.video_container.valueChanged.connect(self.update_embed_option_states)

    def update_embed_option_states(self, *_):
        # 切换到 MP4 或非 ASS 格式时只置灰、不重置开关：容器格式是会被临时来回切换的选项，
        # 重置会让用户切回 MKV 后还得重新开一遍。运行时另有静默跳过兜底
        can_embed = (
            self.download_switch.isChecked()
            and self.type_choice.currentText() == "ass"
            and config.get(config.video_container) == VideoContainer.MKV
        )

        self.embed_group.setEnabled(can_embed)
        self.delete_after_embed_group.setEnabled(can_embed and self.embed_switch.isChecked())

class SubtitleSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.SUBTITLES, self.tr("Subtitle Download Settings"), self.tr("Adjust subtitle download settings"), parent)

        self.download_switch = SettingSwitchButton(config.download_subtitle, parent = self)

        self.type_choice = SettingComboBox(config.subtitle_type, ["srt", "lrc", "txt", "ass", "json"], parent = self)
        self.type_choice.setFixedWidth(120)

        self.language_btn = PushButton(self.tr("Customize…"), self)
        self.custom_style_btn = PushButton(self.tr("Customize…"), self)

        self.embed_switch = SettingSwitchButton(config.embed_subtitle, parent = self)
        self.delete_after_embed_switch = SettingSwitchButton(config.delete_subtitle_after_embed, parent = self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Download Subtitles"), "", self.download_switch)
        self.addGroup("", self.tr("Subtitle Format"), "", self.type_choice)
        self.addGroup("", self.tr("Subtitle Language"), "", self.language_btn)
        self.addGroup("", self.tr("Subtitle Style"), self.tr("Only effective for ASS format subtitles"), self.custom_style_btn)
        self.embed_group = self.addGroup("", self.tr("Embed Subtitles"), self.tr("Embed subtitles into the video file as subtitle tracks, only available when the format is ASS and the output container is MKV"), self.embed_switch)
        self.delete_after_embed_group = self.addGroup("", self.tr("Delete Subtitles After Embedding"), self.tr("Delete the original subtitle files after embedding them into the video file"), self.delete_after_embed_switch)

        self.update_embed_option_states()

        self.download_switch.checkedChanged.connect(self.update_embed_option_states)
        self.type_choice.currentIndexChanged.connect(self.update_embed_option_states)
        self.embed_switch.checkedChanged.connect(self.update_embed_option_states)

        # 输出容器格式在另一张卡片上，借 ConfigItem 自带的信号做跨卡片联动
        config.video_container.valueChanged.connect(self.update_embed_option_states)

    def update_embed_option_states(self, *_):
        can_embed = (
            self.download_switch.isChecked()
            and self.type_choice.currentText() == "ass"
            and config.get(config.video_container) == VideoContainer.MKV
        )

        self.embed_group.setEnabled(can_embed)
        self.delete_after_embed_group.setEnabled(can_embed and self.embed_switch.isChecked())

class CoverSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.PHOTO, self.tr("Cover Download Settings"), self.tr("Adjust cover download settings"), parent)

        self.download_switch = SettingSwitchButton(config.download_cover, parent = self)

        self.type_choice = SettingComboBox(config.cover_type, ["jpg", "png", "avif", "webp"], parent = self)
        self.type_choice.setFixedWidth(120)

        self.attach_cover_switch = SettingSwitchButton(config.attach_cover, parent = self)
        self.delete_cover_after_attach_switch = SettingSwitchButton(config.delete_cover_after_attach, parent = self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Download Cover"), "", self.download_switch)
        self.addGroup("", self.tr("Cover Format"), "", self.type_choice)
        self.attach_cover_group = self.addGroup("", self.tr("Embed Cover"), self.tr("Embed the downloaded cover into the video file"), self.attach_cover_switch)
        self.delete_cover_after_attach_group = self.addGroup("", self.tr("Delete Cover After Embedding"), self.tr("Delete the original cover file after embedding it into the video file"), self.delete_cover_after_attach_switch)

        self.update_cover_option_states()
        self.download_switch.checkedChanged.connect(self.on_toggle_attach_cover)
        self.type_choice.currentIndexChanged.connect(self.on_change_cover_format)
        self.attach_cover_switch.checkedChanged.connect(self.on_toggle_delete_cover)

    def on_change_cover_format(self, index: int):
        # avif 格式不支持作为封面嵌入，如果用户选择了 avif 作为封面格式，则禁用嵌入封面选项
        is_avif = index == 2

        if is_avif and self.attach_cover_switch.isChecked():
            self.attach_cover_switch.setChecked(False)

        self.update_cover_option_states()

    def on_toggle_attach_cover(self, checked: bool):
        if not checked:
            self.attach_cover_switch.setChecked(False)

        self.update_cover_option_states()

    def on_toggle_delete_cover(self, checked: bool):
        if not checked:
            self.delete_cover_after_attach_switch.setChecked(False)

        self.update_cover_option_states()

    def update_cover_option_states(self):
        can_embed_cover = self.download_switch.isChecked() and self.type_choice.currentText() != "avif"
        self.attach_cover_group.setEnabled(can_embed_cover)

        can_delete_cover = can_embed_cover and self.attach_cover_switch.isChecked()
        self.delete_cover_after_attach_group.setEnabled(can_delete_cover)

class ChapterSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.BOOK_SHELF, self.tr("Chapter Settings"), self.tr("Adjust chapter settings"), parent)

        self.download_switch = SettingSwitchButton(config.embed_chapter, parent = self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Embed Chapters"), self.tr("Embed the video chapters into the video file, only effective when merging video and audio"), self.download_switch)

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
    def __init__(self, parent_window, parent = None):
        super().__init__(ExtendedFluentIcon.NUMBERS, self.tr("Numbering"), self.tr("Configure how the {number} variable is formatted"), parent)

        self.parent_window = parent_window

        self.numbering_type_choice = SettingComboBox(
            config.numbering_type,
            [
                self.tr("Sequential numbering starting from 1 per batch"),
                self.tr("Use the index from the parse list"),
                self.tr("Global sequential numbering")
            ],
            parent = self
        )
        self.custom_global_starting_number_btn = PushButton(self.tr("Customize…"), self)

        self.addGroup(
            "",
            self.tr("Numbering Mode"),
            self.tr("Select how the {number} variable is formatted and incremented"),
            self.numbering_type_choice
        )
        
        self.global_number_group = self.addGroup(
            "",
            self.tr("Global Sequential Starting Number"),
            self.get_global_starting_number_content(config.global_starting_number),
            self.custom_global_starting_number_btn
        )

        self.showHyperLinkLabel(self.tr("About Numbering Settings"))

        self.connect_signals()

        self.global_number_group.setEnabled(self.numbering_type_choice.currentIndex() == 2)

    def connect_signals(self):
        self.hyper_label.clicked.connect(lambda: self.showGuideMessageBox(self.tr("Instructions"), Translator.NUMBERING_GUIDE()))
        self.numbering_type_choice.currentIndexChanged.connect(self.on_change_numbering_type)

        self.card.expandButton.clicked.connect(self._update_global_starting_number)

        self.custom_global_starting_number_btn.clicked.connect(self.show_custom_starting_number_dialog)

    def on_change_numbering_type(self, type_index: int):
        self.global_number_group.setEnabled(type_index == 2)

    def set_current_global_starting_number(self, value: int):
        config.global_starting_number = value

        self.global_number_group.setContent(self.get_global_starting_number_content(value))

    def get_global_starting_number_content(self, value: int):
        return self.tr("Set global sequential starting number. Current: {current}").format(current = value)

    def show_custom_starting_number_dialog(self):
        from ...dialog.setting.starting_number import StartingNumberDialog

        dialog = StartingNumberDialog(
            self.tr("Customize Global Sequential Starting Number"), 
            config.global_starting_number, 
            self.parent_window
        )

        if dialog.exec():
            self.set_current_global_starting_number(dialog.starting_number)

    def _update_global_starting_number(self):
        self.get_global_starting_number_content(config.global_starting_number)

class CDNSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent_window, parent = None):
        super().__init__(FluentIcon.CLOUD_DOWNLOAD, self.tr("CDN Settings"), self.tr("Adjust CDN settings used for downloading"), parent)

        self.parent_window = parent_window

        self.prefer_server_provider_switch = SettingSwitchButton(config.prefer_cdn_server_provider, parent = self)
        self.configure_area_btn = PushButton(self.tr("Configure…"), self)
        self.custom_provider_btn = PushButton(self.tr("Customize…"), self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Prefer Service Provider CDN"), self.tr("Prefer CDN provided by cloud service providers to improve download stability"), self.prefer_server_provider_switch)
        self.addGroup("", self.tr("Select Geographic Location"), self.tr("Select your actual location to automatically match a more suitable CDN server and improve download speed"), self.configure_area_btn)
        self.addGroup("", self.tr("Customize Service Provider CDN"), self.tr("Customize the list and priority of service provider CDNs"), self.custom_provider_btn)

        self.configure_area_btn.clicked.connect(self.show_select_area_dialog)

    def show_select_area_dialog(self):
        from ...dialog.setting.select_area import SelectAreaDialog

        dialog = SelectAreaDialog(self.parent_window)
        dialog.exec()

class ProxySettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.SERVER, self.tr("Proxy Settings"), self.tr("Adjust proxy server settings used for parsing and downloading"), parent)

        self.proxy_mode_choice = SettingComboBox(config.proxy_mode, [self.tr("Do not use proxy"), self.tr("Use system proxy"), self.tr("Manual configuration")], parent = self)

        self.custom_btn = PushButton(self.tr("Configure…"), self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.addGroup("", self.tr("Proxy Mode"), self.tr("Select the proxy used for parsing and downloading"), self.proxy_mode_choice)
        self.custom_group = self.addGroup("", self.tr("Configure Proxy Server"), "", self.custom_btn)

        self.custom_group.setEnabled(self.proxy_mode_choice.currentIndex() == 2)

class FFmpegSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent_window, parent = None):
        super().__init__(FluentIcon.SETTING, self.tr("FFmpeg Settings"), self.tr("Configure FFmpeg used for merging and converting videos"), parent)

        self.parent_window = parent_window

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

        self.custom_parse_list_btn = PushButton(self.tr("Configure…"), self)
        self.custom_monitor_clipboard_btn = PushButton(self.tr("Configure…"), self)
        self.custom_auto_select_btn = PushButton(self.tr("Configure…"), self)
        self.parse_history_switch = SettingSwitchButton(config.parse_history, parent = self)

        self.addGroup("", self.tr("Parse List Settings"), self.tr("Customize the display and behavior of the parse list"), self.custom_parse_list_btn)
        self.addGroup("", self.tr("Monitor Clipboard Settings"), self.tr("Configure the behavior of clipboard monitoring"), self.custom_monitor_clipboard_btn)
        self.addGroup("", self.tr("Auto-select Download Items Settings"), self.tr("Configure how items in the parse list are automatically selected after parsing"), self.custom_auto_select_btn)
        self.addGroup("", self.tr("Save Parse History"), self.tr("Save the history of parsed links"), self.parse_history_switch)

class WindowBehaviorSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.APPLICATION_WINDOW, self.tr("Window Behavior"), self.tr("Adjust the behavior of the main window during startup, runtime, and shutdown"), parent)

        self.silent_start_switch = SettingSwitchButton(config.silent_start, parent = self)
        self.remember_window_state_switch = SettingSwitchButton(config.remember_window_state, parent = self)
        self.stay_on_top_switch = SettingSwitchButton(config.stay_on_top, parent = self)
        self.when_close_action_choice = SettingComboBox(config.when_close_window, [self.tr("Exit the program"), self.tr("Minimize to system tray"), self.tr("Always ask")], parent = self)

        self.addGroup("", self.tr("Silent Start"), self.tr("Start the application without showing the main window"), self.silent_start_switch)
        self.addGroup("", self.tr("Remember Window State"), self.tr("Restore the window size and position from the last session on startup"), self.remember_window_state_switch)
        self.addGroup("", self.tr("Stay on Top"), self.tr("Keep the window always on top of the desktop"), self.stay_on_top_switch)
        self.addGroup("", self.tr("Close the Main Window"), self.tr("Choose the action when closing the main window"), self.when_close_action_choice)

class DownloadHandlingSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent_window, parent = None):
        super().__init__(FluentIcon.DOWNLOAD, self.tr("Download Handling"), self.tr("Configure download prompts, notifications, and file conflict handling"), parent)

        self.parent_window = parent_window

        self.show_download_options_dialog_switch = SettingSwitchButton(config.show_download_options_dialog, parent = self)
        self.show_notification_switch = SettingSwitchButton(config.show_notification, parent = self)
        self.duplicate_download_resolution_choice = SettingComboBox(config.duplicate_download_resolution, [self.tr("Continue"), self.tr("Skip"), self.tr("Always ask")], parent = self)
        self.file_conflict_resolution_choice = SettingComboBox(config.file_conflict_resolution, [self.tr("Auto-rename"), self.tr("Overwrite")], parent = self)
        self.prelocation_switch = SettingSwitchButton(config.preallocate_file_space, parent = self)

        self.addGroup("", self.tr("Show Download Options Dialog"), self.tr("Show a dialog before starting the download to customize settings for this task"), self.show_download_options_dialog_switch)
        self.addGroup("", self.tr("Show Notifications"), self.tr("Show notifications when downloads complete"), self.show_notification_switch)
        preallocate_group = self.addGroup("", self.tr("Preallocate File Space"), self.tr("Preallocate file space before downloading to improve performance"), self.prelocation_switch)
        duplicate_group = self.addGroup("", self.tr("Duplicate Download Resolution"), self.tr("Choose the action when a duplicate download is detected"), self.duplicate_download_resolution_choice)

        self.addGroup("", self.tr("File Conflict Resolution"), self.tr("Choose the action when a file with the same name already exists"), self.file_conflict_resolution_choice)

        preallocate_group.showHyperLinkLabel(self.tr("About Preallocating File Space"))
        preallocate_group.hyper_label.clicked.connect(lambda: preallocate_group.showGuideMessageBox(self.tr("Instructions"), Translator.PREALLOCATE_GUIDE()))

        duplicate_group.showHyperLinkLabel(self.tr("About Duplicate Download Resolution"))
        duplicate_group.hyper_label.clicked.connect(lambda: duplicate_group.showGuideMessageBox(self.tr("Instructions"), Translator.DUPLICATE_DOWNLOAD_GUIDE()))

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

class OtherAdvancedSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent_window, parent = None):
        super().__init__(FluentIcon.SETTING, self.tr("Other Advanced Settings"), self.tr("Configure other advanced settings"), parent)

        self.parent_window = parent_window

        self.custom_user_agent_btn = PushButton(self.tr("Customize…"), self)
        self.config_file_settings_btn = DropDownPushButton(text = self.tr("Configure"), parent = self)

        menu = RoundMenu(parent = self.config_file_settings_btn)
        menu.addAction(Action(ExtendedFluentIcon.IMPORT, self.tr("Import Config"), triggered = self.on_import_config))
        menu.addAction(Action(ExtendedFluentIcon.EXPORT, self.tr("Export Config"), triggered = self.on_export_config))
        menu.addAction(Action(ExtendedFluentIcon.RETRY, self.tr("Reset Config"), triggered = self.on_reset_config))
        menu.addAction(Action(FluentIcon.FOLDER, self.tr("Open Config Directory"), triggered = self.on_open_config_directory))

        self.config_file_settings_btn.setMenu(menu)

        self.addGroup("", self.tr("Custom User-Agent"), self.tr("Set a custom User-Agent string for network requests"), self.custom_user_agent_btn)
        self.addGroup("", self.tr("Config File Settings"), self.tr("Import/export configuration files or reset to defaults"), self.config_file_settings_btn)
        
        self.connect_signals()

    def connect_signals(self):
        self.custom_user_agent_btn.clicked.connect(self.on_custom_user_agent)

    def on_custom_user_agent(self):
        from ...dialog.setting.user_agent import UserAgentDialog

        dialog = UserAgentDialog(self.parent_window)
        dialog.exec()

    def on_import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent_window,
            self.tr("Import Config File"),
            "",
            self.tr("Config Files (*.json)")
        )

        if not file_path:
            return
        
        original_file = config.file
        
        config.load(file_path)
        config.file = original_file  # 恢复原来的配置文件路径，避免误覆盖
        
        config.save()

        config.appRestartSig.emit()

        logger.info("从文件导入配置成功，路径：%s", file_path)

    def on_export_config(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent_window,
            self.tr("Export Config File"),
            "",
            self.tr("Config Files (*.json)")
        )

        if not file_path:
            return
        
        temp_config = APPConfig()
        temp_config.load(config.file)
        temp_config.file = Path(file_path)

        temp_config.save()

        logger.info("配置导出成功，路径：%s", file_path)

    def on_reset_config(self):
        dialog = MessageBox(
            self.tr("Reset Config"),
            self.tr("Are you sure you want to reset all settings to their default values? This action cannot be undone."),
            self.parent_window
        )

        if dialog.exec():
            # 直接删除配置文件，程序会在下次启动时自动创建一个新的默认配置文件
            config.file.unlink(missing_ok = True)
            
            config.appRestartSig.emit()

            logger.info("配置重置成功，配置文件已删除：%s", config.file)

    def on_open_config_directory(self):
        Directory.open_directory_in_explorer(str(config.file.parent))

class MCPSettingCard(ExpandGroupSettingCard):
    # 开关、端口、令牌任一变化都需要重启服务器才能生效
    restartRequested = Signal()

    def __init__(self, parent_window, parent = None):
        super().__init__(ExtendedFluentIcon.SERVER, self.tr("MCP Server"), self.tr("Let AI clients parse links and manage downloads through the Model Context Protocol"), parent)

        self.parent_window = parent_window

        self.enable_switch = SettingSwitchButton(config.mcp_enabled, parent = self)

        self.status_label = QLabel(self)

        self.port_box = SpinBox(self)
        self.port_box.setRange(*config.mcp_port.range)
        self.port_box.setValue(config.get(config.mcp_port))
        self.port_box.setMinimumWidth(150)

        self.allow_download_switch = SettingSwitchButton(config.mcp_allow_download, parent = self)

        self.copy_token_btn = PushButton(self.tr("Copy"), self)
        self.regenerate_token_btn = PushButton(self.tr("Regenerate"), self)

        # 客户端分两种：一种支持 HTTP 直连（Claude Code 等），一种只认 stdio
        # 传输（Claude Desktop 等，配置里填 url 会被当作非法条目跳过）。
        # 让用户自己去分辨哪个客户端支持什么不现实，两种配置都给
        self.copy_config_btn = DropDownPushButton(text = self.tr("Copy"), parent = self)

        config_menu = RoundMenu(parent = self.copy_config_btn)
        config_menu.addAction(Action(
            FluentIcon.GLOBE, self.tr("HTTP (Claude Code, etc.)"), triggered = self.on_copy_http_config
        ))
        config_menu.addAction(Action(
            FluentIcon.COMMAND_PROMPT, self.tr("stdio (Claude Desktop, etc.)"), triggered = self.on_copy_stdio_config
        ))

        self.copy_config_btn.setMenu(config_menu)

        token_layout = QHBoxLayout()
        token_layout.setContentsMargins(0, 0, 0, 0)
        token_layout.addWidget(self.copy_token_btn)
        token_layout.addWidget(self.regenerate_token_btn)

        token_widget = QWidget(self)
        token_widget.setLayout(token_layout)

        self.addGroup("", self.tr("Enable MCP Server"), self.tr("Listen on the local loopback address only. Disabled by default."), self.enable_switch)
        self.status_group = self.addGroup("", self.tr("Status"), "", self.status_label)
        self.port_group = self.addGroup("", self.tr("Port"), self.tr("Takes effect after the server restarts"), self.port_box)
        self.addGroup("", self.tr("Allow Download Operations"), self.tr("Let AI clients create, pause and cancel download tasks. Turn off to expose read-only tools."), self.allow_download_switch)
        self.addGroup("", self.tr("Access Token"), self.tr("Required by every request. Treat it like a password."), token_widget)
        self.addGroup("", self.tr("Client Configuration"), self.tr("Copy a ready-to-use MCP client configuration"), self.copy_config_btn)

        # 这里跳转到在线文档而不是弹说明对话框：配置 AI 客户端要贴 JSON、
        # 分辨客户端差异，篇幅远超一个对话框能承载的量
        self.showHyperLinkLabel(self.tr("View Documentation"))

        self.hyper_label.clicked.connect(self.on_open_documentation)

        self.copy_token_btn.clicked.connect(self.on_copy_token)
        self.regenerate_token_btn.clicked.connect(self.on_regenerate_token)

        self.enable_switch.checkedChanged.connect(self.on_toggle_enabled)
        self.port_box.valueChanged.connect(self.on_port_changed)

        self.update_status()

    def on_open_documentation(self):
        import webbrowser

        webbrowser.open("https://bili23.scott-sloan.cn/doc/mcp-server.html")

    def update_status(self):
        if not config.get(config.mcp_enabled):
            text = self.tr("Disabled")

        elif config.mcp_running:
            text = self.tr("Listening on 127.0.0.1:{port}").format(port = config.get(config.mcp_port))

        elif config.mcp_last_error:
            text = self.tr("Failed to start: {error}").format(error = config.mcp_last_error)

        else:
            text = self.tr("Not running")

        self.status_label.setText(text)

    def on_toggle_enabled(self, checked: bool):
        self.restartRequested.emit()

    def on_port_changed(self, value: int):
        config.set(config.mcp_port, value)

        self.restartRequested.emit()

    def _ensure_token(self) -> str:
        token = config.get(config.mcp_token)

        if not token:
            from util.mcp.server import generate_token

            token = generate_token()

            config.set(config.mcp_token, token)

        return token

    def on_copy_token(self):
        QApplication.clipboard().setText(self._ensure_token())

        signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Access token copied"))

    def on_regenerate_token(self):
        dialog = MessageBox(
            self.tr("Regenerate Access Token"),
            self.tr("Existing AI clients will stop working until they are reconfigured with the new token. Continue?"),
            self.parent_window
        )

        if not dialog.exec():
            return

        from util.mcp.server import generate_token

        config.set(config.mcp_token, generate_token())

        self.restartRequested.emit()

        signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Access token regenerated"))

    def _copy_config(self, entry: dict):
        import json

        QApplication.clipboard().setText(
            json.dumps({"mcpServers": {"bili23-downloader": entry}}, indent = 2)
        )

        signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Client configuration copied"))

    def on_copy_http_config(self):
        self._copy_config({
            "type": "http",
            "url": f"http://127.0.0.1:{config.get(config.mcp_port)}/mcp",
            "headers": {"Authorization": f"Bearer {self._ensure_token()}"},
        })

    def on_copy_stdio_config(self):
        from util.mcp.stdio_bridge import stdio_launch_command

        command = stdio_launch_command()

        # 令牌不写进配置：桥接会自己从 config.json 读，用户重新生成令牌后
        # 不必再改一遍客户端配置
        self._ensure_token()

        self._copy_config({
            "command": command[0],
            "args": command[1:],
        })
