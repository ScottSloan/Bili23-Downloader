import wx

from utils.common.icon_v2 import IconManager, IconType

from gui.templates import InfoLabel

class EmptyItemPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

    def init_UI(self):
        self.empty_lab = wx.StaticText(self, -1, "无项目")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.empty_lab, 0, wx.ALL, 10)
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddStretchSpacer(200)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer(200)

        self.SetSizer(vbox)

class DownloadTaskItemPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.icon_manager = IconManager(self)

        self.cover_bmp = wx.StaticBitmap(self, -1, size = self.FromDIP((112, 63)))

        self.title_lab = wx.StaticText(self, -1, size = self.FromDIP((300, 24)), style = wx.ST_ELLIPSIZE_MIDDLE)

        self.video_quality_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))
        self.video_codec_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))
        self.video_size_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))

        video_info_hbox = wx.BoxSizer(wx.HORIZONTAL)

        video_info_hbox.Add(self.video_quality_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        video_info_hbox.AddSpacer(20)
        video_info_hbox.Add(self.video_codec_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        video_info_hbox.AddSpacer(20)
        video_info_hbox.Add(self.video_size_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        video_info_vbox = wx.BoxSizer(wx.VERTICAL)
        video_info_vbox.AddSpacer(5)
        video_info_vbox.Add(self.title_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, 10)
        video_info_vbox.AddStretchSpacer()
        video_info_vbox.Add(video_info_hbox, 0, wx.EXPAND)
        video_info_vbox.AddSpacer(5)

        self.progress_bar = wx.Gauge(self, -1, 100, size = (-1, -1), style = wx.GA_SMOOTH)

        progress_bar_hbox = wx.BoxSizer(wx.HORIZONTAL)
        progress_bar_hbox.Add(self.progress_bar, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)

        self.speed_lab = InfoLabel(self, "等待下载...", size = self.FromDIP((-1, -1)))

        speed_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_hbox.Add(self.speed_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        progress_bar_vbox = wx.BoxSizer(wx.VERTICAL)
        progress_bar_vbox.AddSpacer(5)
        progress_bar_vbox.Add(progress_bar_hbox, 0, wx.EXPAND)
        progress_bar_vbox.AddStretchSpacer()
        progress_bar_vbox.Add(speed_hbox, 0, wx.EXPAND)
        progress_bar_vbox.AddSpacer(5)

        self.pause_btn = wx.BitmapButton(self, -1, self.icon_manager.get_icon_bitmap(IconType.RESUME_ICON), size = self.FromDIP((24, 24)))
        self.pause_btn.SetToolTip("开始下载")

        self.stop_btn = wx.BitmapButton(self, -1, self.icon_manager.get_icon_bitmap(IconType.DELETE_ICON), size = self.FromDIP((24, 24)))
        self.stop_btn.SetToolTip("取消下载")

        panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel_hbox.Add(self.cover_bmp, 0, wx.ALL, 10)
        panel_hbox.Add(video_info_vbox, 0, wx.EXPAND)
        panel_hbox.AddStretchSpacer()
        panel_hbox.Add(progress_bar_vbox, 0, wx.EXPAND)
        panel_hbox.Add(self.pause_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.Add(self.stop_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.AddSpacer(10)

        bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        self.panel_vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel_vbox.Add(panel_hbox, 1, wx.EXPAND)
        self.panel_vbox.Add(bottom_border, 0, wx.EXPAND)

        self.SetSizer(self.panel_vbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_ENTER_WINDOW, self.onItemHoverEVT)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.onItemLeaveEVT)

        self.cover_bmp.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        self.title_lab.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        self.video_quality_lab.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        self.video_codec_lab.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        self.video_size_lab.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        self.progress_bar.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        self.speed_lab.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        self.pause_btn.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        self.stop_btn.Bind(wx.EVT_ENTER_WINDOW, self.onItemChildrenHoverEVT)
        
        self.cover_bmp.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)
        self.title_lab.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)
        self.video_quality_lab.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)
        self.video_codec_lab.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)
        self.video_size_lab.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)
        self.progress_bar.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)
        self.speed_lab.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)
        self.pause_btn.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)
        self.stop_btn.Bind(wx.EVT_LEAVE_WINDOW, self.onItemChildrenLeave)

    def init_utils(self):
        self._children_hover = False

    def onItemHoverEVT(self, event):
        self.SetBackgroundColour(wx.Colour(220, 220, 220))

        self.Refresh()

        event.Skip()
    
    def onItemChildrenHoverEVT(self, event):
        self._children_hover = True

        event.Skip()

    def onItemLeaveEVT(self, event):
        if not self._children_hover:
            self.SetBackgroundColour("white")

            self.Refresh()

            event.Skip()

    def onItemChildrenLeave(self, event):
        self._children_hover = False

        event.Skip()