import wx
from typing import Callable

from utils.config import Config

from utils.common.map import number_type_map, video_quality_map, video_codec_preference_map, video_codec_map, audio_quality_map, get_mapping_key_by_value
from utils.common.enums import StreamType, VideoQualityID, AudioQualityID, ParseType
from utils.common.thread import Thread
from utils.common.formatter.formatter import FormatUtils
from utils.common.exception import GlobalException, GlobalExceptionInfo

from utils.parse.preview import VideoPreview
from utils.parse.audio import AudioInfo

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel

from gui.dialog.confirm.video_resolution import RequireVideoResolutionDialog
from gui.dialog.error import ErrorInfoDialog

from gui.component.staticbox.extra import ExtraStaticBox
from gui.component.label.info_label import InfoLabel
from gui.component.misc.tooltip import ToolTip
from gui.component.choice.choice import Choice

class MediaInfoPanel(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.requery = False

    def init_UI(self):
        label_color = wx.Colour(64, 64, 64)

        stream_lab = wx.StaticText(self, -1, "当前视频类型：")
        self.stream_type_lab = wx.StaticText(self, -1)
        stream_type_tooltip = ToolTip(self)
        stream_type_tooltip.set_tooltip("视频格式说明：\n\nDASH：视频与音频分开存储，需要合并为一个文件\nFLV：视频与音频已合并，因此无需选择音质\nMP4：同 FLV 格式")

        stream_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        stream_type_hbox.Add(stream_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        stream_type_hbox.Add(self.stream_type_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        stream_type_hbox.Add(stream_type_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.video_quality_lab = wx.StaticText(self, -1, "清晰度")
        self.video_quality_choice = Choice(self)
        video_quality_tooltip = ToolTip(self)
        video_quality_tooltip.set_tooltip("此处显示的媒体信息为解析链接对应的单个视频\n\n若存在多个视频媒体信息不一致的情况，可能会不准确")
        
        video_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_hbox.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        video_quality_hbox.Add(video_quality_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.video_quality_warn_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))))
        self.video_quality_warn_icon.Hide()
        self.video_quality_warn_icon.SetToolTip("当前所选的清晰度与实际获取到的不符。\n\n这可能是未登录或账号未开通大会员所致。")
        self.video_quality_info_lab = InfoLabel(self, "", size = self.FromDIP((340, 16)), color = label_color)

        video_quality_info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_info_hbox.Add(self.video_quality_warn_icon, 0, wx.ALL & (~wx.TOP) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        video_quality_info_hbox.Add(self.video_quality_info_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.audio_quality_lab = wx.StaticText(self, -1, "音质")
        self.audio_quality_choice = Choice(self)
        self.audio_quality_warn_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))))
        self.audio_quality_warn_icon.Hide()
        self.audio_quality_warn_icon.SetToolTip("当前所选的音质与实际获取到的不符。\n\n这可能是未登录或账号未开通大会员所致。")
        self.audio_quality_info_lab = InfoLabel(self, "", size = self.FromDIP((340, 16)), color = label_color)

        audio_quality_info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        audio_quality_info_hbox.Add(self.audio_quality_warn_icon, 0, wx.ALL & (~wx.TOP) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        audio_quality_info_hbox.Add(self.audio_quality_info_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.video_codec_lab = wx.StaticText(self, -1, "编码格式")
        self.video_codec_choice = Choice(self)
        self.video_codec_warn_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))))
        self.video_codec_warn_icon.Hide()
        self.video_codec_warn_icon.SetToolTip("当前所选的编码与实际获取到的不符。\n\n杜比视界和HDR 视频仅支持 H.265 编码。")
        self.video_codec_info_lab = InfoLabel(self, "", size = self.FromDIP((340, 16)), color = label_color)

        video_codec_info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_codec_info_hbox.Add(self.video_codec_warn_icon, 0, wx.ALL & (~wx.TOP) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        video_codec_info_hbox.Add(self.video_codec_info_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        flex_grid_box = wx.FlexGridSizer(6, 2, 0, 0)
        flex_grid_box.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_grid_box.Add(video_quality_hbox, 0, wx.EXPAND)
        flex_grid_box.AddStretchSpacer()
        flex_grid_box.Add(video_quality_info_hbox, 0, wx.EXPAND)
        flex_grid_box.Add(self.audio_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_grid_box.Add(self.audio_quality_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        flex_grid_box.AddStretchSpacer()
        flex_grid_box.Add(audio_quality_info_hbox, 0, wx.EXPAND)
        flex_grid_box.Add(self.video_codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_grid_box.Add(self.video_codec_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        flex_grid_box.AddStretchSpacer()
        flex_grid_box.Add(video_codec_info_hbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(stream_type_hbox, 0, wx.EXPAND)
        vbox.Add(flex_grid_box, 0, wx.EXPAND)

        self.SetSizer(vbox)
    
    def Bind_EVT(self):
        self.video_quality_choice.Bind(wx.EVT_CHOICE, self.onChangeVideoQualityEVT)
        self.audio_quality_choice.Bind(wx.EVT_CHOICE, self.onChangeAudioQualityEVT)
        self.video_codec_choice.Bind(wx.EVT_CHOICE, self.onChangeVideoQualityEVT)

    def load_data(self, parent):
        from gui.window.main.main_v3 import MainWindow

        self.parent: DownloadOptionDialog = parent
        self.main_window: MainWindow = self.parent.GetParent()

        self.video_quality_choice.SetChoices(self.main_window.video_quality_data_dict)
        self.video_quality_choice.SetCurrentSelection(self.main_window.video_quality_id)

        self.audio_quality_choice.SetChoices(AudioInfo.audio_quality_data_dict)
        self.audio_quality_choice.SetCurrentSelection(AudioInfo.audio_quality_id)

        self.video_codec_choice.SetChoices(video_codec_preference_map)
        self.video_codec_choice.SetCurrentSelection(Config.Download.video_codec_id)

        self.preview = VideoPreview(self.main_window.parser.parse_type, self.main_window.stream_type)

        self.onChangeVideoQualityEVT(0)
        self.onChangeAudioQualityEVT(0)

    def save(self):
        self.main_window.parser.video_quality_id = self.video_quality_id
        AudioInfo.audio_quality_id = self.audio_quality_id
        self.main_window.parser.video_codec_id = self.video_codec_id

    def set_stream_type(self, stream_type: str):
        self.stream_type_lab.SetLabel(stream_type)
        self.stream_type = stream_type

    def parse_worker(self, worker: Callable):
        try:
            worker()

        except Exception as e:
            raise GlobalException(callback = self.onError) from e

    def get_video_quality_info(self):
        def worker():
            def get_label():
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
        
            def update_ui():
                self.video_quality_info_lab.SetLabel(get_label())
                self.video_codec_info_lab.SetLabel(get_mapping_key_by_value(video_codec_map, info["codec"]))

                video_quality_id = self.video_quality_id if self.video_quality_id != VideoQualityID._Auto.value else self.video_quality_choice.GetClientData(1)

                self.video_quality_warn_icon.Show(info["id"] != video_quality_id)
                self.video_codec_warn_icon.Show(info["codec"] != self.video_codec_id)

                self.Layout()

            info = self.preview.get_video_stream_info(self.video_quality_id, self.video_codec_id, self.requery)

            self.requery = StreamType(self.stream_type) != StreamType.Dash

            wx.CallAfter(update_ui)

        self.parse_worker(worker)

    def get_audio_quality_info(self):
        def worker():
            def get_label():
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

            def update_ui():
                self.audio_quality_info_lab.SetLabel(get_label())

                if info not in [None, "FLV", "MP4"]:
                    audio_quality_id = self.audio_quality_id if self.audio_quality_id != AudioQualityID._Auto.value else self.audio_quality_choice.GetClientData(1)

                    self.audio_quality_warn_icon.Show(info["id"] != audio_quality_id)

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

            wx.CallAfter(update_ui)

        self.parse_worker(worker)

    def onChangeVideoQualityEVT(self, event):
        self.video_quality_info_lab.SetLabel("正在检测...")
        self.video_codec_info_lab.SetLabel("正在检测...")

        Thread(target = self.get_video_quality_info).start()

    def onChangeAudioQualityEVT(self, event):
        self.audio_quality_info_lab.SetLabel("正在检测...")

        Thread(target = self.get_audio_quality_info).start()

    def enable_video_quality_group(self, enable: bool):
        self.video_quality_lab.Enable(enable)
        self.video_quality_choice.Enable(enable)
        self.video_quality_warn_icon.Enable(enable)
        self.video_quality_info_lab.Enable(enable)

        self.video_codec_lab.Enable(enable)
        self.video_codec_choice.Enable(enable)
        self.video_codec_warn_icon.Enable(enable)
        self.video_codec_info_lab.Enable(enable)

    def enable_audio_quality_group(self, enable: bool):
        self.audio_quality_lab.Enable(enable)
        self.audio_quality_choice.Enable(enable)
        self.audio_quality_warn_icon.Enable(enable)
        self.audio_quality_info_lab.Enable(enable)

    def disable_download_audio_option(self):
        self.parent.media_option_box.enable_audio_download_option(False)

    def onError(self):
        def worker():
            dlg = wx.MessageDialog(self.GetParent(), f"获取媒体信息失败\n\n错误原因：{info.get('message')}", "错误", wx.ICON_ERROR | wx.YES_NO)
            dlg.SetYesNoLabels("详细信息", "确定")

            if dlg.ShowModal() == wx.ID_YES:
                err_dlg = ErrorInfoDialog(self.main_window, info)
                err_dlg.ShowModal()

        info = GlobalExceptionInfo.info.copy()

        wx.CallAfter(worker)

    @property
    def video_quality_id(self):
        return self.video_quality_choice.GetCurrentClientData()

    @property
    def audio_quality_id(self):
        return self.audio_quality_choice.GetCurrentClientData()
    
    @property
    def video_codec_id(self):
        return self.video_codec_choice.GetCurrentClientData()

    @property
    def is_warn_show(self):
        return self.video_quality_warn_icon.Shown or self.audio_quality_warn_icon.Shown
    
class MediaOptionStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        media_box = wx.StaticBox(self, -1, "媒体下载选项")

        self.download_video_steam_chk = wx.CheckBox(media_box, -1, "视频流")
        self.video_stream_tip = ToolTip(media_box)
        self.video_stream_tip.set_tooltip('下载独立的视频流文件\n\n视频和音频分开存储，需要合并为一个完整的视频文件')

        video_stream_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_stream_hbox.Add(self.download_video_steam_chk, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        video_stream_hbox.Add(self.video_stream_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.download_audio_steam_chk = wx.CheckBox(media_box, -1, "音频流")
        self.audio_stream_tip = ToolTip(media_box)
        self.audio_stream_tip.set_tooltip('下载独立的音频流文件')

        audio_stream_hbox = wx.BoxSizer(wx.HORIZONTAL)
        audio_stream_hbox.Add(self.download_audio_steam_chk, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        audio_stream_hbox.Add(self.audio_stream_tip, 0, wx.ALL & (~wx.LEFT)| wx.ALIGN_CENTER, self.FromDIP(6))
        
        self.ffmpeg_merge_chk = wx.CheckBox(media_box, -1, "合并视频和音频")
        ffmpeg_merge_tip = ToolTip(media_box)
        ffmpeg_merge_tip.set_tooltip("选中后，在下载完成时，程序会自动将独立的视频和音频文件合并为一个完整的视频文件")

        ffmpeg_merge_hbox = wx.BoxSizer(wx.HORIZONTAL)
        ffmpeg_merge_hbox.Add(self.ffmpeg_merge_chk, 0, wx.ALL & (~wx.RIGHT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        ffmpeg_merge_hbox.Add(ffmpeg_merge_tip, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.keep_original_files_chk = wx.CheckBox(media_box, -1, "合并完成后保留原始文件")
        keep_original_files_tip = ToolTip(media_box)
        keep_original_files_tip.set_tooltip("合并完成后，保留原始的视频和音频文件")

        keep_original_files_hbox = wx.BoxSizer(wx.HORIZONTAL)
        keep_original_files_hbox.Add(self.keep_original_files_chk, 0, wx.ALL & (~wx.RIGHT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        keep_original_files_hbox.Add(keep_original_files_tip, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        media_flex_grid_box = wx.FlexGridSizer(2, 2, 0, 0)
        media_flex_grid_box.Add(video_stream_hbox, 0, wx.EXPAND)
        media_flex_grid_box.Add(audio_stream_hbox, 0, wx.EXPAND)
        media_flex_grid_box.Add(ffmpeg_merge_hbox, 0, wx.EXPAND)
        media_flex_grid_box.Add(keep_original_files_hbox, 0, wx.EXPAND)

        media_sbox = wx.StaticBoxSizer(media_box, wx.VERTICAL)
        media_sbox.Add(media_flex_grid_box, 0, wx.EXPAND)

        self.SetSizer(media_sbox)

    def Bind_EVT(self):
        self.download_video_steam_chk.Bind(wx.EVT_CHECKBOX, self.onChangeStreamDownloadOptionEVT)
        self.download_audio_steam_chk.Bind(wx.EVT_CHECKBOX, self.onChangeStreamDownloadOptionEVT)

        self.ffmpeg_merge_chk.Bind(wx.EVT_CHECKBOX, self.onEnableKeepFilesEVT)

    def load_data(self, parent):
        self.parent: DownloadOptionDialog = parent

        self.download_video_steam_chk.SetValue("video" in Config.Download.stream_download_option)
        self.download_audio_steam_chk.SetValue("audio" in Config.Download.stream_download_option)

        self.keep_original_files_chk.SetValue(Config.Merge.keep_original_files)

        self.onChangeStreamDownloadOptionEVT(0)

    def save(self):
        Config.Download.stream_download_option.clear()

        if self.download_video_steam_chk.GetValue():
            Config.Download.stream_download_option.append("video")
        
        if self.download_audio_steam_chk.GetValue():
            Config.Download.stream_download_option.append("audio")

        Config.Merge.keep_original_files = self.keep_original_files_chk.GetValue()

    def onChangeStreamDownloadOptionEVT(self, event):
        video_enable = self.download_video_steam_chk.GetValue()
        audio_enable = self.download_audio_steam_chk.GetValue()

        self.parent.media_info_box.enable_video_quality_group(video_enable)
        self.parent.media_info_box.enable_audio_quality_group(audio_enable)

        ffmpeg_merge_enable = video_enable and audio_enable

        self.ffmpeg_merge_chk.Enable(ffmpeg_merge_enable)
        self.ffmpeg_merge_chk.SetValue(ffmpeg_merge_enable)

        self.onEnableKeepFilesEVT(0)

    def onEnableKeepFilesEVT(self, event):
        enable = self.ffmpeg_merge_chk.GetValue()

        self.keep_original_files_chk.Enable(enable)
    
    def enable_audio_download_option(self, enable: bool):
        self.download_audio_steam_chk.Enable(enable)
        self.download_audio_steam_chk.SetValue(enable)

        self.onChangeStreamDownloadOptionEVT(0)

class PathStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        path_box = wx.StaticBox(self, -1, "下载目录设置")

        self.path_box = wx.TextCtrl(path_box, -1)
        self.browse_btn = wx.Button(path_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        path_sbox = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        path_sbox.Add(path_hbox, 0, wx.EXPAND)

        self.SetSizer(path_sbox)

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)

    def onBrowsePathEVT(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = self.path_box.GetValue())

        if dlg.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dlg.GetPath())

    def load_data(self):
        self.path_box.SetValue(Config.Download.path)

    def save(self):
        Config.Download.path = self.path_box.GetValue()

class OtherStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        other_box = wx.StaticBox(self, -1, "其他选项")
        
        self.auto_popup_chk = wx.CheckBox(other_box, -1, "下载时自动弹出此对话框")

        self.auto_show_download_window_chk = wx.CheckBox(other_box, -1, "自动跳转下载窗口")

        self.number_type_lab = wx.StaticText(other_box, -1, "序号类型")
        self.number_type_choice = wx.Choice(other_box, -1, choices = list(number_type_map.keys()))
        number_type_tip = ToolTip(other_box)
        number_type_tip.set_tooltip("总是从 1 开始：每次下载时，序号都从 1 开始递增\n连贯递增：每次下载时，序号都连贯递增，退出程序后重置\n使用剧集列表序号：使用在剧集列表中显示的序号\n\n请注意：自定义下载文件名模板需添加序号相关字段才会显示")

        number_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        number_type_hbox.Add(self.number_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(self.number_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(number_type_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.AddSpacer(self.FromDIP(30))

        other_sbox = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        other_sbox.Add(self.auto_popup_chk, 0, wx.ALL, self.FromDIP(6))
        other_sbox.Add(self.auto_show_download_window_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        other_sbox.Add(number_type_hbox, 0, wx.EXPAND)

        self.SetSizer(other_sbox)

    def load_data(self):
        self.auto_popup_chk.SetValue(Config.Basic.auto_popup_option_dialog)
        self.auto_show_download_window_chk.SetValue(Config.Basic.auto_show_download_window)
        self.number_type_choice.SetSelection(Config.Download.number_type)

    def save(self):
        Config.Basic.auto_popup_option_dialog = self.auto_popup_chk.GetValue()
        Config.Basic.auto_show_download_window = self.auto_show_download_window_chk.GetValue()
        Config.Download.number_type = self.number_type_choice.GetSelection()

class DownloadOptionDialog(Dialog):
    def __init__(self, parent):
        from gui.window.main.main_v3 import MainWindow

        self.parent: MainWindow = parent

        Dialog.__init__(self, parent, "下载选项")

        self.init_UI()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.media_info_box = MediaInfoPanel(self)

        self.media_option_box = MediaOptionStaticBox(self)

        self.path_box = PathStaticBox(self)

        left_vbox = wx.BoxSizer(wx.VERTICAL)
        left_vbox.Add(self.media_info_box, 0, wx.EXPAND)
        left_vbox.AddStretchSpacer()
        left_vbox.Add(self.media_option_box, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        left_vbox.Add(self.path_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.extra_box = ExtraStaticBox(self, show_more = False)

        self.other_box = OtherStaticBox(self)

        right_vbox = wx.BoxSizer(wx.VERTICAL)
        right_vbox.Add(self.extra_box, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
        right_vbox.Add(self.other_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(left_vbox, 0, wx.EXPAND)
        hbox.Add(right_vbox, 0, wx.EXPAND)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_utils(self):
        def load_download_option():
            self.media_info_box.load_data(self)

            self.media_option_box.load_data(self)

            self.path_box.load_data()

            self.extra_box.load_data()

            self.other_box.load_data()

        self.media_info_box.set_stream_type(self.parent.stream_type)

        load_download_option()

    def warn(self, message: str, flag: int = None):
        dlg = wx.MessageDialog(self, message, "警告", wx.ICON_WARNING | flag)
        dlg.SetYesNoCancelLabels("是", "否", "不再提示")

        return dlg.ShowModal()

    def check_ass_only(self):
        not_dash = StreamType(self.parent.stream_type) != StreamType.Dash
        ass_danmaku = self.extra_box.danmaku_file_type_choice.GetStringSelection() == "ass" and self.extra_box.download_danmaku_file_chk.GetValue()
        ass_subtitle = self.extra_box.subtitle_file_type_choice.GetStringSelection() == "ass" and self.extra_box.download_subtitle_file_chk.GetValue()

        Config.Temp.ass_resolution_confirm = (not self.media_option_box.download_video_steam_chk.GetValue() or not_dash) and (ass_danmaku or ass_subtitle)

        video_quality_desc_list = self.media_info_box.video_quality_choice.GetItems()
        video_quality_desc = self.media_info_box.video_quality_choice.GetStringSelection()

        if Config.Temp.ass_resolution_confirm and not Config.Temp.remember_resolution_settings:
            dlg = RequireVideoResolutionDialog(self, video_quality_desc_list, video_quality_desc, not_dash)
            
            if dlg.ShowModal() == wx.ID_OK:
                self.media_info_box.video_quality_choice.SetStringSelection(dlg.video_quality_choice.GetStringSelection())
                self.parent.parser.video_quality_id = self.media_info_box.video_quality_id
            else:
                return True

    def check_login_paid(self):
        def show_dialog(message: str):
            rtn = self.warn(message,  wx.YES_NO | wx.CANCEL)

            if rtn == wx.ID_CANCEL:
                Config.Basic.no_paid_check = True

                Config.save_app_config()

            return rtn == wx.ID_NO
        
        if not Config.Basic.no_paid_check:
            if not Config.User.login:
                return show_dialog("账号未登录\n\n账号未登录，无法下载 480P 以上清晰度视频，是否继续下载？")
            
            if self.parent.episode_list.CheckItemBadgePaid() and self.parent.parser.parse_type == ParseType.Bangumi:
                from utils.parse.bangumi import BangumiInfo

                if BangumiInfo.play_check == "PLAY_PREVIEW":
                    return show_dialog("账号未开通大会员\n\n账号未开通大会员，无法完整下载全片，仅能下载 6 分钟试看部分，是否继续下载？")

            if self.media_info_box.is_warn_show:
                return show_dialog("账号未开通大会员\n\n账号未开通大会员，无法下载 1080P 以上清晰度视频、杜比无损音质，是否继续下载？")

    def onOKEVT(self):
        if not self.path_box.path_box.GetValue():
            self.warn("保存设置失败\n\n下载目录不能为空", wx.OK)
            return True

        self.media_info_box.save()
        self.media_option_box.save()
        self.path_box.save()
        self.extra_box.save()
        self.other_box.save()

        Config.save_app_config()

        if self.check_ass_only():
            return True
        
        if self.check_login_paid():
            return True