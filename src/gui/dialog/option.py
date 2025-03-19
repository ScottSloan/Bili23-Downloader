import wx

from utils.config import Config, config_utils
from utils.common.map import audio_quality_map, danmaku_format_map, subtitle_format_map, video_codec_map, get_mapping_index_by_value
from utils.common.enums import StreamType

from utils.parse.audio import AudioInfo

from gui.component.dialog import Dialog

class OptionDialog(Dialog):
    def __init__(self, parent, stream_type: int, callback):
        self.stream_type, self.callback = stream_type, callback

        Dialog.__init__(self, parent, "下载选项")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self): 
        self.video_quality_lab = wx.StaticText(self, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self, -1)

        audio_quality_lab = wx.StaticText(self, -1, "音质")
        self.audio_quality_choice = wx.Choice(self, -1)

        self.video_codec_lab = wx.StaticText(self, -1, "编码格式")
        self.video_codec_choice = wx.Choice(self, -1)

        self.audio_only_chk = wx.CheckBox(self, -1, "仅下载音频")

        flex_box = wx.FlexGridSizer(3, 2, 0, 0)
        flex_box.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        flex_box.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)
        flex_box.Add(audio_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        flex_box.Add(self.audio_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)
        flex_box.Add(self.video_codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        flex_box.Add(self.video_codec_choice, 0, wx.ALL & (~wx.LEFT), 10)

        media_vbox = wx.BoxSizer(wx.VERTICAL)
        media_vbox.Add(flex_box, 0, wx.EXPAND)
        media_vbox.Add(self.audio_only_chk, 0, wx.ALL, 10)

        self.get_danmaku_chk = wx.CheckBox(self, -1, "下载视频弹幕")
        self.danmaku_format_lab = wx.StaticText(self, -1, "弹幕文件格式")
        self.danmaku_type_choice = wx.Choice(self, -1, choices = list(danmaku_format_map.keys()))

        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(30)
        danmaku_hbox.Add(self.danmaku_format_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        danmaku_hbox.Add(self.danmaku_type_choice, 0, wx.ALL & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.get_subtitle_chk = wx.CheckBox(self, -1, "下载视频字幕")
        self.subtitle_format_lab = wx.StaticText(self, -1, "字幕文件格式")
        self.subtitle_format_choice = wx.Choice(self, -1, choices = list(subtitle_format_map.keys()))

        subtitle_hbox = wx.BoxSizer(wx.HORIZONTAL)
        subtitle_hbox.AddSpacer(30)
        subtitle_hbox.Add(self.subtitle_format_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        subtitle_hbox.Add(self.subtitle_format_choice, 0, wx.ALL & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.get_cover_chk = wx.CheckBox(self, -1, "下载视频封面")

        self.add_number_chk = wx.CheckBox(self, -1, "批量下载视频时自动添加序号")

        extra_vbox = wx.BoxSizer(wx.VERTICAL)
        extra_vbox.Add(self.get_danmaku_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        extra_vbox.Add(danmaku_hbox, 0, wx.EXPAND)
        extra_vbox.Add(self.get_subtitle_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        extra_vbox.Add(subtitle_hbox, 0, wx.EXPAND)
        extra_vbox.Add(self.get_cover_chk, 0, wx.ALL, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(30)
        hbox.Add(media_vbox, 0, wx.EXPAND)
        hbox.Add(extra_vbox, 0, wx.EXPAND)
        hbox.AddSpacer(30)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        self.auto_popup_chk = wx.CheckBox(self, -1, "下载时自动弹出此对话框")

        popup_hbox = wx.BoxSizer(wx.HORIZONTAL)
        popup_hbox.AddSpacer(30)
        popup_hbox.Add(self.auto_popup_chk, 0, wx.ALL, 10)
        popup_hbox.Add(self.add_number_chk, 0, wx.ALL & (~wx.LEFT), 10)
        popup_hbox.AddSpacer(30)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(10)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(popup_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.audio_only_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAudioOnlyEVT)
        self.get_danmaku_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDanmakuEVT)
        self.get_subtitle_chk.Bind(wx.EVT_CHECKBOX, self.onCheckSubtitleEVT)

        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirmEVT)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.onCloseEVT)

        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

    def init_utils(self):
        def _get_audio_quality_list():
            audio_quality_desc_list = AudioInfo.aduio_quality_desc_list.copy()

            if AudioInfo.Availability.audio:
                audio_quality_desc_list.insert(0, "自动")
            else:
                audio_quality_desc_list.insert(0, "--无音轨--")

            return audio_quality_desc_list

        def _get_choice_index(_audio_quality_id: int):
            if AudioInfo.audio_quality_id == 30300:
                return 0
            else:
                if _audio_quality_id in AudioInfo.audio_quality_id_list:
                    return AudioInfo.audio_quality_id_list.index(_audio_quality_id) + 1
                else:
                    return 1
            
        self.video_quality_choice.Set(self.GetParent().video_quality_choice.GetItems())
        self.video_quality_choice.SetSelection(self.GetParent().video_quality_choice.GetSelection())

        self.audio_quality_choice.Set(_get_audio_quality_list())
        self.audio_quality_choice.SetSelection(_get_choice_index(AudioInfo.audio_quality_id))

        if self.stream_type == StreamType.Dash.value:
            self.video_codec_choice.Set(list(video_codec_map.keys()))
            self.video_codec_choice.SetSelection(get_mapping_index_by_value(video_codec_map, Config.Download.video_codec_id))
        else:
            self.video_codec_choice.Set([list(video_codec_map.keys())[0]])
            self.video_codec_choice.SetSelection(0)

        self.audio_only_chk.SetValue(AudioInfo.download_audio_only)

        if not AudioInfo.Availability.audio:
            self.audio_only_chk.Enable(False)
            self.audio_only_chk.SetValue(False)

        self.get_danmaku_chk.SetValue(Config.Extra.download_danmaku_file)
        self.danmaku_type_choice.SetSelection(Config.Extra.danmaku_file_type)
        self.get_subtitle_chk.SetValue(Config.Extra.download_subtitle_file)
        self.subtitle_format_choice.SetSelection(Config.Extra.subtitle_file_type)
        self.get_cover_chk.SetValue(Config.Extra.download_cover_file)

        self.add_number_chk.SetValue(Config.Download.add_number)
        self.auto_popup_chk.SetValue(Config.Download.auto_popup_option_dialog)

        self.onCheckAudioOnlyEVT(0)
        self.onCheckDanmakuEVT(0)
        self.onCheckSubtitleEVT(0)

    def onCheckAudioOnlyEVT(self, event):
        _enable = not self.audio_only_chk.GetValue()

        self.video_quality_choice.Enable(_enable)
        self.video_quality_lab.Enable(_enable)
        self.video_codec_lab.Enable(_enable)
        self.video_codec_choice.Enable(_enable)

    def onCheckDanmakuEVT(self, event):
        def set_enable(enable: bool):
            self.danmaku_type_choice.Enable(enable)
            self.danmaku_format_lab.Enable(enable)

        set_enable(self.get_danmaku_chk.GetValue())

    def onCheckSubtitleEVT(self, event):
        def set_enable(enable: bool):
            self.subtitle_format_choice.Enable(enable)
            self.subtitle_format_lab.Enable(enable)

        set_enable(self.get_subtitle_chk.GetValue())

    def onConfirmEVT(self, event):
        AudioInfo.audio_quality_id = audio_quality_map[self.audio_quality_choice.GetStringSelection()]
        AudioInfo.download_audio_only = self.audio_only_chk.GetValue()

        Config.Download.video_codec_id = video_codec_map[self.video_codec_choice.GetStringSelection()]

        Config.Extra.download_danmaku_file = self.get_danmaku_chk.GetValue()
        Config.Extra.danmaku_file_type = self.danmaku_type_choice.GetSelection()
        Config.Extra.download_subtitle_file = self.get_subtitle_chk.GetValue()
        Config.Extra.subtitle_file_type = self.subtitle_format_choice.GetSelection()
        Config.Extra.download_cover_file = self.get_cover_chk.GetValue()

        Config.Download.add_number = self.add_number_chk.GetValue()

        self.callback(self.video_quality_choice.GetSelection(), self.video_quality_choice.IsEnabled())

        event.Skip()

    def onCloseEVT(self, event):
        Config.Download.auto_popup_option_dialog = self.auto_popup_chk.GetValue()

        kwargs = {
            "auto_popup_option_dialog": Config.Download.auto_popup_option_dialog
        }

        config_utils.update_config_kwargs(Config.APP.app_config_path, "download", **kwargs)

        event.Skip()

    def onCanelEVT(self, event):
        event.Skip()