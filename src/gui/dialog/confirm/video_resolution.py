import wx

from utils.config import Config

from gui.component.window.dialog import Dialog

from gui.component.misc.tooltip import ToolTip

class RequireVideoResolutionDialog(Dialog):
    def __init__(self, parent, video_quality_desc_list: list, video_quality_desc: str, flv_mp4: bool = False):
        self.video_quality_desc_list, self.video_quality_desc, self.flv_mp4 = video_quality_desc_list, video_quality_desc, flv_mp4

        Dialog.__init__(self, parent, "选择视频分辨率")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        tip_lab = wx.StaticText(self, -1, "在单独下载 .ass 格式的弹幕或字幕时，请手动选择视频的分辨率\n注意：确保所选分辨率与原视频一致，否则可能会导致显示异常")

        self.choose_radio_btn = wx.RadioButton(self, -1, "快速选择")
        self.choose_radio_btn.Enable(not self.flv_mp4)
        choose_tooltip = ToolTip(self)
        choose_tooltip.set_tooltip("FLV 和 MP4 格式视频流不支持根据所选分辨率自动获取，请手动输入")

        choose_hbox = wx.BoxSizer(wx.HORIZONTAL)
        choose_hbox.Add(self.choose_radio_btn, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        choose_hbox.Add(choose_tooltip, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.video_quality_choice = wx.Choice(self, -1, choices = self.video_quality_desc_list)
        self.video_quality_choice.SetStringSelection(self.video_quality_desc)

        video_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_hbox.Add(self.video_quality_choice, 0, wx.ALL, self.FromDIP(6))

        self.custom_radio_btn = wx.RadioButton(self, -1, "手动输入")
        self.custom_radio_btn.SetValue(True if self.flv_mp4 else Config.Temp.ass_custom_resolution)

        self.video_width_box = wx.TextCtrl(self, -1, str(Config.Temp.ass_video_width), size = self.FromDIP((60, 24)))
        self.x_lab = wx.StaticText(self, -1, "x")
        self.video_height_box = wx.TextCtrl(self, -1, str(Config.Temp.ass_video_height), size = self.FromDIP((60, 24)))

        resolution_hbox = wx.BoxSizer(wx.HORIZONTAL)
        resolution_hbox.Add(self.video_width_box, 0, wx.ALL, self.FromDIP(6))
        resolution_hbox.Add(self.x_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        resolution_hbox.Add(self.video_height_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        grid_box = wx.FlexGridSizer(2, 3, 0, 0)
        grid_box.Add(choose_hbox, 0, wx.EXPAND)
        grid_box.AddSpacer(self.FromDIP(20))
        grid_box.Add(self.custom_radio_btn, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        grid_box.Add(video_quality_hbox, 0, wx.EXPAND)
        grid_box.AddSpacer(self.FromDIP(20))
        grid_box.Add(resolution_hbox, 0, wx.EXPAND)

        self.remember_resolution_chk = wx.CheckBox(self, -1, "记住所选设置，在关闭程序前不再提示")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(tip_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(grid_box, 0, wx.EXPAND)
        vbox.Add(self.remember_resolution_chk, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        padding_vbox = wx.BoxSizer(wx.VERTICAL)
        padding_vbox.Add(vbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        self.SetSizerAndFit(padding_vbox)

    def Bind_EVT(self):
        self.choose_radio_btn.Bind(wx.EVT_RADIOBUTTON, self.onRadioButtonEVT)
        self.custom_radio_btn.Bind(wx.EVT_RADIOBUTTON, self.onRadioButtonEVT)

    def onRadioButtonEVT(self, event):
        choose_enable = self.choose_radio_btn.GetValue()
        custom_enable = self.custom_radio_btn.GetValue()

        self.video_quality_choice.Enable(choose_enable)
        self.video_width_box.Enable(custom_enable)
        self.x_lab.Enable(custom_enable)
        self.video_height_box.Enable(custom_enable)

    def onOKEVT(self):
        Config.Temp.ass_custom_resolution = self.custom_radio_btn.GetValue()

        Config.Temp.ass_video_width = int(self.video_width_box.GetValue())
        Config.Temp.ass_video_height = int(self.video_height_box.GetValue())

        Config.Temp.remember_resolution_settings = self.remember_resolution_chk.GetValue()