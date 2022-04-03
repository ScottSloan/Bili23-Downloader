import wx
import os
import wx.html2

from utils.config import Config
from utils.video import VideoInfo

from gui.template import Frame

class InfoWindow(Frame):
    def __init__(self, parent, title, theme):
        self.theme = theme
        Frame.__init__(self, parent, title, (800, 500))

        self.init_controls()
        self.Bind_EVT()

        self.browser.LoadURL("file://{}".format(Config._info_html))

    def init_controls(self):
        self.browser = wx.html2.WebView.New(self.panel, -1)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.browser, 1, wx.EXPAND)

        self.panel.SetSizer(vbox)
    
    def Bind_EVT(self):
        self.Bind(wx.EVT_SHOW, self.on_show)

    def on_show(self, event):
        if self.theme == VideoInfo:
            from utils.html import save_video_info
            save_video_info()

        else:
            from utils.html import save_bangumi_info
            save_bangumi_info()

        event.Skip()