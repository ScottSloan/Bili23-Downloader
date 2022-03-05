import wx
import wx.html2

from utils.config import Config

from gui.template import Frame

class InfoWindow(Frame):
    def __init__(self, parent, title):
        Frame.__init__(self, parent, title, (800, 500))

        self.init_controls()
        self.browser.LoadURL("file://{}".format(Config._info_html))

    def init_controls(self):
        self.browser = wx.html2.WebView.New(self.panel, -1)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.browser, 1, wx.EXPAND)

        self.panel.SetSizer(vbox)