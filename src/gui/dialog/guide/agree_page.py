import wx
import sys
import gettext

from gui.component.panel.panel import Panel

_ = gettext.gettext

class AgreePage(Panel):
    def __init__(self, parent: wx.Window, desc: str):
        self.desc = desc

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 1)

        self.desc_box = wx.TextCtrl(self, -1, self.desc, style = wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE)
        self.desc_box.SetFont(font)
        self.desc_box.SetInsertionPoint(0)

        self.agree_btn = wx.Button(self, -1, _("已知晓"), size = self.get_scaled_size((80, 28)))
        self.agree_btn.Hide()
        self.disagree_btn = wx.Button(self, -1, _("不理解"), size = self.get_scaled_size((80, 28)))
        self.disagree_btn.Hide()

        button_hbox = wx.BoxSizer(wx.HORIZONTAL)
        button_hbox.AddStretchSpacer()
        button_hbox.Add(self.agree_btn, 0, wx.ALL, self.FromDIP(6))
        button_hbox.Add(self.disagree_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        button_hbox.AddStretchSpacer()
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.desc_box, 1, wx.ALL | wx.EXPAND, self.FromDIP(10))
        vbox.Add(button_hbox, 0, wx.EXPAND)
        vbox.AddSpacer(self.FromDIP(10))

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