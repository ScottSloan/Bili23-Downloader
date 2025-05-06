import wx
import os

from gui.component.webview import Webview

from gui.component.dialog import Dialog

class GraphWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "Graph")

        self.init_UI()

        self.SetSize(self.FromDIP((700, 400)))

        self.CenterOnParent()

    def init_UI(self):
        self.webview = Webview(self)

        self.webview.browser.SetPage(self.get_page(), "")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.webview.browser, 1, wx.ALL | wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def get_page(self):
        path = os.path.join(os.getcwd(), "src", "static", "graph.html")

        with open(path, "r", encoding = "utf-8") as f:
            return f.read()