import wx
import sys

from gui.component.panel.panel import Panel

class AgreePage(Panel):
    def __init__(self, parent: wx.Window, desc: str):
        self.desc = desc

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 1)

        self.desc_lab = wx.StaticText(self, -1, self.desc)
        self.desc_lab.Wrap(self.FromDIP(400))
        self.desc_lab.SetFont(font)

        self.agree_btn = wx.Button(self, -1, "已知晓", size = self.get_scaled_size((80, 28)))
        self.agree_btn.Hide()
        self.disagree_btn = wx.Button(self, -1, "不理解", size = self.get_scaled_size((80, 28)))
        self.disagree_btn.Hide()

        button_hbox = wx.BoxSizer(wx.HORIZONTAL)
        button_hbox.AddStretchSpacer()
        button_hbox.Add(self.agree_btn, 0, wx.ALL, self.FromDIP(6))
        button_hbox.Add(self.disagree_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        button_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.desc_lab, 0, wx.ALL, self.FromDIP(10))
        vbox.AddStretchSpacer()
        vbox.Add(button_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.agree_btn.Bind(wx.EVT_BUTTON, self.onAgreeEVT)
        self.disagree_btn.Bind(wx.EVT_BUTTON, self.onDisagreeEVT)

    def startCountdown(self):
        def worker():
            self.agree_btn.Show()
            self.disagree_btn.Show()
            self.Layout()

        wx.CallLater(5000, worker)

    def onAgreeEVT(self, event: wx.CommandEvent):
        dlg = wx.FindWindowByName("guide")

        dlg.onNextPageEVT(0)

        self.agree_btn.Hide()
        self.disagree_btn.Hide()

    def onDisagreeEVT(self, event: wx.CommandEvent):
        sys.exit()