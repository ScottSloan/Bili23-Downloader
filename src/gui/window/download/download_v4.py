import wx
from datetime import datetime
from typing import List, Callable

from utils.config import Config

from utils.common.enums import Platform, NumberType
from utils.common.icon_v4 import Icon, IconID
from utils.common.directory import DirectoryUtils
from utils.common.data_type import DownloadTaskInfo

from gui.window.download.page import DownloadingPage, CompletedPage

from gui.component.button.action_button import ActionButton

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel

class TopPanel(Panel):
    def __init__(self, parent: wx.Window):
        self.parent: DownloadManagerWindow = parent

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        self.set_dark_mode()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 4))

        self.top_title_lab = wx.StaticText(self, -1, "下载管理")
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

        self.parent.left_panel.UpdateButtonTitle(count, source)

    def UpdateTitle(self, count: int, source: str):
        def worker():
            self.top_title_lab.SetLabel(title)

        if count:
            title = f"{count} 个任务{source}"
        else:
            title = "下载管理"

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

        self.downloading_page_btn = ActionButton(self, "正在下载(0)", name = "正在下载")
        self.downloading_page_btn.setBitmap(Icon.get_icon_bitmap(IconID.Downloading))
        self.completed_page_btn = ActionButton(self, "下载完成(0)", name = "下载完成")
        self.completed_page_btn.setBitmap(Icon.get_icon_bitmap(IconID.Complete))

        self.open_download_dir_btn = wx.Button(self, -1, "打开下载目录", size = self.FromDIP((120, 28)))

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
        DirectoryUtils.open_directory(Config.Download.path)

    def UpdateButtonTitle(self, count: int, source: str):
        def worker():
            action_button: ActionButton = wx.FindWindowByName(source, self)

            action_button.setTitle(f"{source}({count})")

        wx.CallAfter(worker)

    def GetCurrentPageName(self):
        return self.parent.right_panel.GetCurrentPageName()

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
    
    def ShowDownloadingItemList(self, download_list: List[DownloadTaskInfo], callback: Callable, start_download: bool):
        def after_show_items_callback():
            callback()

            if start_download:
                self.downloading_page.start_download()

        self.downloading_page.scroller.info_list.extend(download_list)

        self.downloading_page.scroller.ShowListItems(after_show_items_callback)

        self.downloading_page.show_task_info()

    def GetCurrentPageName(self):
        return self.book.GetPageText(self.book.GetSelection())

class Utils:
    index = 0

    @classmethod
    def create_download_file(cls, download_list: List[DownloadTaskInfo]):
        def update_index():
            if Config.Download.auto_add_number:
                match NumberType(Config.Download.number_type):
                    case NumberType.From_1 | NumberType.Coherent:
                        entry.number = cls.index
                        entry.zero_padding_number = str(cls.index).zfill(len(str(len(download_list))))

                    case NumberType.Episode_List:
                        entry.number = entry.list_number
                        entry.zero_padding_number = entry.list_number

        if NumberType(Config.Download.number_type) == NumberType.From_1:
            cls.index = 0

        last_cid = 0

        for index, entry in enumerate(download_list):
            entry.timestamp = cls.get_timestamp(index)
            entry.source = "正在下载"

            if last_cid != entry.cid:
                last_cid = entry.cid
                cls.index += 1

            update_index()

            entry.update()

    @staticmethod
    def get_timestamp(index):
        return round(datetime.now().timestamp()) + index

class DownloadManagerWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "下载管理")

        self.set_window_params()

        self.init_UI()

        self.Bind_EVT()

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
        pass
    
    def onCloseEVT(self, event):
        self.Hide()

    def add_to_download_list(self, download_list: List[DownloadTaskInfo], after_show_items_callback: Callable, create_local_file: bool = False, start_download: bool = False):
        def get_after_show_items_callback():
            after_show_items_callback()

            self.top_panel.UpdateAllTitle(self.right_panel.downloading_page.total_item_count, self.right_panel.GetCurrentPageName())
        
        if create_local_file:
            Utils.create_download_file(download_list)

        wx.CallAfter(self.right_panel.ShowDownloadingItemList, download_list, get_after_show_items_callback, start_download)

    def add_to_completed_list(self):
        pass
    
    def update_title(self, source: str):
        page: DownloadingPage = wx.FindWindowByName(source, self.right_panel)

        count = page.total_item_count

        self.top_panel.UpdateTitle(count, source)
        self.left_panel.UpdateButtonTitle(count, source)

        page.scroller.Layout()

    def remove_item(self, source: str):
        page: DownloadingPage = wx.FindWindowByName(source, self.right_panel)

        page.scroller.Remove()

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