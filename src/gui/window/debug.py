import wx

from utils.module.web.ws import WebSocketServer

from gui.component.window.frame import Frame

class DebugWindow(Frame):
    def __init__(self, parent):
        from gui.main_v3 import MainWindow
        
        self.parent: MainWindow = parent

        Frame.__init__(self, parent, "Debug")

        self.init_UI()

        self.init_utils()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        panel = wx.Panel(self, -1)

        self.enable_episode_list_chk = wx.CheckBox(panel, -1, "Enable Episode List Button")
        self.enable_download_option_chk = wx.CheckBox(panel, -1, "Enable Download Option Button")

        enable_hbox = wx.BoxSizer(wx.HORIZONTAL)
        enable_hbox.Add(self.enable_episode_list_chk, 0, wx.ALL, 10)
        enable_hbox.Add(self.enable_download_option_chk, 0, wx.ALL & (~wx.LEFT), 10)

        self.start_ws_btn = wx.Button(panel, -1, "Start WebSocket")
        self.stop_ws_btn = wx.Button(panel, -1, "Stop WebSocket")

        ws_hbox = wx.BoxSizer(wx.HORIZONTAL)
        ws_hbox.Add(self.start_ws_btn, 0, wx.ALL, self.FromDIP(6))
        ws_hbox.Add(self.stop_ws_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        parse_info = wx.StaticText(panel, -1, "查看当前 ParseInfo")

        self.info_list = wx.ListCtrl(panel, -1, style = wx.LC_REPORT)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(enable_hbox, 0, wx.EXPAND)
        vbox.Add(ws_hbox, 0, wx.EXPAND)
        vbox.Add(parse_info, 0, wx.ALL, 10)
        vbox.Add(self.info_list, 0, wx.ALL & (~wx.TOP), 10)

        panel.SetSizerAndFit(vbox)
    
    def init_utils(self):
        self.websocket_server = WebSocketServer()

    def Bind_EVT(self):
        self.enable_episode_list_chk.Bind(wx.EVT_CHECKBOX, self.onEnableEpisodeListEVT)
        self.enable_download_option_chk.Bind(wx.EVT_CHECKBOX, self.onEnableDownloadOptionEVT)

        self.start_ws_btn.Bind(wx.EVT_BUTTON, self.onStartWSEVT)
        self.stop_ws_btn.Bind(wx.EVT_BUTTON, self.onStopWSEVT)

    def onEnableEpisodeListEVT(self, event):
        self.parent.episode_option_btn.Enable(self.enable_episode_list_chk.GetValue())

    def onEnableDownloadOptionEVT(self, event):
        self.parent.download_option_btn.Enable(self.enable_download_option_chk.GetValue())

    def onStartWSEVT(self, event):
        self.websocket_server.start()

    def onStopWSEVT(self, event):
        self.websocket_server.stop()