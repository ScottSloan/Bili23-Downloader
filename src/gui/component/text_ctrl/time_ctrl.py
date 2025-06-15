import wx
from wx.lib.masked import TextCtrl

from gui.component.panel.panel import Panel

class TimeCtrl(Panel):
    def __init__(self, parent, label: str):
        self.label = label

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        label = wx.StaticText(self, -1, self.label)

        label_hbox = wx.BoxSizer(wx.HORIZONTAL)
        label_hbox.AddStretchSpacer()
        label_hbox.Add(label, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        label_hbox.AddStretchSpacer()

        self.time_ctrl = TextCtrl(self, -1, mask = "##:##:##.###", formatcodes = "F0R", defaultValue = "00:00:00.000")
        self.time_ctrl.SetFont(self.GetParent().GetFont())

        self.min_btn = wx.Button(self, -1, "-", size = self.FromDIP((24, 24)))
        self.plus_btn = wx.Button(self, -1, "+", size = self.FromDIP((24, 24)))

        adjust_hbox = wx.BoxSizer(wx.HORIZONTAL)
        adjust_hbox.Add(self.min_btn, 0, wx.ALL, self.FromDIP(6))
        adjust_hbox.Add(self.time_ctrl, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        adjust_hbox.Add(self.plus_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(label_hbox, 0, wx.EXPAND)
        vbox.Add(adjust_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)
