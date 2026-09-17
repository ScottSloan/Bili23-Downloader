from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics

from qfluentwidgets import (
    FluentIcon, SettingCard, ComboBox
)

from gui.component.setting.card import ExpandGroupSettingCard
from gui.component.widget.button import ToolButton
from gui.component.widget.combobox import DictComboBox

from util.common.data import (
    reversed_video_quality_map, reversed_audio_quality_map, reversed_video_codec_map, reversed_audio_codec_map,
    reversed_convention_type_map
)
from util.common.naming_rules import display_name
from util.common.translator import Translator
from util.common.enum import MediaType
from util.common.runtime import runtime

from util.parse.preview.info import PreviewerInfo
from util.format.file_name import FileNameFormatter
from util.format.units import Units

class ChoiceWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.setContentsMargins(0, 0, 0, 0)

        self.choice = DictComboBox(parent = self)
        self.custom_btn = ToolButton(FluentIcon.SETTING, parent = self)
        self.custom_btn.setToolTip(self.tr("Customize Priority"))

        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.choice)
        self.hBoxLayout.addWidget(self.custom_btn)

class MediaInfoCard(ExpandGroupSettingCard):
    def __init__(self, parent_window, parent = None):
        super().__init__(FluentIcon.INFO, self.tr("Media Info"), self.tr("Configure download video quality, audio quality, and codec settings"), parent)

        self.parent_window = parent_window

        self.video_quality_widget = ChoiceWidget(parent = self)
        self.audio_quality_widget = ChoiceWidget(parent = self)
        self.video_codec_widget = ChoiceWidget(parent = self)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        self.source_group = self.addGroup(FluentIcon.MOVIE, self.tr("Source Video"), "", QWidget(self))
        self.video_quality_group = self.addGroup(FluentIcon.VIDEO, self.tr("Video Quality"), "", self.video_quality_widget)
        self.audio_quality_group = self.addGroup(FluentIcon.MUSIC, self.tr("Audio Quality"), "", self.audio_quality_widget)
        self.video_codec_group = self.addGroup(FluentIcon.CODE, self.tr("Video Codec"), "", self.video_codec_widget)

        self.showHyperLinkLabel(self.tr("About Media Info"))

        self.connect_signals()

    def connect_signals(self):
        self.hyper_label.clicked.connect(lambda: self.showGuideMessageBox(self.tr("Instructions"), Translator.MEDIA_INFO_GUIDE()))

    def on_load(self):
        self.video_quality_widget.choice.set_current_data(runtime.download.video_quality_id)
        self.audio_quality_widget.choice.set_current_data(runtime.download.audio_quality_id)
        self.video_codec_widget.choice.set_current_data(runtime.download.video_codec_id)

    def update_source_description(self):
        # 说明当前的清晰度、编码等信息取自哪个视频。
        # 解析结果包含多个视频时，媒体信息只取其中一个，且首选项无权限时会自动换用备选，
        # 不说明来源的话，用户看到的清晰度可能与自己要下载的视频对不上
        title = PreviewerInfo.episode_title or self.tr("Unknown")

        if PreviewerInfo.from_fallback:
            content = self.tr("{title} · media info of the video the link points to is unavailable, this one is used instead").format(title = title)
        else:
            content = title

        content = "#{number} - {content}".format(number = PreviewerInfo.episode_number, content = content)

        # 对话框宽度固定，标题过长时省略，完整内容放到工具提示里
        label = self.source_group.contentLabel

        self.source_group.setContent(QFontMetrics(label.font()).elidedText(content, Qt.TextElideMode.ElideRight, 540))

        label.setToolTip(content)

    def update_choice_data(self, video_data: dict, audio_data: dict, codec_data: dict):
        self.video_quality_widget.choice.clear()
        self.audio_quality_widget.choice.clear()
        self.video_codec_widget.choice.clear()

        self.video_quality_widget.choice.init_dict_data(video_data, Translator.VIDEO_QUALITY())
        self.audio_quality_widget.choice.init_dict_data(audio_data, Translator.AUDIO_QUALITY())
        self.video_codec_widget.choice.init_dict_data(codec_data, Translator.VIDEO_CODEC())

        self.on_load()

    def pre_query_video_info(self):
        self.video_quality_group.setContent(self.tr("Fetching..."))
        self.video_codec_group.setContent(self.tr("Fetching..."))

        # 上一次查询留下的回退提示属于上一组画质/编码，重新查询期间先撤下，
        # 免得它挂在那里与新结果对不上
        self.video_codec_group.setWarningContent()

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

            self.video_codec_group.setWarningContent()

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
        codec_id = info["codec_id"]
        fallback_message = self.get_codec_fallback_message(codec_id)

        if fallback_message:
            # 回退时这一行让给「实际编码 + 为什么不是它」，省略掉体积/兼容性那句
            # 通用说明：三者串成一行会把右侧的编码下拉框挤出卡片（实测中文多出
            # 一截就会挡住，英文更是整条越界），而此刻用户要知道的正是前两件事
            codec_label_list = [reversed_video_codec_map.get(codec_id, self.tr("Unknown Video Codec"))]

        else:
            codec_label_list = [
                reversed_video_codec_map.get(codec_id, self.tr("Unknown Video Codec")),
                self.get_codec_tip(codec_id)
            ]

        self.video_codec_group.setContent(", ".join(codec_label_list))

        self.video_codec_group.setWarningContent(fallback_message)

    def get_codec_fallback_message(self, codec_id: int):
        """
        用户指定了编码、而稿件里没有这一路流时，生成那句要显示的提示，否则返回空串

        这一行显示的从来都是**实际**会用到的编码，但只有一行灰字，与画质、码率、
        文件大小并排放在一起，看不出「这和你选的不一样」。Issue #465 的报告者选了
        AV1、下载到 AVC/H.264，全程没有任何地方告诉他这个稿件里没有 AV1。

        刻意不重复实际编码的名字：它就写在这句话前面，再说一遍只会把行撑长。

        「自动（按优先级）」不算回退：按优先级挑编码本来就是它的行为
        """
        requested_codec_id = self.video_codec_id

        # 20 即「自动（按优先级）」，见 media_info.py 的 video_codec_map
        if requested_codec_id in (None, 20) or requested_codec_id == codec_id:
            return ""

        return Translator.TIP_MESSAGES("VIDEO_CODEC_FALLBACK").format(
            requested = Translator.VIDEO_CODEC(reversed_video_codec_map.get(requested_codec_id, ""))
        )

    def get_codec_tip(self, video_codec_id: int):
        match video_codec_id:
            case 7:
                return self.tr("Largest file size, best compatibility")
            
            case 12:
                return self.tr("Smaller file size, limited compatibility")
            
            case 13:
                return self.tr("Smallest file size, poorest compatibility")

    @property
    def video_quality_id(self):
        return self.video_quality_widget.choice.currentData()
    
    @property
    def audio_quality_id(self):
        return self.audio_quality_widget.choice.currentData()
    
    @property
    def video_codec_id(self):
        return self.video_codec_widget.choice.currentData()

