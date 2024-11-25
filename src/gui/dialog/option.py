import wx

from utils.config import Config
from utils.parse.audio import AudioInfo
from utils.parse.extra import ExtraInfo
from utils.mapping import audio_quality_mapping, danmaku_format_mapping

class OptionDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "下载选项")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)

                case "linux" | "darwin":
                    return wx.DefaultSize
                
        self.video_quality_lab = wx.StaticText(self, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self, -1)

        audio_quality_lab = wx.StaticText(self, -1, "音质")
        self.audio_quality_choice = wx.Choice(self, -1)

        self.audio_only_chk = wx.CheckBox(self, -1, "仅下载音频")

        flex_box = wx.FlexGridSizer(2, 2, 0, 0)
        flex_box.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        flex_box.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)
        flex_box.Add(audio_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        flex_box.Add(self.audio_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)

        media_vbox = wx.BoxSizer(wx.VERTICAL)
        media_vbox.Add(flex_box, 0, wx.EXPAND)
        media_vbox.Add(self.audio_only_chk, 0, wx.ALL, 10)

        self.get_danmaku_chk = wx.CheckBox(self, -1, "下载视频弹幕")
        self.danmaku_format_lab = wx.StaticText(self, -1, "弹幕文件格式")
        self.danmaku_type_choice = wx.Choice(self, -1, choices = list(danmaku_format_mapping.keys()))

        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(30)
        danmaku_hbox.Add(self.danmaku_format_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        danmaku_hbox.Add(self.danmaku_type_choice, 0, wx.ALL & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.get_cover_chk = wx.CheckBox(self, -1, "下载视频封面")

        self.add_number_chk = wx.CheckBox(self, -1, "批量下载视频时自动添加序号")

        extra_vbox = wx.BoxSizer(wx.VERTICAL)
        extra_vbox.Add(self.get_danmaku_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        extra_vbox.Add(danmaku_hbox, 0, wx.EXPAND)
        extra_vbox.Add(self.get_cover_chk, 0, wx.ALL, 10)
        extra_vbox.Add(self.add_number_chk, 0, wx.ALL, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(media_vbox, 0, wx.EXPAND)
        hbox.Add(extra_vbox, 0, wx.EXPAND)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = _get_scale_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = _get_scale_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.audio_only_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAudioOnlyEVT)
        self.get_danmaku_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDanmakuEVT)

        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirmEVT)

    def init_utils(self):
        def _get_audio_quality_list():
            audio_quality_desc_list = AudioInfo.aduio_quality_desc_list.copy()

            audio_quality_desc_list.insert(0, "自动")

            return audio_quality_desc_list

        def _get_choice_index(_audio_quality_id: int):
            if AudioInfo.audio_quality_id == 30300:
                return 0
            else:
                return AudioInfo.audio_quality_id_list.index(_audio_quality_id) + 1
            
        self.video_quality_choice.Set(self.GetParent().video_quality_choice.GetItems())
        self.video_quality_choice.SetSelection(self.GetParent().video_quality_choice.GetSelection())

        self.audio_quality_choice.Set(_get_audio_quality_list())
        self.audio_quality_choice.SetSelection(_get_choice_index(AudioInfo.audio_quality_id))

        self.audio_only_chk.SetValue(AudioInfo.download_audio_only)

        self.get_danmaku_chk.SetValue(ExtraInfo.get_danmaku)
        self.danmaku_type_choice.SetSelection(ExtraInfo.danmaku_type)
        self.get_cover_chk.SetValue(ExtraInfo.get_cover)

        self.add_number_chk.SetValue(Config.Download.add_number)

        self.onCheckDanmakuEVT(None)

    def onCheckAudioOnlyEVT(self, event):
        _enable = not self.audio_only_chk.GetValue()

        self.video_quality_choice.Enable(_enable)
        self.video_quality_lab.Enable(_enable)

    def onCheckDanmakuEVT(self, event):
        def set_enable(enable: bool):
            self.danmaku_type_choice.Enable(enable)
            self.danmaku_format_lab.Enable(enable)

        set_enable(self.get_danmaku_chk.GetValue())

    def onConfirmEVT(self, event):
        AudioInfo.audio_quality_id = audio_quality_mapping[self.audio_quality_choice.GetStringSelection()]
        AudioInfo.download_audio_only = self.audio_only_chk.GetValue()

        ExtraInfo.get_danmaku = self.get_danmaku_chk.GetValue()
        ExtraInfo.danmaku_type = self.danmaku_type_choice.GetSelection()
        ExtraInfo.get_cover = self.get_cover_chk.GetValue()

        Config.Download.add_number = self.add_number_chk.GetValue()

        event.Skip()