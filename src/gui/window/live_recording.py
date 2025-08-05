import wx

from utils.config import Config

from utils.common.enums import Platform
from utils.common.model.data_type import LiveRoomInfo

from gui.component.panel.panel import Panel
from gui.component.panel.live_room_item import LiveRoomItemPanel
from gui.component.panel.scrolled_panel_list import ScrolledPanelList

from gui.component.window.frame import Frame

class LiveRecordingWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "直播录制")

        self.set_window_params()

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        top_panel = Panel(self)
        top_panel.set_dark_mode()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 4)

        top_title_lab = wx.StaticText(top_panel, -1, "直播间列表")
        top_title_lab.SetFont(font)

        top_panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_panel_hbox.AddSpacer(self.FromDIP(13))
        top_panel_hbox.Add(top_title_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        top_panel_vbox = wx.BoxSizer(wx.VERTICAL)
        top_panel_vbox.AddSpacer(self.FromDIP(6))
        top_panel_vbox.Add(top_panel_hbox, 0, wx.EXPAND)
        top_panel_vbox.AddSpacer(self.FromDIP(6))

        top_panel.SetSizerAndFit(top_panel_vbox)

        top_seperate_line = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        list_panel = Panel(self)
        list_panel.set_dark_mode()

        info = {
            "empty_label": "直播间列表为空"
        }

        self.live_room_list = ScrolledPanelList(list_panel, info)
        self.live_room_list.set_dark_mode()

        list_vbox = wx.BoxSizer(wx.VERTICAL)
        list_vbox.Add(self.live_room_list, 1, wx.EXPAND)
        
        list_panel.SetSizerAndFit(list_vbox)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_panel, 0, wx.EXPAND)
        vbox.Add(top_seperate_line, 0, wx.EXPAND)
        vbox.Add(list_panel, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def add_new_live_room(self, info: LiveRoomInfo):
        panel = LiveRoomItemPanel(self.live_room_list, info, self)

        self.live_room_list.Add(panel, 0, wx.EXPAND)

    def remove_live_room(self):
        self.live_room_list.Remove()

    def set_window_params(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                if self.GetDPIScaleFactor() >= 1.5:
                    size = self.FromDIP((930, 550))
                else:
                    size = self.FromDIP((960, 580))
            
            case Platform.macOS:
                size = self.FromDIP((1000, 600))
            
            case Platform.Linux:
                size = self.FromDIP((1070, 650))

        self.SetSize(size)