def fill_rule_choice(choice: ComboBox, type_id: int):
    """
    把某个内容类型下可用的命名规则填进下拉框，返回是否有可选项

    只取显示名，不写回 entry —— 写回去就把当前语言的译文持久化进了配置，
    用户切一次界面语言，翻译键便再也匹配不上
    """
    rule_list = FileNameFormatter().get_rule_list_from_type(type_id)

    for entry in rule_list:
        name = display_name(entry)

        choice.addItem(name, userData = entry["id"])

        # 如果是默认规则，直接选中
        if entry["default"]:
            choice.setCurrentText(name)

    return bool(rule_list)

class NamingConventionCard(SettingCard):
    def __init__(self, type_id = None, parent = None):
        super().__init__(FluentIcon.DOCUMENT, self.tr("Naming Convention"), self.tr("Choose the naming rule to use when downloading"), parent)

        # 未指定时回落到链接指向的那个条目，供 MCP 等拿不到勾选列表的调用方使用
        self.type_id = type_id if type_id is not None else FileNameFormatter().get_type_id_from_attribute(PreviewerInfo.attribute)

        self.rule_choice = ComboBox(parent = self)

        self.rule_group = self.hBoxLayout.addWidget(self.rule_choice, 0, Qt.AlignmentFlag.AlignRight)

        self.hBoxLayout.addSpacing(16)

        self.init_default_rules()

    def init_default_rules(self):
        # 如果查询不到数据，则说明该类型不支持自定义命名规则，禁用选择框
        if not fill_rule_choice(self.rule_choice, self.type_id):
            self.rule_choice.addItem(self.tr("Not available"))
            self.rule_choice.setEnabled(False)
            self.setContent(self.tr("Custom naming rules are not available for this type of media"))

    @property
    def rule_ids(self):
        if self.type_id is None or not self.rule_choice.isEnabled():
            return {}

        return {self.type_id: self.rule_choice.currentData()}

class MultiTypeNamingConventionCard(ExpandGroupSettingCard):
    """
    一次下载里混有多种内容类型时，逐类型选择命名规则

    解析结果里可能既有普通视频又有剧集，各自该套用自己类型的规则。只给一个
    下拉框的话，选中的那一条会被无差别套给整批任务
    """

    def __init__(self, type_ids, parent = None):
        super().__init__(
            FluentIcon.DOCUMENT,
            self.tr("Naming Convention"),
            self.tr("This batch contains multiple content types, choose a naming rule for each"),
            parent
        )

        self.rule_choices = {}

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        for type_id in sorted(type_ids):
            choice = ComboBox(parent = self)

            if fill_rule_choice(choice, type_id):
                self.rule_choices[type_id] = choice
            else:
                choice.addItem(self.tr("Not available"))
                choice.setEnabled(False)

            self.addGroup(
                "",
                Translator.CONVENTION_TYPE(reversed_convention_type_map.get(type_id)),
                "",
                choice
            )

    @property
    def rule_ids(self):
        return {type_id: choice.currentData() for type_id, choice in self.rule_choices.items()}
