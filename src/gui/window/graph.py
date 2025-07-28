import wx
import json

from utils.module.graph import Graph

from gui.component.webview import Webview
from gui.component.window.frame import Frame

class GraphWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, f"Graph Viewer")

        self.init_UI()

        self.SetSize(self.FromDIP((960, 540)))

        self.init_utils()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        self.webview = Webview(self)

        self.webview.browser.LoadURL(self.webview.get_page("graph.html"))
        self.webview.browser.EnableAccessToDevTools(True)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.webview.browser, 1, wx.ALL | wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.webview.browser.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self.onMessageEVT)

        self.webview.browser.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.onLoadedEVT)

    def init_utils(self):
        self.webview.browser.AddScriptMessageHandler("MainApplication")

    def onLoadedEVT(self, event):
        data = Graph.get_graph_json(self.GetFont().GetFaceName())

        self.webview.browser.RunScriptAsync(f"initGraph('{data.get("graph")}', '{data.get("title")}');")

    def onMessageEVT(self, event):
        msg = event.GetString()

        if msg == "fullscreen":
            self.Maximize(not self.IsMaximized())