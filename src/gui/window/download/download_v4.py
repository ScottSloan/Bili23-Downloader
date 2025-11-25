import wx
import os
import gettext
from typing import List, Callable

from utils.config import Config

from utils.common.enums import Platform, NumberType, DownloadStatus
from utils.common.style.icon_v4 import Icon, IconID
from utils.common.io.directory import Directory
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.thread import Thread
from utils.common.datetime_util import DateTime

from utils.module.notification import NotificationManager

from gui.window.download.page import DownloadingPage, CompletedPage
from gui.window.download.item_panel_v4 import DownloadTaskItemPanel

from gui.component.button.action_button import ActionButton
from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel

_ = gettext.gettext

class TopPanel(Panel):
    def __init__(self, parent: wx.Window):
        self.parent: DownloadManagerWindow = parent

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        self.set_dark_mode()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 4))

        self.top_title_lab = wx.StaticText(self, -1, _("下载管理"))
        self.top_title_lab.SetFont(font)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(self.FromDIP(13))
        hbox.Add(self.top_title_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(self.FromDIP(6))
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddSpacer(self.FromDIP(6))

        self.SetSizer(vbox)

    def UpdateAllTitle(self, count: int, source: str):
        self.UpdateTitle(count, source)

        self.parent.left_panel.UpdateButtonTitle()

    def UpdateTitle(self, count: int, source: str):
        def worker():
            self.top_title_lab.SetLabel(title)

        if count:
            match source:
                case "正在下载":
                    title = _("%s个任务正在下载") % count

                case "下载完成":
                    title = _("%s个任务下载完成") % count
        else:
            title = _("下载管理")

        if source == self.GetCurrentPageName():
            wx.CallAfter(worker)

    def GetCurrentPageName(self):
        return self.parent.right_panel.GetCurrentPageName()

class LeftPanel(Panel):
    def __init__(self, parent: wx.Window):
        self.parent: DownloadManagerWindow = parent

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.set_dark_mode()

        self.downloading_page_btn = ActionButton(self, _("正在下载(%s)") % 0, name = "正在下载")
        self.downloading_page_btn.setBitmap(Icon.get_icon_bitmap(IconID.Downloading))
        self.completed_page_btn = ActionButton(self, _("下载完成(%s)") % 0, name = "下载完成")
        self.completed_page_btn.setBitmap(Icon.get_icon_bitmap(IconID.Complete))

        self.open_download_dir_btn = wx.Button(self, -1, _("打开下载目录"), size = self.FromDIP((120, 28)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.open_download_dir_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.downloading_page_btn, 0, wx.EXPAND)
        vbox.Add(self.completed_page_btn, 0, wx.EXPAND)
        vbox.AddStretchSpacer()
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.downloading_page_btn.onClickCustomEVT = self.onClickDownloadingPageEVT
        self.completed_page_btn.onClickCustomEVT = self.onClickCompletedPageEVT

        self.open_download_dir_btn.Bind(wx.EVT_BUTTON, self.onOpenDirEVT)

    def init_utils(self):
        self.downloading_page_btn.setActiveState()

    def onClickDownloadingPageEVT(self):
        self.parent.right_panel.change_page(0)

        self.parent.top_panel.UpdateTitle(self.parent.right_panel.downloading_page.total_item_count, self.GetCurrentPageName())

        self.completed_page_btn.setUnactiveState()

    def onClickCompletedPageEVT(self):
        self.parent.right_panel.change_page(1)

        self.parent.top_panel.UpdateTitle(self.parent.right_panel.completed_page.total_item_count, self.GetCurrentPageName())

        self.downloading_page_btn.setUnactiveState()

    def onOpenDirEVT(self, event):
        Directory.open_directory(Config.Download.path)

    def UpdateButtonTitle(self):
        def worker():
            self.downloading_page_btn.setTitle(_("正在下载(%s)") % self.GetTotalDownloadingCount())
            self.completed_page_btn.setTitle(_("下载完成(%s)") % self.GetTotalCompletedCount())

        wx.CallAfter(worker)

    def GetCurrentPageName(self):
        return self.parent.right_panel.GetCurrentPageName()
    
    def GetTotalDownloadingCount(self):
        return self.parent.right_panel.downloading_page.total_item_count
    
    def GetTotalCompletedCount(self):
        return self.parent.right_panel.completed_page.total_item_count

class RightPanel(Panel):
    def __init__(self, parent: wx.Window):
        self.parent: DownloadManagerWindow = parent

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        self.set_dark_mode()

        self.book = wx.Simplebook(self, -1)

        self.downloading_page = DownloadingPage(self.book, self.parent, "正在下载")
        self.completed_page = CompletedPage(self.book, self.parent, "下载完成")

        self.book.AddPage(self.downloading_page, "正在下载")
        self.book.AddPage(self.completed_page, "下载完成")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.book, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def change_page(self, index: 0):
        self.book.SetSelection(index)
    
    def ShowDownloadingItemList(self, download_list: List[DownloadTaskInfo], callback: Callable = None, max_limit = False):
        self.downloading_page.scroller.info_list.extend(download_list)

        self.downloading_page.ShowItems(callback, max_limit = max_limit)

    def ShowCompletedItemList(self, download_list: List[DownloadTaskInfo], max_limit: bool = False):
        self.completed_page.scroller.info_list.extend(download_list)

        self.completed_page.ShowItems(max_limit = max_limit)

    def move_to_completed_page(self, task_info: DownloadTaskInfo):
        def worker():
            task_info.source = "下载完成"

            self.ShowCompletedItemList([task_info], max_limit = True)

            self.parent.top_panel.UpdateAllTitle(self.parent.left_panel.GetTotalCompletedCount(), "下载完成")

        wx.CallAfter(worker)

    def GetCurrentPageName(self):
        return self.book.GetPageText(self.book.GetSelection())

class Utils:
    index = 0

    @classmethod
    def create_download_file(cls, download_list: List[DownloadTaskInfo]):
        def update_index():
            match NumberType(Config.Download.number_type):
                case NumberType.From_1 | NumberType.Coherent:
                    entry.number = cls.index
                    entry.zero_padding_number = str(cls.index).zfill(len(str(len(download_list))))

                case NumberType.Episode_List:
                    entry.number = entry.list_number
                    entry.zero_padding_number = entry.list_number

        if NumberType(Config.Download.number_type) == NumberType.From_1:
            cls.index = 0

        last_aid = 0

        for index, entry in enumerate(download_list):
            entry.timestamp = cls.get_timestamp(index)
            entry.source = "正在下载"

            if last_aid != entry.aid:
                last_aid = entry.aid
                cls.index += 1

            update_index()

            entry.update()

    @staticmethod
    def get_timestamp(index):
        return DateTime.get_timestamp() + index

    @classmethod
    def read_download_files(cls):
        temp_task_info_list: List[DownloadTaskInfo] = []

        for file_name in os.listdir(Config.User.task_file_directory):
            file_path = os.path.join(Config.User.task_file_directory, file_name)

            if file_name.startswith("info_") and file_name.endswith(".json"):
                task_info = DownloadTaskInfo()
                task_info.load_from_file(file_path)

                if task_info.is_valid():
                    temp_task_info_list.append(task_info)
                else:
                    task_info.remove_file()

        return cls.task_info_filter(temp_task_info_list)

    @staticmethod
    def task_info_filter(task_info_list: List[DownloadTaskInfo]):
        temp_downloading_list: List[DownloadTaskInfo] = []
        temp_completed_list: List[DownloadTaskInfo] = []

        for task_info in task_info_list:
            if DownloadStatus(task_info.status) == DownloadStatus.Complete:
                temp_completed_list.append(task_info)
            else:
                if DownloadStatus(task_info.status) in [DownloadStatus.Downloading, DownloadStatus.Waiting, DownloadStatus.Merging]:
                    task_info.status = DownloadStatus.Pause.value

                temp_downloading_list.append(task_info)

        temp_downloading_list.sort(key = lambda x: x.timestamp, reverse = False)
        temp_completed_list.sort(key = lambda x: x.timestamp, reverse = False)

        return temp_downloading_list, temp_completed_list

    @staticmethod
    def get_hash_id_list():
        hash_id_list: List[str] = []

        window: DownloadManagerWindow = wx.FindWindowByName("download")

        hash_id_list.extend(window.right_panel.downloading_page.hash_id_list)
        hash_id_list.extend(window.right_panel.completed_page.hash_id_list)

        return hash_id_list

class DownloadManagerWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, _("下载管理"), style = self.get_window_style(), name = "download")
        
        self.set_window_params()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.top_panel = TopPanel(self)

        top_separate_line = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        self.left_panel = LeftPanel(self)

        middle_separate_line = wx.StaticLine(self, -1, style = wx.LI_VERTICAL)

        self.right_panel = RightPanel(self)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.left_panel, 0, wx.EXPAND)
        hbox.Add(middle_separate_line, 0, wx.EXPAND)
        hbox.Add(self.right_panel, 1, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.top_panel, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(hbox, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)
    
    def init_utils(self):
        def worker():
            downloading_list, completed_list = Utils.read_download_files()

            self.add_to_download_list(downloading_list)
            self.add_to_completed_list(completed_list)

        Thread(target = worker).start()
    
    def onCloseEVT(self, event):
        self.Hide()

    def add_to_download_list(self, download_list: List[DownloadTaskInfo], after_show_items_callback: Callable = None, create_local_file: bool = False, start_download: bool = False):
        def get_after_show_items_callback():
            if after_show_items_callback:
                after_show_items_callback()

            if start_download:
                self.right_panel.downloading_page.start_download()

            self.top_panel.UpdateAllTitle(self.right_panel.downloading_page.total_item_count, "正在下载")
        
        if create_local_file:
            Utils.create_download_file(download_list)

        wx.CallAfter(self.right_panel.ShowDownloadingItemList, download_list, get_after_show_items_callback, True)

    def add_to_completed_list(self, completed_list: List[DownloadTaskInfo]):
        wx.CallAfter(self.right_panel.ShowCompletedItemList, completed_list)
    
    def update_title(self, source: str, user_action: bool = False):
        page = self.get_page(source)

        count = page.total_item_count

        self.top_panel.UpdateAllTitle(count, source)

        page.scroller.Layout()

        if count == 0 and source == "正在下载" and not user_action and Config.Download.enable_notification:
            notification = NotificationManager(self)
            notification.show_toast(_("下载完成"), _("所有任务已下载完成"), flags = wx.ICON_INFORMATION)

    def remove_item(self, source: str):
        page = self.get_page(source)

        page.scroller.Remove()

    def start_next_task(self):
        self.load_next_task("正在下载", self.right_panel.downloading_page.start_download)
    
    def load_next_task(self, source: str, callback: Callable = None):
        def worker():
            page.ShowItems(callback, load_items = 1)

        page = self.get_page(source)

        if page.is_need_load_more():
            wx.CallAfter(worker)

        if callback:
            callback()

    def adjust_download_item_count(self, selection: int):
        self.right_panel.downloading_page.max_download_choice.SetSelection(selection)

        self.right_panel.downloading_page.start_download()

    def find_duplicate_task(self, download_task_list: List[DownloadTaskInfo]):
        to_download_hash_id_list = [entry.hash_id for entry in download_task_list]
        existing_hash_id_list = Utils.get_hash_id_list()

        duplicate_hash_id_list = list(set(to_download_hash_id_list) & set(existing_hash_id_list))

        duplicate_task_info_list = [entry for entry in download_task_list if entry.hash_id in duplicate_hash_id_list]

        return duplicate_task_info_list
    
    def remove_duplicate_task(self, download_task_list: List[DownloadTaskInfo], duplicate_hash_id_list: List[str]):
        return [entry for entry in download_task_list if entry.hash_id not in duplicate_hash_id_list]

    def set_window_params(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                if self.GetDPIScaleFactor() >= 1.5:
                    size = self.FromDIP((940, 550))
                else:
                    size = self.FromDIP((970, 580))
            
            case Platform.macOS:
                size = self.FromDIP((1000, 600))
            
            case Platform.Linux:
                size = self.FromDIP((1070, 650))

        self.SetSize(size)

    def get_page(self, source: str):
        match source:
            case "正在下载":
                return self.right_panel.downloading_page
            
            case "下载完成":
                return self.right_panel.completed_page
            
    def get_window_style(self):
        style = wx.DEFAULT_FRAME_STYLE

        if Config.Basic.always_on_top:
            style |= wx.STAY_ON_TOP

        return style