import wx
import os
from typing import List, Callable, Tuple

from utils.config import Config

from utils.common.enums import Platform
from utils.common.model.data_type import LiveRoomInfo
from utils.common.thread import Thread
from utils.common.datetime_util import DateTime

from gui.component.panel.panel import Panel
from gui.component.panel.live_room_item import LiveRoomItemPanel
from gui.component.panel.scrolled_panel_list import ScrolledPanelList

from gui.component.window.frame import Frame

class Utils:
    @staticmethod
    def create_live_file(live_list: List[LiveRoomInfo]):
        for entry in live_list:
            if os.path.exists(entry.file_path):
                return True

            entry.timestamp = DateTime.get_timestamp()

            entry.update()

    @staticmethod
    def read_live_files():
        temp_live_info_list: List[LiveRoomInfo] = []

        for file_name in os.listdir(Config.User.live_file_directory):
            file_path = os.path.join(Config.User.live_file_directory, file_name)

            if file_name.startswith("info_") and file_name.endswith(".json"):
                task_info = LiveRoomInfo()
                task_info.load_from_file(file_path)

                if task_info.is_valid():
                    temp_live_info_list.append(task_info)
                else:
                    task_info.remove_file()

        temp_live_info_list.sort(key = lambda x: x.timestamp, reverse = False)

        return temp_live_info_list

class LiveRecordingWindow(Frame):
    def __init__(self, parent: wx.Window):
        Frame.__init__(self, parent, "直播录制")

        self.set_window_params()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

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
            "max_items": 50,
            "empty_label": "直播间列表为空",
            "add_panel_item": self.add_panel_item,
            "load_more_item": self.ShowItems
        }

        self.scroller = ScrolledPanelList(list_panel, info)
        self.scroller.set_dark_mode()

        list_vbox = wx.BoxSizer(wx.VERTICAL)
        list_vbox.Add(self.scroller, 1, wx.EXPAND)
        
        list_panel.SetSizerAndFit(list_vbox)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_panel, 0, wx.EXPAND)
        vbox.Add(top_seperate_line, 0, wx.EXPAND)
        vbox.Add(list_panel, 1, wx.EXPAND)

        self.SetSizer(vbox)
    
    def init_utils(self):
        def worker():
            live_list = Utils.read_live_files()

            self.add_to_live_list(live_list)

        self.temp_panel_items: List[Tuple[LiveRoomItemPanel, int, int]] = []

        Thread(target = worker).start()

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

    def onCloseEVT(self, event: wx.CloseEvent):
        self.Hide()

    def add_panel_item(self, temp_info_list: List[LiveRoomInfo]):
        self.temp_panel_items = [(LiveRoomItemPanel(self.scroller, entry, self), 0, wx.EXPAND) for entry in temp_info_list]

        return self.temp_panel_items
    
    def ShowItems(self, callback: Callable = None, load_items: int = None, max_limit: bool = False):
        self.scroller.ShowListItems(callback, load_items, max_limit)

        self.show_room_info()

    def show_room_info(self):
        def worker():
            for (panel, proportion, flag) in self.temp_panel_items:
                wx.CallAfter(panel.utils.show_room_info)

                panel.utils.show_cover()

            self.temp_panel_items.clear()

        Thread(target = worker).start()

    def add_to_live_list(self, live_list = List[LiveRoomInfo], create_local_file: bool = False):
        if create_local_file:
            if Utils.create_live_file(live_list):
                return

        self.scroller.info_list.extend(live_list)

        wx.CallAfter(self.ShowItems)

    def remove_item(self):
        self.scroller.Remove()

        self.scroller.Layout()

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