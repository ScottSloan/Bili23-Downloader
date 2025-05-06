import wx

from gui.component.webview import Webview

from gui.component.frame import Frame

class GraphWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "Graph")

        self.init_UI()

        self.SetSize(self.FromDIP((700, 400)))

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        self.webview = Webview(self)

        self.webview.browser.SetPage(self.webview.get_page("graph.html"), "")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.webview.browser, 1, wx.ALL | wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.webview.browser.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.onLoadedEVT)

    def onLoadedEVT(self, event):
        from utils.parse.interact_video import InteractVideoInfo

        self.webview.browser.RunScriptAsync(f"initGraph({InteractVideoInfo.graph_data})")