import wx

from gui.component.text_ctrl.text_ctrl import TextCtrl

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel

class SubtitlePage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        video_resolution_lab = wx.StaticText(self, -1, "视频分辨率")
        self.video_width_box = TextCtrl(self, -1, size = self.get_scaled_size((60, 24)))
        video_resolution_x_lab = wx.StaticText(self, -1, "x")
        self.video_height_box = TextCtrl(self, -1, size = self.get_scaled_size((60, 24)))

        video_resolution_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_resolution_hbox.Add(video_resolution_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        video_resolution_hbox.Add(self.video_width_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        video_resolution_hbox.Add(video_resolution_x_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        video_resolution_hbox.Add(self.video_height_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(video_resolution_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

class CustomASSStyleDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义 ASS 样式")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        type_lab = wx.StaticText(self, -1, "类型")
        self.type_choice = wx.Choice(self, -1)

        type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        type_hbox.Add(type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        type_hbox.Add(self.type_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        self.notebook = wx.Simplebook(self, -1)

        self.notebook.AddPage(SubtitlePage(self.notebook), "subtitle")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(type_hbox, 0, wx.EXPAND)
        vbox.Add(self.notebook, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        pass

    def set_option(self):
        pass