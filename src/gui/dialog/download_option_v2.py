import wx
from typing import Callable

from utils.common.map import audio_quality_map, video_codec_preference_map, danmaku_format_map, subtitle_format_map, get_mapping_index_by_value
from utils.common.enums import AudioQualityID, DownloadOption
from utils.config import Config, config_utils

from utils.parse.audio import AudioInfo

from gui.component.dialog import Dialog

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
        self.video_quality_lab = wx.StaticText(self, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self, -1)
        self.video_quality_info_lab = wx.StaticText(self, -1, "约 356.5 MB")

        self.audio_quality_lab = wx.StaticText(self, -1, "音质")
        self.audio_quality_choice = wx.Choice(self, -1)
        self.audio_quality_info_lab = wx.StaticText(self, -1, "约 18.6 MB")

        self.video_codec_lab = wx.StaticText(self, -1, "编码格式")
        self.video_codec_choice = wx.Choice(self, -1)
        self.video_codec_info_lab = wx.StaticText(self, -1)

        flex_grid_box = wx.FlexGridSizer(3, 3, 0, 0)
        flex_grid_box.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        flex_grid_box.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)
        flex_grid_box.Add(self.video_quality_info_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        flex_grid_box.Add(self.audio_quality_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        flex_grid_box.Add(self.audio_quality_choice, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP), 10)
        flex_grid_box.Add(self.audio_quality_info_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        flex_grid_box.Add(self.video_codec_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        flex_grid_box.Add(self.video_codec_choice, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP), 10)
        flex_grid_box.Add(self.video_codec_info_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        media_box = wx.StaticBox(self, -1, "音视频下载选项")

        self.download_none_radio = wx.RadioButton(media_box, -1, "不下载")
        self.download_video_radio = wx.RadioButton(media_box, -1, "仅下载视频")
        self.download_audio_radio = wx.RadioButton(media_box, -1, "仅下载音频")
        self.download_both_radio = wx.RadioButton(media_box, -1, "下载视频和音频")
        self.use_ffmpeg_chk = wx.CheckBox(media_box, -1, "使用 FFmpeg 合并视频和音频")

        media_sbox = wx.StaticBoxSizer(media_box, wx.VERTICAL)
        media_sbox.Add(self.download_none_radio, 0, wx.ALL, 10)
        media_sbox.Add(self.download_video_radio, 0, wx.ALL & (~wx.TOP), 10)
        media_sbox.Add(self.download_audio_radio, 0, wx.ALL & (~wx.TOP), 10)
        media_sbox.Add(self.download_both_radio, 0, wx.ALL & (~wx.TOP), 10)
        media_sbox.Add(self.use_ffmpeg_chk, 0, wx.ALL & (~wx.TOP), 10)

        left_vbox = wx.BoxSizer(wx.VERTICAL)
        left_vbox.Add(flex_grid_box, 0, wx.EXPAND)
        left_vbox.Add(media_sbox, 1, wx.ALL | wx.EXPAND, 10)

        extra_box = wx.StaticBox(self, -1, "附加内容下载选项")

        self.download_danmaku_file_chk = wx.CheckBox(extra_box, -1, "下载视频弹幕")
        self.danmaku_file_type_lab = wx.StaticText(extra_box, -1, "弹幕文件格式")
        self.danmaku_file_type_choice = wx.Choice(extra_box, -1, choices = list(danmaku_format_map.keys()))

        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(self.FromDIP(20))
        danmaku_hbox.Add(self.danmaku_file_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        danmaku_hbox.Add(self.danmaku_file_type_choice, 0, wx.ALL & (~wx.LEFT), 10)
        danmaku_hbox.AddSpacer(self.FromDIP(20))

        self.download_subtitle_file_chk = wx.CheckBox(extra_box, -1, "下载视频字幕")
        self.subtitle_file_type_lab = wx.StaticText(extra_box, -1, "字幕文件格式")
        self.subtitle_file_type_choice = wx.Choice(extra_box, -1, choices = list(subtitle_format_map.keys()))

        subtitle_hbox = wx.BoxSizer(wx.HORIZONTAL)
        subtitle_hbox.AddSpacer(self.FromDIP(20))
        subtitle_hbox.Add(self.subtitle_file_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        subtitle_hbox.Add(self.subtitle_file_type_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        subtitle_hbox.AddSpacer(self.FromDIP(20))

        self.download_cover_file_chk = wx.CheckBox(extra_box, -1, "下载视频封面")

        extra_sbox = wx.StaticBoxSizer(extra_box, wx.VERTICAL)
        extra_sbox.Add(self.download_danmaku_file_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        extra_sbox.Add(danmaku_hbox, 0, wx.EXPAND)
        extra_sbox.Add(self.download_subtitle_file_chk, 0, wx.ALL & (~wx.TOP), 10)
        extra_sbox.Add(subtitle_hbox, 0, wx.EXPAND)
        extra_sbox.Add(self.download_cover_file_chk, 0, wx.ALL & (~wx.TOP), 10)

        other_box = wx.StaticBox(self, -1, "其他选项")
        
        self.auto_popup_chk = wx.CheckBox(other_box, -1, "下载时自动弹出")
        self.auto_add_number_chk = wx.CheckBox(other_box, -1, "批量下载视频时自动添加序号")

        other_sbox = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        other_sbox.Add(self.auto_popup_chk, 0, wx.ALL, 10)
        other_sbox.Add(self.auto_add_number_chk, 0, wx.ALL & (~wx.TOP), 10)

        right_vbox = wx.BoxSizer(wx.VERTICAL)
        right_vbox.Add(extra_sbox, 0, wx.ALL | wx.EXPAND, 10)
        right_vbox.Add(other_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(left_vbox, 0, wx.EXPAND)
        hbox.Add(right_vbox, 0, wx.EXPAND)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.download_none_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeStreamDownloadOptionEVT)
        self.download_video_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeStreamDownloadOptionEVT)
        self.download_audio_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeStreamDownloadOptionEVT)
        self.download_both_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeStreamDownloadOptionEVT)

        self.download_danmaku_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadDanmakuEVT)
        self.download_subtitle_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadSubtitleEVT)

        self.auto_add_number_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAutoPopupEVT)

        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirmEVT)

    def init_utils(self):
        self.load_download_option()

        self.onChangeStreamDownloadOptionEVT(0)
        self.onCheckDownloadDanmakuEVT(0)
        self.onCheckDownloadSubtitleEVT(0)

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
            match DownloadOption(Config.Download.stream_download_option):
                case DownloadOption.NONE:
                    self.download_none_radio.SetValue(True)

                case DownloadOption.OnlyVideo:
                    self.download_video_radio.SetValue(True)

                case DownloadOption.OnlyAudio:
                    self.download_audio_radio.SetValue(True)

                case DownloadOption.VideoAndAudio:
                    self.download_both_radio.SetValue(True)

        self.video_quality_choice.Set(self.parent.video_quality_choice.GetItems())
        self.video_quality_choice.Select(self.parent.video_quality_choice.GetSelection())

        set_audio_quality_list()

        self.video_codec_choice.Set(list(video_codec_preference_map.keys()))
        self.video_codec_choice.Select(get_mapping_index_by_value(video_codec_preference_map, Config.Download.video_codec_id))

        set_stream_download_option()

        self.download_danmaku_file_chk.SetValue(Config.Extra.download_danmaku_file)
        self.danmaku_file_type_choice.Select(Config.Extra.danmaku_file_type)
        self.download_subtitle_file_chk.SetValue(Config.Extra.download_subtitle_file)
        self.subtitle_file_type_choice.Select(Config.Extra.subtitle_file_type)
        self.download_cover_file_chk.SetValue(Config.Extra.download_cover_file)

        self.auto_popup_chk.SetValue(Config.Download.auto_popup_option_dialog)
        self.auto_add_number_chk.SetValue(Config.Download.add_number)
    
    def onChangeVideoQualityEVT(self, event):
        pass

    def onChangeAudioQualityEVT(self, event):
        pass

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

        def set_use_ffmpeg_enable(enable: bool):
            self.use_ffmpeg_chk.Enable(enable)
            self.use_ffmpeg_chk.SetValue(enable)

        if self.download_none_radio.GetValue():
            set_video_quality_enable(False)
            set_audio_quality_enable(False)

            set_use_ffmpeg_enable(False)
        
        if self.download_video_radio.GetValue():
            set_video_quality_enable(True)
            set_audio_quality_enable(False)

            set_use_ffmpeg_enable(False)

        if self.download_audio_radio.GetValue():
            set_video_quality_enable(False)
            set_audio_quality_enable(True)

            set_use_ffmpeg_enable(False)
        
        if self.download_both_radio.GetValue():
            set_video_quality_enable(True)
            set_audio_quality_enable(True)

            set_use_ffmpeg_enable(True)

    def onCheckDownloadDanmakuEVT(self, event):
        self.danmaku_file_type_lab.Enable(self.download_danmaku_file_chk.GetValue())
        self.danmaku_file_type_choice.Enable(self.download_danmaku_file_chk.GetValue())

    def onCheckDownloadSubtitleEVT(self, event):
        self.subtitle_file_type_lab.Enable(self.download_subtitle_file_chk.GetValue())
        self.subtitle_file_type_choice.Enable(self.download_subtitle_file_chk.GetValue())

    def onCheckAutoPopupEVT(self, event):
        Config.Download.auto_popup_option_dialog = self.auto_popup_chk.GetValue()

        kwargs = {
            "auto_popup_option_dialog": Config.Download.auto_popup_option_dialog
        }

        config_utils.update_config_kwargs(Config.APP.app_config_path, "download", **kwargs)

    def onConfirmEVT(self, event):
        def set_stream_download_option():
            if self.download_none_radio.GetValue():
                Config.Download.stream_download_option = DownloadOption.NONE.value

            if self.download_video_radio.GetValue():
                Config.Download.stream_download_option = DownloadOption.OnlyVideo.value

            if self.download_audio_radio.GetValue():
                Config.Download.stream_download_option = DownloadOption.OnlyAudio.value

            if self.download_both_radio.GetValue():
                Config.Download.stream_download_option = DownloadOption.VideoAndAudio.value

            Config.Download.use_ffmpeg_merge = self.use_ffmpeg_chk.GetValue()

        AudioInfo.audio_quality_id = audio_quality_map.get(self.audio_quality_choice.GetStringSelection())
        Config.Download.video_codec_id = video_codec_preference_map.get(self.video_codec_choice.GetStringSelection())

        set_stream_download_option()

        Config.Extra.download_danmaku_file = self.download_danmaku_file_chk.GetValue()
        Config.Extra.danmaku_file_type = self.danmaku_file_type_choice.GetSelection()
        Config.Extra.download_subtitle_file = self.download_subtitle_file_chk.GetValue()
        Config.Extra.subtitle_file_type = self.subtitle_file_type_choice.GetSelection()
        Config.Extra.download_cover_file = self.download_cover_file_chk.GetValue()

        Config.Download.add_number = self.auto_add_number_chk.GetValue()

        event.Skip()