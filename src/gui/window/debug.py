import wx

from gui.component.window.frame import Frame

class DebugWindow(Frame):
    def __init__(self, parent):
        from gui.main_v2 import MainWindow
        
        self.parent: MainWindow = parent

        Frame.__init__(self, parent, "Debug")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        panel = wx.Panel(self, -1)

        self.enable_episode_list_chk = wx.CheckBox(panel, -1, "设置剧集列表按钮可用")
        self.enable_download_option_chk = wx.CheckBox(panel, -1, "设置下载选项按钮可用")

        enable_hbox = wx.BoxSizer(wx.HORIZONTAL)
        enable_hbox.Add(self.enable_episode_list_chk, 0, wx.ALL, 10)
        enable_hbox.Add(self.enable_download_option_chk, 0, wx.ALL & (~wx.LEFT), 10)

        parse_info = wx.StaticText(panel, -1, "查看当前 ParseInfo")

        self.info_list = wx.ListCtrl(panel, -1, style = wx.LC_REPORT)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(enable_hbox, 0, wx.EXPAND, 10, )
        vbox.Add(parse_info, 0, wx.ALL, 10)
        vbox.Add(self.info_list, 0, wx.ALL & (~wx.TOP), 10)

        panel.SetSizerAndFit(vbox)
    
    def init_utils(self):
        pass

    def Bind_EVT(self):
        self.enable_episode_list_chk.Bind(wx.EVT_CHECKBOX, self.onEnableEpisodeListEVT)
        self.enable_download_option_chk.Bind(wx.EVT_CHECKBOX, self.onEnableDownloadOptionEVT)

    def onEnableEpisodeListEVT(self, event):
        self.parent.episode_option_btn.Enable(self.enable_episode_list_chk.GetValue())

    def onEnableDownloadOptionEVT(self, event):
        self.parent.download_option_btn.Enable(self.enable_download_option_chk.GetValue())