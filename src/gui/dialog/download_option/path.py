import wx

from utils.config import Config

from gui.component.panel.panel import Panel

class PathStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        path_box = wx.StaticBox(self, -1, "下载目录设置")

        self.path_box = wx.TextCtrl(path_box, -1)
        self.browse_btn = wx.Button(path_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        path_sbox = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        path_sbox.Add(path_hbox, 0, wx.EXPAND)

        self.SetSizer(path_sbox)

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)

    def onBrowsePathEVT(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = self.path_box.GetValue())

        if dlg.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dlg.GetPath())

    def load_data(self):
        self.path_box.SetValue(Config.Download.path)

    def save(self):
        Config.Download.path = self.path_box.GetValue()
