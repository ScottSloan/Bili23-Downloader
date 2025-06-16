import wx
from wx.lib.masked import TextCtrl

from gui.component.panel.panel import Panel

class TimeCtrl(Panel):
    def __init__(self, parent, label: str):
        self.label = label

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

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

    def Bind_EVT(self):
        self.plus_btn.Bind(wx.EVT_BUTTON, self.onPlusEVT)
        self.min_btn.Bind(wx.EVT_BUTTON, self.onMinEVT)

    def onPlusEVT(self, event):
        ms = self.GetTime()
        self.SetTime(ms + 100)

    def onMinEVT(self, event):
        ms = self.GetTime()
        self.SetTime(ms - 100)

    def SetTime(self, ms: int):
        hours, ms = divmod(ms, 3600000)
        minutes, ms = divmod(ms, 60000)
        seconds, ms = divmod(ms, 1000)
        
        time =  f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{int(ms):03d}"

        self.time_ctrl.SetValue(time)

    def GetTime(self):
        h, m, s_millis = self.time_ctrl.GetValue().split(':')
        s, ms = s_millis.split('.') if '.' in s_millis else (s_millis, '000')

        return (int(h) * 3600000) + (int(m) * 60000) + (int(s) * 1000) + int(ms)
