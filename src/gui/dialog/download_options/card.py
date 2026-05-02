from PySide6.QtCore import Qt

from qfluentwidgets import (
    ExpandGroupSettingCard, FluentIcon, SwitchButton, IndicatorPosition, HyperlinkButton, MessageBox, SettingCard,
    ComboBox
)

from gui.component.widget import DictComboBox

from util.common.data import reversed_video_quality_map, reversed_audio_quality_map, reversed_video_codec_map, reversed_audio_codec_map
from util.common import config, Translator, ExtendedFluentIcon
from util.parse.preview.info import PreviewerInfo
from util.format import FileNameFormatter, Units
from util.common.enum import MediaType

class MediaInfoCard(ExpandGroupSettingCard):
    def __init__(self, options_dialog, parent = None):
        super().__init__(FluentIcon.INFO, self.tr("Media Info"), self.tr("Configure download video quality, audio quality, and codec settings"), parent)

        self.options_dialog = options_dialog

        self.guide_btn = HyperlinkButton("", self.tr("Guide"), parent = self)

        self.video_quality_choice = DictComboBox(parent = self)
        self.audio_quality_choice = DictComboBox(parent = self)
        self.video_codec_choice = DictComboBox(parent = self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.video_quality_group = self.addGroup(FluentIcon.VIDEO, self.tr("Video Quality"), "", self.video_quality_choice)
        self.audio_quality_group = self.addGroup(FluentIcon.MUSIC, self.tr("Audio Quality"), "", self.audio_quality_choice)
        self.video_codec_group = self.addGroup(FluentIcon.CODE, self.tr("Video Codec"), "", self.video_codec_choice)

        self.addWidget(self.guide_btn)

        self.guide_btn.clicked.connect(self.on_guide)

    def on_load(self):
        self.video_quality_choice.set_current_data(config.video_quality_id)
        self.audio_quality_choice.set_current_data(config.audio_quality_id)
        self.video_codec_choice.set_current_data(config.video_codec_id)

    def update_choice_data(self, video_data: dict, audio_data: dict, codec_data: dict):
        self.video_quality_choice.clear()
        self.audio_quality_choice.clear()
        self.video_codec_choice.clear()

        self.video_quality_choice.init_dict_data(video_data, Translator.VIDEO_QUALITY())
        self.audio_quality_choice.init_dict_data(audio_data, Translator.AUDIO_QUALITY())
        self.video_codec_choice.init_dict_data(codec_data, Translator.VIDEO_CODEC())

        self.on_load()

    def pre_query_video_info(self):
        self.video_quality_group.setContent(self.tr("Fetching..."))
        self.video_codec_group.setContent(self.tr("Fetching..."))

    def pre_query_audio_info(self):
        self.audio_quality_group.setContent(self.tr("Fetching..."))

    def on_query_video_info(self, info: dict):
        # 处理获取到的视频媒体信息并更新界面显示

        if info:
            self.update_video_quality_description(info)
            self.update_video_codec_description(info)
        else:
            self.video_quality_group.setContent(self.tr("Video quality will be automatically selected based on priority settings"))
            self.video_codec_group.setContent(self.tr("Video codec will be automatically selected based on priority settings"))

    def on_query_audio_info(self, info: dict):
        # 处理获取到的音频媒体信息并更新界面显示

        if info:
            self.update_audio_quality_description(info)
        else:
            # 音频流为空，需判断原因并给出提示
            match PreviewerInfo.media_type:
                case MediaType.DASH:
                    reason = self.tr("No audio track (silent video stream)")

                case MediaType.MP4 | MediaType.FLV:
                    reason = self.tr("Audio track is already embedded in the video stream")

                case MediaType.UNKNOWN:
                    reason = self.tr("Audio quality will be automatically selected based on priority settings")

            self.audio_quality_group.setContent(reason)

    def update_video_quality_description(self, info: dict):
        video_quality_key = reversed_video_quality_map.get(info["quality_id"], self.tr("Unknown Video Quality"))

        quality_label_list = [
            Translator.VIDEO_QUALITY(video_quality_key),
            Units.format_frame_rate(float(info["frame_rate"])),
            Units.format_bitrate(info["bitrate"]),
            Units.format_file_size(info["file_size"])
        ]

        if PreviewerInfo.media_type == MediaType.MP4:
            quality_label_list.append("MP4")

        elif PreviewerInfo.media_type == MediaType.FLV:
            quality_label_list.append("FLV")

        if not info["is_full_video"]:
            quality_label_list.append(self.tr("preview"))

        self.video_quality_group.setContent(", ".join([label for label in quality_label_list if label]))

    def update_audio_quality_description(self, info: dict):
        audio_quality_key = reversed_audio_quality_map.get(info["quality_id"], self.tr("Unknown Audio Quality"))

        label_list = [
            Translator.AUDIO_QUALITY(audio_quality_key),
            reversed_audio_codec_map.get(info["codec"], info["codec"]),
            Units.format_bitrate(info["bitrate"]),
            Units.format_file_size(info["file_size"])
        ]

        self.audio_quality_group.setContent(", ".join([label for label in label_list if label]))

    def update_video_codec_description(self, info: dict):
        codec_label_list = [
            reversed_video_codec_map.get(info["codec_id"], self.tr("Unknown Video Codec")),
            self.get_codec_tip(info["codec_id"])
        ]

        self.video_codec_group.setContent(", ".join(codec_label_list))

    def get_codec_tip(self, video_codec_id: int):
        match video_codec_id:
            case 7:
                return self.tr("Largest file size, best compatibility")
            
            case 12:
                return self.tr("Smaller file size, limited compatibility")
            
            case 13:
                return self.tr("Smallest file size, poorest compatibility")

    def on_guide(self):
        dialog = MessageBox(
            self.tr("Guide"),
            Translator.MEDIA_INFO_GUIDE(),
            parent = self.options_dialog
        )
        dialog.hideCancelButton()

        dialog.exec()

    @property
    def video_quality_id(self):
        return self.video_quality_choice.currentData()
    
    @property
    def audio_quality_id(self):
        return self.audio_quality_choice.currentData()
    
    @property
    def video_codec_id(self):
        return self.video_codec_choice.currentData()

class MediaOptionsCard(ExpandGroupSettingCard):
    def __init__(self, parent = None):
        super().__init__(ExtendedFluentIcon.OPTIONS, self.tr("Media Options"), self.tr("Configure download behavior for video and audio streams"), parent)

        self.download_video_stream_switch = SwitchButton(parent = self, indicatorPos = IndicatorPosition.RIGHT)
        self.download_audio_stream_switch = SwitchButton(parent = self, indicatorPos = IndicatorPosition.RIGHT)

        self.merge_video_audio_switch = SwitchButton(parent = self, indicatorPos = IndicatorPosition.RIGHT)
        self.keep_original_files_switch = SwitchButton(parent = self, indicatorPos = IndicatorPosition.RIGHT)

        self.addGroup("", self.tr("Download standalone video stream"), self.tr("Download a video stream without audio"), self.download_video_stream_switch)
        self.addGroup("", self.tr("Download standalone audio stream"), self.tr("Download an audio stream without video"), self.download_audio_stream_switch)
        self.merge_video_audio_group = self.addGroup("", self.tr("Merge video and audio"), self.tr("Merge separate video and audio streams into a single file"), self.merge_video_audio_switch)
        self.keep_original_files_group = self.addGroup("", self.tr("Keep original files"), self.tr("Keep the original separate stream files after merging"), self.keep_original_files_switch)

        self.connect_signals()

        self.on_load()

    def connect_signals(self):
        self.download_video_stream_switch.checkedChanged.connect(self.on_change_download_stream_options)
        self.download_audio_stream_switch.checkedChanged.connect(self.on_change_download_stream_options)
        self.merge_video_audio_switch.checkedChanged.connect(self.on_change_merge_option)

    def on_load(self):
        self.download_video_stream_switch.setChecked(config.download_video_stream)
        self.download_audio_stream_switch.setChecked(config.download_audio_stream)
        self.merge_video_audio_switch.setChecked(config.merge_video_audio)
        self.keep_original_files_switch.setChecked(config.keep_original_files)

    def on_change_download_stream_options(self):
        enable = self.download_video_stream_switch.isChecked() and self.download_audio_stream_switch.isChecked()

        self.merge_video_audio_switch.setEnabled(enable)
        self.merge_video_audio_switch.setChecked(enable)
        self.merge_video_audio_group.setEnabled(enable)

        keep_original_enable = enable and self.merge_video_audio_switch.isChecked()
        
        self.keep_original_files_switch.setEnabled(keep_original_enable)
        self.keep_original_files_group.setEnabled(keep_original_enable)

        if not keep_original_enable:
            self.keep_original_files_switch.setChecked(False)

    def on_change_merge_option(self):
        enable = self.merge_video_audio_switch.isChecked()

        self.keep_original_files_switch.setEnabled(enable)
        self.keep_original_files_group.setEnabled(enable)

        if not enable:
            self.keep_original_files_switch.setChecked(False)

    @property
    def download_video_stream(self):
        return self.download_video_stream_switch.isChecked()
    
    @property
    def download_audio_stream(self):
        return self.download_audio_stream_switch.isChecked()
    
    @property
    def merge_video_audio(self):
        return self.merge_video_audio_switch.isChecked()
    
    @property
    def keep_original_files(self):
        return self.keep_original_files_switch.isChecked()

class NamingConventionCard(SettingCard):
    def __init__(self, parent = None):
        super().__init__(FluentIcon.DOCUMENT, self.tr("Naming Convention"), self.tr("Choose the naming rule to use when downloading"), parent)

        self.rule_choice = ComboBox(parent = self)

        self.rule_group = self.hBoxLayout.addWidget(self.rule_choice, 0, Qt.AlignmentFlag.AlignRight)

        self.hBoxLayout.addSpacing(16)

        self.init_default_rules()

    def init_default_rules(self):
        # 查询可用的命名规则列表
        file_name_formatter = FileNameFormatter()
        rule_list = file_name_formatter.get_rule_list_from_attribute(PreviewerInfo.attribute)

        # 如果能查询到数据，则说明是支持自定义命名规则的类型，直接显示
        if rule_list:
            for entry in rule_list:
                name_key = entry["name"]
                default_rule_names = Translator.DEFAULT_RULE_NAMES()

                if name_key in default_rule_names:
                    entry["name"] = Translator.DEFAULT_RULE_NAMES(name_key)

                self.rule_choice.addItem(entry["name"], userData = entry["id"])

                # 如果是默认规则，直接选中
                if entry["default"]:
                    self.rule_choice.setCurrentText(entry["name"])

        # 如果查询不到数据，则说明是该类型不支持自定义命名规则，禁用选择框
        else:
            self.rule_choice.addItem(self.tr("Not available"))
            self.rule_choice.setEnabled(False)
            self.setContent(self.tr("Custom naming rules are not supported for favorites and profiles"))
