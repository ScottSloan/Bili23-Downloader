import wx

from gui.component.window.dialog import Dialog

from gui.component.text_ctrl.text_ctrl import TextCtrl

class RequireVideoResolutionDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "选择视频分辨率")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        tip_lab = wx.StaticText(self, -1, "单独下载 ass 格式的弹幕或字幕时，需要手动选择视频分辨率\n注意：请确保选择的视频分辨率与原视频一致，否则将导致显示异常")

        self.choose_radio_btn = wx.RadioButton(self, -1, "快速选择")

        self.video_quality_choice = wx.Choice(self, -1)

        video_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_hbox.Add(self.video_quality_choice, 0, wx.ALL, self.FromDIP(6))

        self.custom_radio_btn = wx.RadioButton(self, -1, "手动输入")

        self.video_width_box = TextCtrl(self, -1, "1920", size = self.FromDIP((60, 24)))
        self.x_lab = wx.StaticText(self, -1, "x")
        self.video_height_box = TextCtrl(self, -1, "1080", size = self.FromDIP((60, 24)))

        resolution_hbox = wx.BoxSizer(wx.HORIZONTAL)
        resolution_hbox.Add(self.video_width_box, 0, wx.ALL, self.FromDIP(6))
        resolution_hbox.Add(self.x_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        resolution_hbox.Add(self.video_height_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        grid_box = wx.FlexGridSizer(2, 3, 0, 0)
        grid_box.Add(self.choose_radio_btn, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        grid_box.AddSpacer(self.FromDIP(20))
        grid_box.Add(self.custom_radio_btn, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        grid_box.Add(video_quality_hbox, 0, wx.EXPAND)
        grid_box.AddSpacer(self.FromDIP(20))
        grid_box.Add(resolution_hbox, 0, wx.EXPAND)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(tip_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(grid_box, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

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