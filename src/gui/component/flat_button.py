import wx

from utils.common.icon_v3 import Icon, IconID

from gui.component.panel import Panel

class FlatButton(Panel):
    def __init__(self, parent, label: str, icon_id: IconID, split: bool = False):
        self.label, self.icon_id, self.split = label, icon_id, split

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        if self.split:
            self.split_line = wx.StaticLine(self, -1, style = wx.LI_VERTICAL)

        self.btn_icon = wx.StaticBitmap(self, -1, Icon.get_icon_bitmap(self.icon_id), size = self.FromDIP((24, 24)))
        self.btn_icon.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        self.btn_lab = wx.StaticText(self, -1, self.label)
        self.btn_lab.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        if self.split:
            hbox.Add(self.split_line, 0, wx.ALL & (~wx.LEFT) & (~wx.RIGHT) | wx.EXPAND, self.FromDIP(10))

        hbox.Add(self.btn_icon, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.Add(self.btn_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.SetSizerAndFit(hbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)
        self.btn_icon.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)
        self.btn_lab.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

    def onClickEVT(self, event):
        self.onClickCustomEVT()

    def onClickCustomEVT(self):
        pass