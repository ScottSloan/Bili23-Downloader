import wx
from typing import Callable

from utils.config import Config
from utils.common.enums import StreamType, VideoQualityID
from utils.common.formatter.formatter import FormatUtils
from utils.common.exception import GlobalException, show_error_message_dialog
from utils.common.map import video_quality_map, audio_quality_map, video_codec_map, video_codec_preference_map, get_mapping_key_by_value
from utils.common.thread import Thread
from utils.common.style.color import Color
from utils.common.style.icon_v4 import Icon, IconID

from utils.parse.preview import VideoPreview, PreviewInfo
from utils.parse.audio import AudioInfo, AudioQualityID

from gui.component.panel.panel import Panel
from gui.component.misc.tooltip import ToolTip
from gui.component.choice.choice import Choice
from gui.component.staticbitmap.staticbitmap import StaticBitmap
from gui.component.label.info_label import InfoLabel
from gui.component.button.bitmap_button import BitmapButton

class InfoGroup(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        self.choice = Choice(self)
        self.tooltip = ToolTip(self)
        self.tooltip.Hide()

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(self.choice, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.warn_icon = StaticBitmap(self, bmp = wx.ArtProvider().GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))), size = self.FromDIP((16, 16)))
        self.warn_icon.Hide()
        self.info_lab = InfoLabel(self, "", size = self.FromDIP((340, 16)), color = Color.get_label_text_color())

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.warn_icon, 0, wx.ALL & (~wx.TOP) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.Add(self.info_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def SetTopToolTip(self, tooltip: str):
        self.tooltip.set_tooltip(tooltip)
        self.tooltip.Show(True)

    def SetBottomToolTip(self, tooltip: str):
        self.warn_icon.SetToolTip(tooltip)

    def SetChoice(self, choices: dict, selection: int):
        self.choice.SetChoices(choices)
        self.choice.SetCurrentSelection(selection)

    def SetCheckingStatus(self):
        self.info_lab.SetLabel("正在检测...")

    def SetEnable(self, enable: bool):
        self.choice.Enable(enable)
        self.tooltip.Enable(enable)

        self.warn_icon.Enable(enable)
        self.info_lab.Enable(enable)

    def SetInfoLabel(self, label: str):
        self.info_lab.SetLabel(label)

    def ShowWarnIcon(self, show: bool):
        self.warn_icon.Show(show)

class MediaInfoPanel(Panel):
    def __init__(self, parent: wx.Window):
        from gui.dialog.download_option.download_option_dialog import DownloadOptionDialog

        self.parent: DownloadOptionDialog = parent

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.requery = False

    def init_UI(self):
        media_info_box = wx.StaticBox(self, -1, "媒体信息")

        stream_lab = wx.StaticText(media_info_box, -1, "当前视频类型：")
        self.stream_type_lab = wx.StaticText(media_info_box, -1, "正在检测...")
        stream_type_tooltip = ToolTip(media_info_box)
        stream_type_tooltip.set_tooltip("视频格式说明：\n\nDASH：视频与音频分开存储，需要合并为一个文件\nFLV：视频与音频已合并，因此无需选择音质\nMP4：同 FLV 格式")
        self.help_btn = BitmapButton(media_info_box, Icon.get_icon_bitmap(IconID.Help), tooltip = "查看帮助")

        stream_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        stream_type_hbox.Add(stream_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        stream_type_hbox.Add(self.stream_type_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        stream_type_hbox.Add(stream_type_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        stream_type_hbox.AddStretchSpacer()
        stream_type_hbox.Add(self.help_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.video_quality_lab = wx.StaticText(media_info_box, -1, "清晰度")
        self.video_quality_info = InfoGroup(media_info_box)
        self.video_quality_info.SetTopToolTip("此处显示的媒体信息为解析链接对应的单个视频\n\n若存在多个视频媒体信息不一致的情况，可能会不准确")
        self.video_quality_info.SetBottomToolTip("当前所选的清晰度与实际获取到的不符。\n\n这可能是未登录或账号未开通大会员所致。")

        self.audio_quality_lab = wx.StaticText(media_info_box, -1, "音质")
        self.audio_quality_info = InfoGroup(media_info_box)
        self.audio_quality_info.SetBottomToolTip("当前所选的音质与实际获取到的不符。\n\n这可能是未登录或账号未开通大会员所致。")

        self.video_codec_lab = wx.StaticText(media_info_box, -1, "编码格式")
        self.video_codec_info = InfoGroup(media_info_box)
        self.video_codec_info.SetBottomToolTip("当前所选的编码与实际获取到的不符。\n\n杜比视界和HDR 视频仅支持 H.265 编码。")

        flex_grid_box = wx.FlexGridSizer(3, 2, 0, 0)
        flex_grid_box.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_grid_box.Add(self.video_quality_info, 0, wx.EXPAND)

        flex_grid_box.Add(self.audio_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_grid_box.Add(self.audio_quality_info, 0, wx.EXPAND)

        flex_grid_box.Add(self.video_codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_grid_box.Add(self.video_codec_info, 0, wx.EXPAND)

        media_info_sbox = wx.StaticBoxSizer(media_info_box, wx.VERTICAL)
        media_info_sbox.Add(stream_type_hbox, 0, wx.EXPAND)
        media_info_sbox.Add(flex_grid_box, 0, wx.EXPAND)

        self.SetSizer(media_info_sbox)
    
    def Bind_EVT(self):
        self.video_quality_info.choice.Bind(wx.EVT_CHOICE, self.onChangeVideoQualityEVT)
        self.audio_quality_info.choice.Bind(wx.EVT_CHOICE, self.onChangeAudioQualityEVT)
        self.video_codec_info.choice.Bind(wx.EVT_CHOICE, self.onChangeVideoQualityEVT)

        self.help_btn.Bind(wx.EVT_BUTTON, self.onHelpEVT)

    def load_data(self):
        from gui.window.main.main_v3 import MainWindow

        self.main_window: MainWindow = self.parent.GetParent()

        self.preview = VideoPreview(self.main_window.parser.parse_type)

        AudioInfo.clear_audio_info()

        AudioInfo.get_audio_quality_list(PreviewInfo.download_json.get("dash", {}))

        video_quality_id = self.preview.get_video_quality_id(Config.Download.video_quality_id, self.preview.download_json) if Config.Download.video_quality_id != VideoQualityID._Auto.value else Config.Download.video_quality_id
        video_quality_data_dict = self.preview.get_video_quality_data_dict(self.preview.download_json)

        self.video_quality_info.SetChoice(video_quality_data_dict, video_quality_id)
        self.audio_quality_info.SetChoice(AudioInfo.audio_quality_data_dict, AudioInfo.audio_quality_id)
        self.video_codec_info.SetChoice(video_codec_preference_map, Config.Download.video_codec_id)

        self.onChangeVideoQualityEVT(0)
        self.onChangeAudioQualityEVT(0)

    def save(self):
        Config.Download.video_quality_id = self.video_quality_id
        Config.Download.audio_quality_id = self.audio_quality_id
        Config.Download.video_codec_id = self.video_codec_id

    def set_stream_type(self, stream_type: str):
        self.stream_type_lab.SetLabel(stream_type)

    def parse_worker(self, worker: Callable):
        try:
            worker()

        except Exception as e:
            raise GlobalException(callback = self.onError) from e

    def get_video_quality_info(self):
        def worker():
            def update_ui():
                is_drm = wx.FindWindowByName("main").parser.parser.is_drm

                video_quality_id = self.video_quality_id if self.video_quality_id != VideoQualityID._Auto.value else self.video_quality_info.choice.GetClientData(1)
                
                self.video_quality_info.SetInfoLabel(info_label)
                self.video_codec_info.SetInfoLabel(get_mapping_key_by_value(video_codec_map, info["codec"]))

                self.video_quality_info.ShowWarnIcon(info["id"] != video_quality_id or is_drm)
                self.video_codec_info.ShowWarnIcon(info["codec"] != self.video_codec_id)

                if is_drm:
                    self.video_quality_info.SetBottomToolTip("此视频采用 WideVine DRM 技术加密，不支持下载 1080P 以上的清晰度。")
                else:
                    self.video_quality_info.SetBottomToolTip("当前所选的清晰度与实际获取到的不符。\n\n这可能是未登录或账号未开通大会员所致。")

                self.video_quality_info.SetTopToolTip("此处显示的媒体信息为解析链接对应的单个视频\n\n若存在多个视频媒体信息不一致的情况，可能会不准确\n\n当前显示的媒体信息所对应的视频：{}".format(self.parent.episode_info.get("title")))

                self.set_stream_type(self.stream_type)

                self.Layout()

            info = self.preview.get_video_stream_info(self.episode_params, self.requery)

            self.requery = StreamType(self.stream_type) != StreamType.Dash

            info_label = self.get_video_quality_label(info)

            wx.CallAfter(update_ui)

        self.parse_worker(worker)

    def get_video_quality_label(self, info: dict):
        match StreamType(self.stream_type):
            case StreamType.Dash:
                label_info = {
                    "desc": get_mapping_key_by_value(video_quality_map, info["id"]),
                    "frame_rate": info["framerate"],
                    "bandwidth": FormatUtils.format_bandwidth(info["bandwidth"]),
                    "size": FormatUtils.format_size(info["size"])
                }
            
            case StreamType.Flv:
                label_info = {
                    "desc": get_mapping_key_by_value(video_quality_map, info["id"]),
                    "seg": "分段" if info["seg"] > 1 else "连贯",
                    "size": FormatUtils.format_size(info["size"])
                }

            case StreamType.Mp4:
                label_info = {
                    "desc": get_mapping_key_by_value(video_quality_map, info["id"]),
                    "size": FormatUtils.format_size(info["size"])
                }

        return "   ".join([f"[{value}]" for value in label_info.values()])

    def get_audio_quality_info(self):
        def worker():
            def update_ui():
                self.audio_quality_info.SetInfoLabel(info_label)

                if info not in [None, "FLV", "MP4"]:
                    audio_quality_id = self.audio_quality_id if self.audio_quality_id != AudioQualityID._Auto.value else self.audio_quality_info.choice.GetClientData(1)
                    
                    self.audio_quality_info.ShowWarnIcon(info["id"] != audio_quality_id)

                    self.Layout()

                else:
                    self.enable_audio_quality_group(False)

                    self.disable_download_audio_option()

            match StreamType(self.stream_type):
                case StreamType.Dash:
                    if AudioInfo.audio:
                        info = self.preview.get_audio_stream_info(self.audio_quality_id)
                    else:
                        info = None

                case StreamType.Flv:
                    info = "FLV"

                case StreamType.Mp4:
                    info = "MP4"

            info_label = self.get_audio_quality_label(info)

            wx.CallAfter(update_ui)

        self.parse_worker(worker)

    def get_audio_quality_label(self, info: dict):
        match info:
            case None:
                return "此视频无音轨"
            
            case "FLV":
                return "FLV 格式视频流中已包含音轨，不支持自定义"
            
            case "MP4":
                return "MP4 格式视频流中已包含音轨，不支持自定义"
            
            case _:
                label_info = {
                    "desc": get_mapping_key_by_value(audio_quality_map, info["id"]),
                    "codec": info["codec"],
                    "bandwidth": FormatUtils.format_bandwidth(info["bandwidth"]),
                    "size": FormatUtils.format_size(info["size"])
                }

                return "   ".join([f"[{value}]" for value in label_info.values()])

    def onChangeVideoQualityEVT(self, event: wx.CommandEvent):
        self.video_quality_info.SetCheckingStatus()
        self.video_codec_info.SetCheckingStatus()

        Thread(target = self.get_video_quality_info).start()

    def onChangeAudioQualityEVT(self, event: wx.CommandEvent):
        self.audio_quality_info.SetCheckingStatus()

        Thread(target = self.get_audio_quality_info).start()

    def enable_video_quality_group(self, enable: bool):
        self.video_quality_lab.Enable(enable)
        self.video_quality_info.SetEnable(enable)

        self.video_codec_lab.Enable(enable)
        self.video_codec_info.SetEnable(enable)

    def enable_audio_quality_group(self, enable: bool):
        self.audio_quality_lab.Enable(enable)
        self.audio_quality_info.SetEnable(enable)

    def disable_download_audio_option(self):
        self.parent.media_option_box.enable_audio_download_option(False)

    def onError(self):
        show_error_message_dialog("获取媒体信息失败", parent = self.parent)

    def onHelpEVT(self, event: wx.CommandEvent):
        wx.LaunchDefaultBrowser("https://bili23.scott-sloan.cn/doc/faq/download.html#%E8%A7%86%E9%A2%91%E6%B8%85%E6%99%B0%E5%BA%A6%E4%B8%8E%E4%B8%8B%E8%BD%BD%E8%AE%BE%E7%BD%AE%E4%B8%8D%E7%AC%A6")

    @property
    def video_quality_id(self):
        return self.video_quality_info.choice.GetCurrentClientData()

    @property
    def audio_quality_id(self):
        return self.audio_quality_info.choice.GetCurrentClientData()
    
    @property
    def video_codec_id(self):
        return self.video_codec_info.choice.GetCurrentClientData()

    @property
    def stream_type(self):
        return self.preview.stream_type
    
    @property
    def episode_params(self):
        return {
            "bvid": self.parent.episode_info.get("bvid"),
            "cid": self.parent.episode_info.get("cid"),
            "aid": self.parent.episode_info.get("aid"),
            "ep_id": self.parent.episode_info.get("ep_id"),
            "qn": self.video_quality_id,
            "codec": self.video_codec_id
        }
