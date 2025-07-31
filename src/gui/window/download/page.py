import wx

from utils.config import Config

from gui.component.panel.scrolled_panel_list import ScrolledPanelList
from gui.component.panel.panel import Panel
from gui.component.panel.download_item_v3 import DownloadTaskItemPanel

class DownloadingPage(Panel):
    def __init__(self, parent: wx.Window, download_window: wx.Window):
        self.download_window = download_window

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        self.set_dark_mode()

        max_download_lab = wx.StaticText(self, -1, "并行下载数")
        self.max_download_choice = wx.Choice(self, -1, choices = [f"{i + 1}" for i in range(10)])
        self.max_download_choice.SetSelection(Config.Download.max_download_count - 1)

        self.start_all_btn = wx.Button(self, -1, "全部开始")
        self.pause_all_btn = wx.Button(self, -1, "全部暂停")
        self.cancel_all_btn = wx.Button(self, -1, "全部取消")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(max_download_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.max_download_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.start_all_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.pause_all_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.cancel_all_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        top_separate_line = wx.StaticLine(self, -1)

        info = {
            "empty_label": "没有正在下载的项目",
            "add_panel_item": self.add_panel_item
        }

        self.scroller = ScrolledPanelList(self, info)
        self.scroller.set_dark_mode()
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(self.scroller, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def add_panel_item(self, entry):
        item = DownloadTaskItemPanel(self.scroller, entry, self.download_window.get_download_task_item_callback(), self.download_window)
        return (item, 0, wx.EXPAND)
    
    def start_download(self):
        pass

    def after_show_items_callback(self, download_list):
        self.scroller.info_list.extend(download_list)

class CompletedPage(Panel):
    def __init__(self, parent: wx.Window, download_window: wx.Window):
        self.download_window = download_window

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        self.set_dark_mode()

        self.clear_history_btn = wx.Button(self, -1, "清除下载记录")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.clear_history_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        top_separate_line = wx.StaticLine(self, -1)

        info = {
            "empty_label": "没有下载完成的项目",
            "add_panel_item": self.add_panel_item
        }

        self.scroller = ScrolledPanelList(self, info)
        self.scroller.set_dark_mode()
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(self.scroller, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def add_panel_item(self, entry):
        item = DownloadTaskItemPanel(self.scroller, entry, self.download_window.get_download_task_item_callback(), self.download_window)
        return (item, 0, wx.EXPAND)