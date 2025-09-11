import wx

from utils.config import Config

from gui.component.window.dialog import Dialog

class RequireVideoResolutionDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, "确认视频分辨率")

        self.init_UI()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        tip_lab = wx.StaticText(self, -1, "单独下载 .ass 格式弹幕或字幕时，请手动确认视频分辨率。\n若分辨率设置与实际视频不符，可能导致文字位置偏移或显示大小异常。")
        resolution_box = wx.StaticText(self, -1, "视频分辨率（长度 x 宽度）：")

        self.video_width_box = wx.TextCtrl(self, -1, str(Config.Temp.video_width), size = self.FromDIP((60, -1)))
        self.x_lab = wx.StaticText(self, -1, "x")
        self.video_height_box = wx.TextCtrl(self, -1, str(Config.Temp.video_height), size = self.FromDIP((60, -1)))

        resolution_hbox = wx.BoxSizer(wx.HORIZONTAL)
        resolution_hbox.Add(self.video_width_box, 0, wx.ALL, self.FromDIP(6))
        resolution_hbox.Add(self.x_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        resolution_hbox.Add(self.video_height_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        self.remember_resolution_chk = wx.CheckBox(self, -1, "记住设置，在关闭程序前不再提示")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(tip_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(resolution_box, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(resolution_hbox, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(self.remember_resolution_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def onOKEVT(self):
        Config.Temp.video_width = int(self.video_width_box.GetValue())
        Config.Temp.video_height = int(self.video_height_box.GetValue())

        Config.Temp.remember_resolution_settings = self.remember_resolution_chk.GetValue()