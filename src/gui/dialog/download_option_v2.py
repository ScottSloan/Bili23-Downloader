import wx
from typing import Callable

from utils.common.map import video_quality_map, audio_quality_map, video_codec_preference_map, video_codec_map, danmaku_format_map, subtitle_format_map, number_type_map, get_mapping_index_by_value, get_mapping_key_by_value
from utils.common.enums import AudioQualityID, VideoQualityID, StreamType
from utils.config import Config, app_config_group
from utils.tool_v2 import FormatTool
from utils.common.thread import Thread

from utils.parse.audio import AudioInfo
from utils.parse.preview import Preview

from gui.dialog.custom_subtitle_lan import CustomLanDialog
from gui.dialog.custom_file_name import CustomFileNameDialog
from gui.dialog.download_sort import DownloadSortDialog

from gui.component.dialog import Dialog
from gui.component.info_label import InfoLabel
from gui.component.tooltip import ToolTip

class DownloadOptionDialog(Dialog):
    def __init__(self, parent, callback: Callable):
        from gui.main_v2 import MainWindow

        self.parent: MainWindow = parent
        self.callback = callback

        Dialog.__init__(self, parent, "下载选项")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        label_color = wx.Colour(64, 64, 64)

        self.stream_type_lab = wx.StaticText(self, -1, "当前视频流格式：")

        self.video_quality_lab = wx.StaticText(self, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self, -1)
        self.video_quality_warn_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))))
        self.video_quality_warn_icon.Hide()
        self.video_quality_warn_icon.SetToolTip("当前所选的清晰度与实际获取到的不符。\n\n这可能是未登录或账号未开通大会员所致。")
        self.video_quality_info_lab = InfoLabel(self, "", size = self.FromDIP((320, 16)), color = label_color)

        video_quality_info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_info_hbox.Add(self.video_quality_warn_icon, 0, wx.ALL & (~wx.TOP) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        video_quality_info_hbox.Add(self.video_quality_info_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.audio_quality_lab = wx.StaticText(self, -1, "音质")
        self.audio_quality_choice = wx.Choice(self, -1)
        self.audio_quality_warn_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))))
        self.audio_quality_warn_icon.Hide()
        self.audio_quality_warn_icon.SetToolTip("当前所选的音质与实际获取到的不符。\n\n这可能是未登录或账号未开通大会员所致。")
        self.audio_quality_info_lab = InfoLabel(self, "", size = self.FromDIP((320, 16)), color = label_color)

        audio_quality_info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        audio_quality_info_hbox.Add(self.audio_quality_warn_icon, 0, wx.ALL & (~wx.TOP) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        audio_quality_info_hbox.Add(self.audio_quality_info_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.video_codec_lab = wx.StaticText(self, -1, "编码格式")
        self.video_codec_choice = wx.Choice(self, -1)
        self.video_codec_warn_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))))
        self.video_codec_warn_icon.Hide()
        self.video_codec_warn_icon.SetToolTip("当前所选的编码与实际获取到的不符。\n\n杜比视界和HDR 视频仅支持 H.265 编码。")
        self.video_codec_info_lab = InfoLabel(self, "", size = self.FromDIP((320, 16)), color = label_color)

        video_codec_info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_codec_info_hbox.Add(self.video_codec_warn_icon, 0, wx.ALL & (~wx.TOP) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        video_codec_info_hbox.Add(self.video_codec_info_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        flex_grid_box = wx.FlexGridSizer(6, 2, 0, 0)
        flex_grid_box.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_grid_box.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
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

        media_box = wx.StaticBox(self, -1, "媒体下载选项")

        self.download_video_steam_chk = wx.CheckBox(media_box, -1, "视频流")
        self.video_stream_tip = ToolTip(media_box)
        self.video_stream_tip.set_tooltip('下载独立的视频流文件\n\n独立的视频流不包含音轨，若需要下载带音轨的视频，请一并勾选"音频流"和"合并视频和音频"选项')

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

        left_vbox = wx.BoxSizer(wx.VERTICAL)
        left_vbox.Add(self.stream_type_lab, 0, wx.ALL, self.FromDIP(6))
        left_vbox.Add(flex_grid_box, 0, wx.EXPAND)
        left_vbox.AddStretchSpacer()
        left_vbox.Add(media_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        extra_box = wx.StaticBox(self, -1, "附加内容下载选项")

        self.download_danmaku_file_chk = wx.CheckBox(extra_box, -1, "下载视频弹幕")
        self.danmaku_file_type_lab = wx.StaticText(extra_box, -1, "弹幕文件格式")
        self.danmaku_file_type_choice = wx.Choice(extra_box, -1, choices = list(danmaku_format_map.keys()))

        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(self.FromDIP(20))
        danmaku_hbox.Add(self.danmaku_file_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        danmaku_hbox.Add(self.danmaku_file_type_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        danmaku_hbox.AddSpacer(self.FromDIP(60))

        self.download_subtitle_file_chk = wx.CheckBox(extra_box, -1, "下载视频字幕")
        self.subtitle_file_type_lab = wx.StaticText(extra_box, -1, "字幕文件格式")
        self.subtitle_file_type_choice = wx.Choice(extra_box, -1, choices = list(subtitle_format_map.keys()))
        self.subtitle_file_lan_type_lab = wx.StaticText(extra_box, -1, "字幕语言")
        self.subtitle_file_lan_type_btn = wx.Button(extra_box, -1, "自定义")

        subtitle_grid_box = wx.FlexGridSizer(2, 4, 0, 0)
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.Add(self.subtitle_file_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_grid_box.Add(self.subtitle_file_type_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.Add(self.subtitle_file_lan_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_grid_box.Add(self.subtitle_file_lan_type_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))

        self.download_cover_file_chk = wx.CheckBox(extra_box, -1, "下载视频封面")

        extra_sbox = wx.StaticBoxSizer(extra_box, wx.VERTICAL)
        extra_sbox.Add(self.download_danmaku_file_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        extra_sbox.Add(danmaku_hbox, 0, wx.EXPAND)
        extra_sbox.Add(self.download_subtitle_file_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        extra_sbox.Add(subtitle_grid_box, 0, wx.EXPAND)
        extra_sbox.Add(self.download_cover_file_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        other_box = wx.StaticBox(self, -1, "其他选项")
        
        self.auto_popup_chk = wx.CheckBox(other_box, -1, "下载时自动弹出此对话框")
        self.auto_add_number_chk = wx.CheckBox(other_box, -1, "自动添加序号")
        self.number_type_lab = wx.StaticText(other_box, -1, "序号类型")
        self.number_type_choice = wx.Choice(other_box, -1, choices = list(number_type_map.keys()))
        number_type_tip = ToolTip(other_box)
        number_type_tip.set_tooltip("总是从 1 开始：每次下载时，序号都从 1 开始递增\n连贯递增：每次下载时，序号都连贯递增，退出程序后重置\n使用剧集列表序号：使用在剧集列表中显示的序号\n\n请注意：自定义下载文件名需添加 {number} 或者 {number_with_zero} 字段才会显示")

        number_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        number_type_hbox.AddSpacer(self.FromDIP(20))
        number_type_hbox.Add(self.number_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(self.number_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(number_type_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.AddSpacer(self.FromDIP(60))

        other_sbox = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        other_sbox.Add(self.auto_popup_chk, 0, wx.ALL, self.FromDIP(6))
        other_sbox.Add(self.auto_add_number_chk, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        other_sbox.Add(number_type_hbox, 0, wx.EXPAND)

        right_vbox = wx.BoxSizer(wx.VERTICAL)
        right_vbox.Add(extra_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        right_vbox.AddStretchSpacer()
        right_vbox.Add(other_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(left_vbox, 0, wx.EXPAND)
        hbox.Add(right_vbox, 0, wx.EXPAND)

        path_box = wx.StaticBox(self, -1, "下载目录&&高级选项")

        self.path_box = wx.TextCtrl(path_box, -1)
        self.browse_btn = wx.Button(path_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        self.custom_file_name_btn = wx.Button(path_box, -1, "文件名...", size = self.get_scaled_size((60, 24)))
        self.download_sort_btn = wx.Button(path_box, -1, "分类...", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        path_hbox.Add(self.custom_file_name_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        path_hbox.Add(self.download_sort_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        path_sbox = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        path_sbox.Add(path_hbox, 0, wx.EXPAND)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(path_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.video_quality_choice.Bind(wx.EVT_CHOICE, self.onChangeVideoQualityCodecEVT)
        self.audio_quality_choice.Bind(wx.EVT_CHOICE, self.onChangeAudioQualityEVT)
        self.video_codec_choice.Bind(wx.EVT_CHOICE, self.onChangeVideoQualityCodecEVT)

        self.download_video_steam_chk.Bind(wx.EVT_CHECKBOX, self.onChangeStreamDownloadOptionEVT)
        self.download_audio_steam_chk.Bind(wx.EVT_CHECKBOX, self.onChangeStreamDownloadOptionEVT)

        self.download_danmaku_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadDanmakuEVT)
        self.download_subtitle_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadSubtitleEVT)
        self.download_cover_file_chk.Bind(wx.EVT_CHECKBOX, self.onEnableOKBtnEVT)

        self.subtitle_file_lan_type_btn.Bind(wx.EVT_BUTTON, self.onCustomSubtitleLanEVT)

        self.auto_popup_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAutoPopupEVT)
        self.auto_add_number_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAutoAddNumberEVT)

        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)
        self.custom_file_name_btn.Bind(wx.EVT_BUTTON, self.onCustomFileNameEVT)
        self.download_sort_btn.Bind(wx.EVT_BUTTON, self.onDownloadSortEVT)

        self.ffmpeg_merge_chk.Bind(wx.EVT_CHECKBOX, self.onEnableKeepFilesEVT)

        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirmEVT)

    def init_utils(self):
        def get_stream_type():
            match StreamType(self.parent.stream_type):
                case StreamType.Dash:
                    lab = "DASH"

                case StreamType.Flv:
                    lab = "FLV"
            
            self.stream_type_lab.SetLabel(f"当前视频流格式：{lab}")

        get_stream_type()

        self.load_download_option()

        self.onChangeStreamDownloadOptionEVT(0)
        self.onCheckDownloadDanmakuEVT(0)
        self.onCheckDownloadSubtitleEVT(0)

        self.preview = Preview(self.parent.current_parse_type, self.parent.stream_type)

        self.onChangeVideoQualityCodecEVT(0)
        self.onChangeAudioQualityEVT(0)

        self.onCheckAutoAddNumberEVT(0)

        self.onEnableKeepFilesEVT(0)

    def load_download_option(self):
        def set_audio_quality_list():
            audio_quality_id_list = AudioInfo.audio_quality_id_list.copy()
            audio_quality_desc_list = AudioInfo.audio_quality_desc_list.copy()

            audio_quality_id_list.insert(0, AudioQualityID._Auto.value)
            audio_quality_desc_list.insert(0, "自动")

            self.audio_quality_choice.Set(audio_quality_desc_list)
            
            if Config.Download.audio_quality_id in audio_quality_id_list:
                self.audio_quality_choice.Select(audio_quality_id_list.index(Config.Download.audio_quality_id))
            else:
                self.audio_quality_choice.Select(1)

        def set_stream_download_option():
            self.download_video_steam_chk.SetValue("video" in Config.Download.stream_download_option)
            self.download_audio_steam_chk.SetValue("audio" in Config.Download.stream_download_option)

        self.video_quality_choice.Set(self.parent.video_quality_choice.GetItems())
        self.video_quality_choice.Select(self.parent.video_quality_choice.GetSelection())

        set_audio_quality_list()

        self.video_codec_choice.Set(list(video_codec_preference_map.keys()))
        self.video_codec_choice.Select(get_mapping_index_by_value(video_codec_preference_map, Config.Download.video_codec_id))

        set_stream_download_option()

        self.download_danmaku_file_chk.SetValue(Config.Basic.download_danmaku_file)
        self.danmaku_file_type_choice.Select(Config.Basic.danmaku_file_type)
        self.download_subtitle_file_chk.SetValue(Config.Basic.download_subtitle_file)
        self.subtitle_file_type_choice.Select(Config.Basic.subtitle_file_type)
        self.download_cover_file_chk.SetValue(Config.Basic.download_cover_file)

        self.auto_popup_chk.SetValue(Config.Basic.auto_popup_option_dialog)
        self.auto_add_number_chk.SetValue(Config.Download.auto_add_number)
        self.number_type_choice.SetSelection(Config.Download.number_type)

        self.ffmpeg_merge_chk.SetValue(Config.Download.ffmpeg_merge)
        self.keep_original_files_chk.SetValue(Config.Merge.keep_original_files)

        self.path_box.SetValue(Config.Download.path)

        Config.Temp.file_name_template = Config.Advanced.file_name_template
        Config.Temp.datetime_format = Config.Advanced.datetime_format
        Config.Temp.auto_adjust_field = Config.Advanced.auto_adjust_field
        Config.Temp.enable_download_sort = Config.Advanced.enable_download_sort
        Config.Temp.sort_by_up = Config.Advanced.sort_by_up
        Config.Temp.sort_by_collection = Config.Advanced.sort_by_collection
        Config.Temp.sort_by_series = Config.Advanced.sort_by_series
    
    def onChangeVideoQualityCodecEVT(self, event):
        def worker():
            def get_video_quality_info_label():
                if not info:
                    return "未知"

                match StreamType(self.parent.stream_type):
                    case StreamType.Dash:

                        return "[{}]   [{}]   [{}]   [{}]".format(get_mapping_key_by_value(video_quality_map, info["video_quality_id"]), info["frame_rate"], FormatTool.format_bandwidth(info["bandwidth"]), FormatTool.format_size(info["size"]))
                    
                    case StreamType.Flv:
                        self.video_stream_tip.set_tooltip("下载独立的视频流文件\n\nFLV 格式视频已包含音轨")

                        return "[{}]   [{}]".format(get_mapping_key_by_value(video_quality_map, info["video_quality_id"]), FormatTool.format_size(info["size"]))
            
            def callback():
                def check():
                    if self.video_quality_id == VideoQualityID._Auto.value:
                        if info:
                            video_quality_id = video_quality_map.get(self.video_quality_choice.GetString(1))
                        else:
                            video_quality_id = VideoQualityID._None.value
                    else:
                        video_quality_id = self.video_quality_id

                    if info["video_quality_id"] != video_quality_id:
                        self.video_quality_warn_icon.Show()
                    else:
                        self.video_quality_warn_icon.Hide()

                    if info["video_codec_id"] != self.video_codec_id:
                        self.video_codec_warn_icon.Show()
                    else:
                        self.video_codec_warn_icon.Hide()

                    self.Layout()

                self.video_quality_info_lab.SetLabel(video_quality_info_label)
                self.video_codec_info_lab.SetLabel(video_codec_info_label)

                check()

            info = self.preview.get_video_stream_info(self.video_quality_id, self.video_codec_id)

            video_quality_info_label = get_video_quality_info_label()
            video_codec_info_label = get_mapping_key_by_value(video_codec_map, info["video_codec_id"])

            wx.CallAfter(callback)

        self.video_quality_info_lab.SetLabel("正在检测...")
        self.video_codec_info_lab.SetLabel("正在检测...")

        Thread(target = worker).start()

    def onChangeAudioQualityEVT(self, event):
        def worker():
            def get_audio_quality_info_label():
                def check():
                    if self.audio_quality_id == AudioQualityID._Auto.value:
                        if self.audio_quality_choice.GetCount() > 1:
                            audio_quality_id = audio_quality_map.get(self.audio_quality_choice.GetString(1))
                        else:
                            audio_quality_id = AudioQualityID._None.value
                    else:
                        audio_quality_id = self.audio_quality_id

                    if info["audio_quality_id"] != audio_quality_id:
                        self.audio_quality_warn_icon.Show()
                    else:
                        self.audio_quality_warn_icon.Hide()

                    self.Layout()

                def disable_download_audio_option():
                    self.audio_quality_choice.Enable(False)

                    self.download_audio_steam_chk.SetValue(False)
                    self.download_audio_steam_chk.Enable(False)

                    self.onChangeStreamDownloadOptionEVT(event)

                match StreamType(self.parent.stream_type):
                    case StreamType.Dash:
                        if AudioInfo.Availability.audio:
                            wx.CallAfter(check)

                            if info:
                                self.audio_stream_tip.set_tooltip("下载独立的音频流文件")

                                return "[{}]   [{}]   [{}]".format(get_mapping_key_by_value(audio_quality_map, info["audio_quality_id"]), FormatTool.format_bandwidth(info["bandwidth"]), FormatTool.format_size(info["size"]))
                            else:
                                return "未知"
                        else:
                            wx.CallAfter(disable_download_audio_option)

                            self.audio_stream_tip.set_tooltip("下载独立的音频流文件\n\n此视频无音轨")

                            return "此视频无音轨"
                    
                    case StreamType.Flv:
                        wx.CallAfter(disable_download_audio_option)

                        self.audio_stream_tip.set_tooltip("下载独立的音频流文件\n\nFLV 格式视频已包含音轨")

                        return "FLV 格式视频已包含音轨，不支持自定义音质"

            info = self.preview.get_audio_stream_size(self.audio_quality_id)

            audio_info_label = get_audio_quality_info_label()
            wx.CallAfter(self.audio_quality_info_lab.SetLabel, audio_info_label)

        self.audio_quality_info_lab.SetLabel("正在检测...")

        Thread(target = worker).start()

    def onChangeStreamDownloadOptionEVT(self, event):
        def set_video_quality_enable(enable: bool):
            self.video_quality_lab.Enable(enable)
            self.video_quality_choice.Enable(enable)
            self.video_quality_info_lab.Enable(enable)

            self.video_codec_lab.Enable(enable)
            self.video_codec_choice.Enable(enable)
            self.video_codec_info_lab.Enable(enable)

        def set_audio_quality_enable(enable: bool):
            self.audio_quality_lab.Enable(enable)
            self.audio_quality_choice.Enable(enable)
            self.audio_quality_info_lab.Enable(enable)

        set_video_quality_enable(self.download_video_steam_chk.GetValue())
        set_audio_quality_enable(self.download_audio_steam_chk.GetValue())

        enable = self.download_video_steam_chk.GetValue() and self.download_audio_steam_chk.GetValue()

        self.ffmpeg_merge_chk.Enable(enable)
        self.ffmpeg_merge_chk.SetValue(enable)

        self.onEnableOKBtnEVT(event)
        self.onEnableKeepFilesEVT(event)

    def onCheckDownloadDanmakuEVT(self, event):
        enable = self.download_danmaku_file_chk.GetValue()

        self.danmaku_file_type_lab.Enable(enable)
        self.danmaku_file_type_choice.Enable(enable)

        self.onEnableOKBtnEVT(event)

    def onCheckDownloadSubtitleEVT(self, event):
        enable = self.download_subtitle_file_chk.GetValue()

        self.subtitle_file_type_lab.Enable(enable)
        self.subtitle_file_type_choice.Enable(enable)
        self.subtitle_file_lan_type_lab.Enable(enable)
        self.subtitle_file_lan_type_btn.Enable(enable)

        self.onEnableOKBtnEVT(event)

    def onCustomSubtitleLanEVT(self, event):
        dlg = CustomLanDialog(self)
        dlg.ShowModal()

    def onCheckAutoPopupEVT(self, event):
        Config.Basic.auto_popup_option_dialog = self.auto_popup_chk.GetValue()

        Config.save_config_group(Config, app_config_group, Config.APP.app_config_path)

    def onCheckAutoAddNumberEVT(self, event):
        enable = self.auto_add_number_chk.GetValue()

        self.number_type_lab.Enable(enable)
        self.number_type_choice.Enable(enable)

    def onEnableOKBtnEVT(self, event):
        enable = (self.download_video_steam_chk.GetValue() or self.download_audio_steam_chk.GetValue()) or (self.download_danmaku_file_chk.GetValue() or self.download_subtitle_file_chk.GetValue() or self.download_cover_file_chk.GetValue())
        
        self.ok_btn.Enable(enable)

    def onBrowsePathEVT(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = self.path_box.GetValue())

        if dlg.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dlg.GetPath())

        dlg.Destroy()

    def onCustomFileNameEVT(self, event):
        dlg = CustomFileNameDialog(self)
        dlg.ShowModal()
    
    def onDownloadSortEVT(self, event):
        dlg = DownloadSortDialog(self)
        dlg.ShowModal()

    def onEnableKeepFilesEVT(self, event):
        enable = self.ffmpeg_merge_chk.GetValue()

        self.keep_original_files_chk.Enable(enable)
        
        if enable:
            self.keep_original_files_chk.SetValue(Config.Merge.keep_original_files)

    def onConfirmEVT(self, event):
        def set_stream_download_option():
            Config.Download.stream_download_option.clear()

            if self.download_video_steam_chk.GetValue():
                Config.Download.stream_download_option.append("video")
            
            if self.download_audio_steam_chk.GetValue():
                Config.Download.stream_download_option.append("audio")

        AudioInfo.audio_quality_id = audio_quality_map.get(self.audio_quality_choice.GetStringSelection())
        Config.Download.video_codec_id = self.video_codec_id

        set_stream_download_option()

        Config.Basic.download_danmaku_file = self.download_danmaku_file_chk.GetValue()
        Config.Basic.danmaku_file_type = self.danmaku_file_type_choice.GetSelection()
        Config.Basic.download_subtitle_file = self.download_subtitle_file_chk.GetValue()
        Config.Basic.subtitle_file_type = self.subtitle_file_type_choice.GetSelection()
        Config.Basic.download_cover_file = self.download_cover_file_chk.GetValue()

        Config.Download.auto_add_number = self.auto_add_number_chk.GetValue()
        Config.Download.number_type = self.number_type_choice.GetSelection()

        Config.Download.path = self.path_box.GetValue()

        Config.Download.ffmpeg_merge = self.ffmpeg_merge_chk.GetValue()
        Config.Merge.keep_original_files = self.keep_original_files_chk.GetValue()

        Config.Advanced.file_name_template = Config.Temp.file_name_template
        Config.Advanced.datetime_format = Config.Temp.datetime_format
        Config.Advanced.auto_adjust_field = Config.Temp.auto_adjust_field
        Config.Advanced.enable_download_sort = Config.Temp.enable_download_sort
        Config.Advanced.sort_by_up = Config.Temp.sort_by_up
        Config.Advanced.sort_by_collection = Config.Temp.sort_by_collection
        Config.Advanced.sort_by_series = Config.Temp.sort_by_series

        self.callback(self.video_quality_choice.GetSelection(), self.video_quality_choice.IsEnabled())

        event.Skip()

    @property
    def video_quality_id(self):
        return video_quality_map.get(self.video_quality_choice.GetStringSelection())
    
    @property
    def audio_quality_id(self):
        return audio_quality_map.get(self.audio_quality_choice.GetStringSelection())
    
    @property
    def video_codec_id(self):
        return video_codec_preference_map.get(self.video_codec_choice.GetStringSelection())
