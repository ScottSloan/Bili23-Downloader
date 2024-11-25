import wx

from utils.config import Config
from utils.parse.audio import AudioInfo
from utils.mapping import audio_quality_mapping

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
                
        video_quality_lab = wx.StaticText(self, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self, -1)

        audio_quality_lab = wx.StaticText(self, -1, "音质")
        self.audio_quality_choice = wx.Choice(self, -1)

        self.audio_only_chk = wx.CheckBox(self, -1, "仅下载音频")

        flex_box = wx.FlexGridSizer(2, 2, 0, 0)
        flex_box.Add(video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        flex_box.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)
        flex_box.Add(audio_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        flex_box.Add(self.audio_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = _get_scale_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = _get_scale_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(flex_box, 0, wx.EXPAND)
        vbox.Add(self.audio_only_chk, 0, wx.ALL, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.audio_only_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAudioOnlyEVT)

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

    def onCheckAudioOnlyEVT(self, event):
        self.video_quality_choice.Enable(not self.audio_only_chk.GetValue())

    def onConfirmEVT(self, event):
        AudioInfo.audio_quality_id = audio_quality_mapping[self.audio_quality_choice.GetStringSelection()]
        AudioInfo.download_audio_only = self.audio_only_chk.GetValue()

        event.Skip()
