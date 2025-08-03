import wx
from typing import List, Tuple, Callable

from utils.config import Config, app_config_group

from utils.common.enums import DownloadStatus
from utils.common.data_type import DownloadTaskInfo
from utils.common.thread import Thread

from gui.component.panel.scrolled_panel_list import ScrolledPanelList
from gui.component.panel.panel import Panel
from gui.component.panel.download_item_v4 import DownloadTaskItemPanel

class BasePage(Panel):
    def __init__(self, parent: wx.Window, name: str):
        Panel.__init__(self, parent, name)

        self.scroller: ScrolledPanelList = None
        self.temp_panel_list: List[Tuple[DownloadTaskItemPanel, int, int]] = []

    def ShowItems(self, callback: Callable = None, load_items: int = None, max_limit: bool = False):
        self.scroller.ShowListItems(callback, load_items, max_limit)

        self.show_task_info()

    def get_panel_items_count(self, condition: List[int]):
        count = 0

        for panel in self.panel_items:
            if isinstance(panel, DownloadTaskItemPanel):
                if panel.task_info.status in condition:
                    count += 1

        return count
    
    def show_task_info(self):
        def worker():
            for (panel, proportion, flag) in self.temp_panel_list:
                wx.CallAfter(panel.utils.show_task_info, self.GetName() == "下载完成")

                panel.utils.show_cover()

            self.temp_panel_list.clear()

        Thread(target = worker).start()

    def remove_all_items(self):
        wx.BeginBusyCursor()

        self.scroller.Freeze()

        for info in self.scroller.info_list:
            info.remove_file()

        self.scroller.info_list.clear()

        for panel in self.panel_items:
            if isinstance(panel, DownloadTaskItemPanel):
                panel.utils.destory_panel(remove_file = True)

        self.scroller.remove_more_panel()
        self.scroller.Remove()

        self.scroller.Thaw()

        wx.EndBusyCursor()

        self.download_window.update_title(self.GetName())

    @property
    def panel_items(self):
        children: List[DownloadTaskItemPanel] = self.scroller.GetChildren()
        return children  

    @property
    def total_panel_items(self):
        count = 0

        for panel in self.panel_items:
            if isinstance(panel, DownloadTaskItemPanel):
                count += 1

        return count 
    
class DownloadingPage(BasePage):
    def __init__(self, parent: wx.Window, download_window: wx.Window, name: str):
        self.download_window = download_window

        BasePage.__init__(self, parent, name)

        self.init_UI()

        self.Bind_EVT()

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
            "max_items": 50,
            "empty_label": "没有正在下载的项目",
            "add_panel_item": self.add_panel_item,
            "load_more_item": self.ShowItems
        }

        self.scroller = ScrolledPanelList(self, info)
        self.scroller.set_dark_mode()
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(self.scroller, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.start_all_btn.Bind(wx.EVT_BUTTON, self.onStartAllEVT)
        self.pause_all_btn.Bind(wx.EVT_BUTTON, self.onPauseAllEVT)
        self.cancel_all_btn.Bind(wx.EVT_BUTTON, self.onStopAllEVT)

        self.max_download_choice.Bind(wx.EVT_BUTTON, self.onChangeDownloadCountEVT)

    def onStartAllEVT(self, event):
        self.start_download(start_all = True)

    def onPauseAllEVT(self, event):
        for panel in self.panel_items:
            if isinstance(panel, DownloadTaskItemPanel):
                if panel.task_info.status in DownloadStatus.Alive.value:
                    panel.utils.pause_download()

    def onStopAllEVT(self, event):
        self.remove_all_items()

    def onChangeDownloadCountEVT(self, event):
        Config.Download.max_download_count = int(self.max_download_choice.GetStringSelection())

        count = 0

        for panel in self.panel_items:
            if isinstance(panel, DownloadTaskItemPanel):
                if self.get_panel_items_count([DownloadStatus.Downloading.value]) < Config.Download.max_download_count:
                    if panel.task_info.status in [DownloadStatus.Waiting.value, DownloadStatus.Pause.value]:
                        panel.utils.resume_download()
                else:
                    if panel.task_info.status == DownloadStatus.Downloading.value:
                        count += 1

                        if count > Config.Download.max_download_count:
                            panel.utils.pause_download(set_waiting_status = True)
          
        Config.save_config_group(Config, app_config_group, Config.APP.app_config_path)

    def add_panel_item(self, temp_info_list: List[DownloadTaskInfo]):
        self.temp_panel_list = [(DownloadTaskItemPanel(self.scroller, entry, self.download_window), 0, wx.EXPAND) for entry in temp_info_list]

        return self.temp_panel_list

    def start_download(self, start_all: bool = False):
        for panel in self.panel_items:
            if isinstance(panel, DownloadTaskItemPanel):
                if panel.task_info.status == DownloadStatus.Pause.value and start_all:
                    panel.utils.set_download_status(DownloadStatus.Waiting.value)

                if panel.task_info.status == DownloadStatus.Waiting.value:
                    if self.get_panel_items_count([DownloadStatus.Downloading.value]) < Config.Download.max_download_count:
                        panel.utils.resume_download()
    
    def is_need_load_more(self):
        return self.scroller.more

    @property
    def total_item_count(self):
        return self.total_panel_items + len(self.scroller.info_list)

class CompletedPage(BasePage):
    def __init__(self, parent: wx.Window, download_window: wx.Window, name: str):
        self.download_window = download_window

        BasePage.__init__(self, parent, name)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.set_dark_mode()

        self.clear_history_btn = wx.Button(self, -1, "清除下载记录")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.clear_history_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        top_separate_line = wx.StaticLine(self, -1)

        info = {
            "max_items": 50,
            "empty_label": "没有下载完成的项目",
            "add_panel_item": self.add_panel_item,
            "load_more_item": self.ShowItems
        }

        self.scroller = ScrolledPanelList(self, info)
        self.scroller.set_dark_mode()
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(self.scroller, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.clear_history_btn.Bind(wx.EVT_BUTTON, self.onClearAllEVT)

    def onClearAllEVT(self, event):
        self.remove_all_items()

    def add_panel_item(self, temp_info_list: List[DownloadTaskInfo]):
        self.temp_panel_list = [(DownloadTaskItemPanel(self.scroller, entry, self.download_window), 0, wx.EXPAND) for entry in temp_info_list]

        return self.temp_panel_list

    @property
    def total_item_count(self):
        return self.total_panel_items + len(self.scroller.info_list)