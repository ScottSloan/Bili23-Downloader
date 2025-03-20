import wx
import os
from datetime import datetime
from typing import List, Callable

from utils.common.icon_v2 import IconManager, IconType
from utils.common.data_type import DownloadTaskInfo, TaskPanelCallback, DownloadPageCallback
from utils.common.enums import DownloadStatus, ParseType
from utils.common.thread import Thread
from utils.common.cache import DataCache

from utils.module.notification import NotificationManager
from utils.tool_v2 import DownloadFileTool, FileDirectoryTool
from utils.config import Config, config_utils

from gui.component.frame import Frame
from gui.component.panel import Panel
from gui.component.action_button import ActionButton
from gui.component.scrolled_panel import ScrolledPanel
from gui.component.download_item_v3 import DownloadTaskItemPanel, EmptyItemPanel, LoadMoreTaskItemPanel

class DownloadManagerWindow(Frame):
    def __init__(self, parent):
        def get_window_size():
            match Config.Sys.platform:
                case "windows":
                    if self.GetDPIScaleFactor() >= 1.5:
                        return self.FromDIP((930, 550))
                    else:
                        return self.FromDIP((960, 580))
                
                case "darwin":
                    return self.FromDIP((1000, 600))
                
                case "linux":
                    return self.FromDIP((1070, 650))

        Frame.__init__(self, parent, "下载管理")

        self.SetSize(get_window_size())
        self.current_page = "正在下载"

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        icon_manager = IconManager(self)

        top_panel = Panel(self)
        top_panel.set_dark_mode()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 5))

        self.top_title_lab = wx.StaticText(top_panel, -1, "下载管理")
        self.top_title_lab.SetFont(font)

        top_panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_panel_hbox.AddSpacer(self.FromDIP(13))
        top_panel_hbox.Add(self.top_title_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        top_panel_vbox = wx.BoxSizer(wx.VERTICAL)
        top_panel_vbox.AddSpacer(self.FromDIP(6))
        top_panel_vbox.Add(top_panel_hbox, 0, wx.EXPAND)
        top_panel_vbox.AddSpacer(self.FromDIP(6))

        top_panel.SetSizerAndFit(top_panel_vbox)

        top_separate_line = wx.StaticLine(self, -1)

        left_panel = Panel(self)
        left_panel.set_dark_mode()

        self.downloading_page_btn = ActionButton(left_panel, "正在下载(0)")
        self.downloading_page_btn.setBitmap(icon_manager.get_icon_bitmap(IconType.DOWNLOADING_ICON))
        self.completed_page_btn = ActionButton(left_panel, "下载完成(0)")
        self.completed_page_btn.setBitmap(icon_manager.get_icon_bitmap(IconType.COMPLETED_ICON))

        self.open_download_dir_btn = wx.Button(left_panel, -1, "打开下载目录", size = self.FromDIP((120, 28)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.open_download_dir_btn, 0, wx.ALL, 10)
        bottom_hbox.AddStretchSpacer()

        left_panel_vbox = wx.BoxSizer(wx.VERTICAL)
        left_panel_vbox.Add(self.downloading_page_btn, 0, wx.EXPAND)
        left_panel_vbox.Add(self.completed_page_btn, 0, wx.EXPAND)
        left_panel_vbox.AddStretchSpacer()
        left_panel_vbox.Add(bottom_hbox, 0, wx.EXPAND)

        left_panel.SetSizerAndFit(left_panel_vbox)

        middle_separate_line = wx.StaticLine(self, -1, style = wx.LI_VERTICAL)

        right_panel = Panel(self)
        right_panel.set_dark_mode()

        self.book = wx.Simplebook(right_panel, -1)

        callback = DownloadPageCallback()
        callback.onSetTitleCallback = self.setTitleLabel
        callback.onAddPanelCallback = self.add_panel_to_completed_page
        callback.onStartNextCallback = self.start_download

        self.downloading_page = DownloadingPage(self.book, callback, self)
        self.completed_page = CompeltedPage(self.book, callback, self)

        self.book.AddPage(self.downloading_page, "downloading_page")
        self.book.AddPage(self.completed_page, "completed_page")

        right_panel_panel = wx.BoxSizer(wx.VERTICAL)
        right_panel_panel.Add(self.book, 1, wx.EXPAND)

        right_panel.SetSizerAndFit(right_panel_panel)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(left_panel, 0, wx.EXPAND)
        hbox.Add(middle_separate_line, 0, wx.EXPAND)
        hbox.Add(right_panel, 1, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_panel, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(hbox, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.downloading_page_btn.onClickCustomEVT = self.onDownloadingPageBtnEVT
        self.completed_page_btn.onClickCustomEVT = self.onCompletedPageBtnEVT

        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.open_download_dir_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadDirectoryEVT)
    
    def init_utils(self):
        self.downloading_page_btn.setActiveState()

        self.load_local_file()
    
    def load_local_file(self):
        def worker():
            def filter(task_info: DownloadTaskInfo):
                # 分为两类
                if task_info.status in [DownloadStatus.Complete.value]:
                    completed_temp_donwload_list.append(task_info)
                else:
                    if task_info.status in [DownloadStatus.Waiting.value, DownloadStatus.Downloading.value, DownloadStatus.Merging.value]:
                        task_info.status = DownloadStatus.Pause.value

                    downloading_temp_download_list.append(task_info)

                # 按照时间戳排序
                downloading_temp_download_list.sort(key = lambda x: x.timestamp, reverse = False)
                completed_temp_donwload_list.sort(key = lambda x: x.timestamp, reverse = False)

            def download_callback():
                pass

            def completed_callback():
                pass

            downloading_temp_download_list: List[DownloadTaskInfo] = []
            completed_temp_donwload_list: List[DownloadTaskInfo] = []

            for file_name in os.listdir(Config.User.download_file_directory):
                file_path = os.path.join(Config.User.download_file_directory, file_name)

                if os.path.isfile(file_path):
                    if file_name.startswith("info") and file_name.endswith("json"):
                        file_tool = DownloadFileTool(file_name = file_name)

                        # 检查文件兼容性
                        if not file_tool._check_compatibility():
                            file_tool.delete_file()
                            continue

                        task_info = DownloadTaskInfo()
                        task_info.load_from_dict(file_tool.get_info("task_info"))

                        filter(task_info)
            
            self.add_to_download_list(downloading_temp_download_list, download_callback, start_download = False)
            self.add_to_completed_list(completed_temp_donwload_list, completed_callback)

        Thread(target = worker).start()

    def add_to_download_list(self, download_list: List[DownloadTaskInfo], callback: Callable, start_download: bool = True):
        def create_local_file():
            def get_video_count():
                count = 0

                for temp_entry in download_list:
                    if ParseType(temp_entry.download_type) in [ParseType.Video, ParseType.Bangumi, ParseType.Cheese]:
                        count += 1

                return count

            def update_index():
                if video_count > 1 and Config.Download.add_number:
                    entry.number = index
                    entry.number_with_zero = str(index).zfill(len(str(len(download_list))))

            index = 0
            last_cid = None
            video_count = get_video_count()

            for list_index, entry in enumerate(download_list):
                if not entry.timestamp:
                    entry.timestamp = self.get_timestamp() + list_index

                if last_cid != entry.cid:
                    index += 1
                    last_cid = entry.cid

                update_index()

                download_local_file = DownloadFileTool(entry.id)

                # 如果本地文件为空，则写入内容
                if not download_local_file.get_info("task_info"):
                    download_local_file.write_file(entry)
            
            self.downloading_page.temp_download_list.extend(download_list)
        
        def download_callback():
            callback()

            if start_download:
                self.downloading_page.start_download()

        create_local_file()
        
        # 显示下载项
        wx.CallAfter(self.downloading_page.load_more_panel_item, download_callback)

    def add_to_completed_list(self, completed_list: List[DownloadTaskInfo], callback: Callable):
        self.completed_page.temp_download_list.extend(completed_list)

        wx.CallAfter(self.completed_page.load_more_panel_item, callback)

    def start_download(self):
        if self.downloading_page.temp_download_list and not self.downloading_page.scroller_count:
            wx.CallAfter(self.downloading_page.load_more_panel_item, self.downloading_page.start_download)
        else:
            self.downloading_page.start_download()

    def onCloseEVT(self, event):
        self.Hide()

    def onDownloadingPageBtnEVT(self):
        self.book.SetSelection(0)
        self.current_page = "正在下载"

        self.setTitleLabel("正在下载", self.downloading_page.total_count)

        self.completed_page_btn.setUnactiveState()

    def onCompletedPageBtnEVT(self):
        self.book.SetSelection(1)
        self.current_page = "下载完成"

        self.setTitleLabel("下载完成", self.completed_page.total_count)

        self.downloading_page_btn.setUnactiveState()

    def onOpenDownloadDirectoryEVT(self, event):
        FileDirectoryTool.open_directory(Config.Download.path)

    def setTitleLabel(self, name: str, count: int):
        if count:
            title = f"{count} 个任务{name}"
        else:
            title = "下载管理"

            self.RequestUserAttention(wx.USER_ATTENTION_ERROR)

        if self.current_page == name:
            self.top_title_lab.SetLabel(title)

        if name == "正在下载":
            self.downloading_page_btn.setTitle(f"正在下载({count})")
            self.downloading_page_btn.Refresh()
        else:
            self.completed_page_btn.setTitle(f"下载完成({count})")
            self.downloading_page_btn.Refresh()

    def add_panel_to_completed_page(self, task_info: DownloadTaskInfo):
        self.completed_page.add_panel(task_info)

    def get_timestamp(self):
        return int(datetime.now().timestamp())

class SimplePage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

    def load_more_panel_item(self, callback: Callable = None):
        def get_download_list():
            # 当前限制每次加载 100 个
            item_per_time = 100

            temp_download_list = self.temp_download_list[:item_per_time]
            self.temp_download_list = self.temp_download_list[item_per_time:]

            return temp_download_list

        def get_items():
            def get_callback():
                callback = TaskPanelCallback()
                callback.onUpdateCountTitleCallback = self.refresh_scroller
                callback.onAddPanelCallback = self.callback.onAddPanelCallback
                callback.onStartNextCallback = self.callback.onStartNextCallback

                return callback

            items = []

            for entry in get_download_list():
                item = DownloadTaskItemPanel(self.scroller, entry, get_callback(), self.download_window)
                items.append((item, 0, wx.EXPAND))

            count = len(self.temp_download_list)

            # 显示加载更多
            if count:
                item = LoadMoreTaskItemPanel(self.scroller, count, self.load_more_panel_item)
                items.append((item, 0, wx.EXPAND))
            
            return items
        
        self.hide_other_item()

        items = get_items()

        if items:
            self.scroller.Freeze()
            self.scroller.sizer.AddMany(items)
            self.scroller.Thaw()

        self.refresh_scroller()

        # 显示封面
        Thread(target = self.show_panel_item_cover).start()

        # 回调函数
        if callback:
            callback()

    def hide_other_item(self):
        # 隐藏显示更多和空白占位 Panel
        for panel in self.scroller_children:
            if isinstance(panel, LoadMoreTaskItemPanel):
                panel.destroy_panel()
            
            elif isinstance(panel, EmptyItemPanel):
                panel.destroy_panel()

    def show_panel_item_cover(self):
        for panel in self.scroller_children:
            if isinstance(panel, DownloadTaskItemPanel):
                panel.show_cover()

        # 封面显示完成后，清除图片换成
        DataCache.clear_cache()

    def refresh_scroller(self, show_toast: bool = False):
        if self.is_scroller_empty:
            if self.temp_download_list:
                wx.CallAfter(self.load_more_panel_item)
            else:
                self.hide_other_item()

                item = EmptyItemPanel(self.scroller, self.name)
                self.scroller.sizer.Add(item, 1, wx.EXPAND)

        self.scroller.Layout()
        self.scroller.SetupScrolling(scroll_x = False, scrollToTop = False)

        self.callback.onSetTitleCallback(self.name, self.total_count)

        if self.name == "正在下载":
            if not self.total_count and show_toast:
                notification = NotificationManager(self)
                notification.show_toast("下载完成", "所有任务已下载完成", flags = wx.ICON_INFORMATION)

    def get_scroller_task_count(self, condition: List[int]):
        _count = 0

        for panel in self.scroller_children:
            if isinstance(panel, DownloadTaskItemPanel):
                if panel.task_info.status in condition:
                    _count += 1

        return _count
    
    @property
    def scroller_children(self):
        children: List[DownloadTaskItemPanel] = self.scroller.GetChildren()
        return children 

    @property
    def is_scroller_empty(self):
        count = 0

        for panel in self.scroller_children:
            if isinstance(panel, DownloadTaskItemPanel):
                count += 1

        return not count

class DownloadingPage(SimplePage):
    def __init__(self, parent, callback: DownloadPageCallback, download_window):
        self.callback, self.name, self.download_window = callback, "正在下载", download_window

        SimplePage.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()
    
    def init_UI(self):
        self.set_dark_mode()

        max_download_lab = wx.StaticText(self, -1, "并行下载数")
        self.max_download_choice = wx.Choice(self, -1, choices = [f"{i + 1}" for i in range(10)])
        self.max_download_choice.SetSelection(Config.Download.max_download_count - 1)

        self.start_all_btn = wx.Button(self, -1, "全部开始")
        self.pause_all_btn = wx.Button(self, -1, "全部暂停")
        self.cancel_all_btn = wx.Button(self, -1, "全部取消")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(max_download_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        top_hbox.Add(self.max_download_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.start_all_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        top_hbox.Add(self.pause_all_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        top_hbox.Add(self.cancel_all_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        top_separate_line = wx.StaticLine(self, -1)

        self.scroller = ScrolledPanel(self)
        self.scroller.set_dark_mode()
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(self.scroller, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def init_utils(self):
        self.temp_download_list: List[DownloadTaskInfo] = []

    def Bind_EVT(self):
        self.start_all_btn.Bind(wx.EVT_BUTTON, self.onStartAllEVT)
        self.pause_all_btn.Bind(wx.EVT_BUTTON, self.onPauseAllEVT)
        self.cancel_all_btn.Bind(wx.EVT_BUTTON, self.onCancelAllEVT)

        self.max_download_choice.Bind(wx.EVT_CHOICE, self.onMaxDownloadChangeEVT)

    def start_download(self, start_all: bool = False):
        # 开始下载
        for panel in self.scroller_children:
            if isinstance(panel, DownloadTaskItemPanel):
                if panel.task_info.status == DownloadStatus.Pause.value and start_all:
                    panel.set_download_status(DownloadStatus.Waiting.value)

                if panel.task_info.status == DownloadStatus.Waiting.value:
                    if self.get_scroller_task_count([DownloadStatus.Downloading.value]) < Config.Download.max_download_count:
                        panel.resume_download()
    
    def onStartAllEVT(self, event):
        self.start_download(start_all = True)

    def onPauseAllEVT(self, event):
        for panel in self.scroller_children:
            if isinstance(panel, DownloadTaskItemPanel):
                if panel.task_info.status in DownloadStatus.Alive.value:
                    panel.pause_download()

    def onCancelAllEVT(self, event):
        def clear_scroller():
            # 取消 scroller 中的任务
            for panel in self.scroller_children:
                if isinstance(panel, DownloadTaskItemPanel):
                    if panel.task_info.status in DownloadStatus.Alive_Ex.value:
                        panel.onStopEVT(0)

        def clear_temp():
            # 取消 temp_download_list 中的任务
            items = []

            for entry in self.temp_download_list:
                if entry.status in DownloadStatus.Alive_Ex.value:
                    DownloadFileTool.delete_file_by_id(entry.id)
                else:
                    items.append(entry)
            
            self.temp_download_list = items

        clear_scroller()

        clear_temp()

        self.refresh_scroller()

    def onMaxDownloadChangeEVT(self, event):
        Config.Download.max_download_count = int(self.max_download_choice.GetStringSelection())

        count = 0

        for panel in self.scroller_children:
            if isinstance(panel, DownloadTaskItemPanel):
                if self.get_scroller_task_count([DownloadStatus.Downloading.value]) < Config.Download.max_download_count:
                    if panel.task_info.status in [DownloadStatus.Waiting.value, DownloadStatus.Pause.value]:
                        panel.resume_download()
                else:
                    if panel.task_info.status == DownloadStatus.Downloading.value:
                        count += 1

                        if count > Config.Download.max_download_count:
                            panel.pause_download(set_waiting_status = True)
        
        kwargs = {
            "max_download_count": Config.Download.max_download_count
        }

        config_utils.update_config_kwargs(Config.APP.app_config_path, "download", **kwargs)
    
    @property
    def scroller_count(self):
        return self.get_scroller_task_count(DownloadStatus.Alive.value)
    
    @property
    def total_count(self):
        return self.scroller_count + len(self.temp_download_list)

class CompeltedPage(SimplePage):
    def __init__(self, parent, callback: DownloadPageCallback, download_window):
        self.callback, self.name, self.download_window = callback, "下载完成", download_window

        SimplePage.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.set_dark_mode()

        self.clear_history_btn = wx.Button(self, -1, "清除下载记录")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.clear_history_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        top_separate_line = wx.StaticLine(self, -1)

        self.scroller = ScrolledPanel(self)
        self.scroller.set_dark_mode()
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(self.scroller, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def init_utils(self):
        self.temp_download_list: List[DownloadTaskInfo] = []

    def Bind_EVT(self):
        self.clear_history_btn.Bind(wx.EVT_BUTTON, self.onClearHistoryEVT)

    def onClearHistoryEVT(self, event):
        def clear_scroller():
            for panel in self.scroller_children:
                if isinstance(panel, DownloadTaskItemPanel):
                    if panel.task_info.status in [DownloadStatus.Complete.value]:
                        panel.onStopEVT(0)

        def clear_temp():
            for entry in self.temp_download_list:
                if entry.status in [DownloadStatus.Complete.value]:
                    DownloadFileTool.delete_file_by_id(entry.id)

            self.temp_download_list.clear()

        clear_scroller()

        clear_temp()

        self.refresh_scroller()

    def add_panel(self, task_info: DownloadTaskInfo):
        self.temp_download_list.append(task_info)

        self.load_more_panel_item()

    @property
    def scroller_count(self):
        return self.get_scroller_task_count([DownloadStatus.Complete.value])
    
    @property
    def total_count(self):
        return self.scroller_count + len(self.temp_download_list)