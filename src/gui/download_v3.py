import wx
import os
from datetime import datetime
from typing import List, Callable

from utils.common.icon_v2 import IconManager, IconType
from utils.common.data_type import DownloadTaskInfo, TaskPanelCallback
from utils.common.enums import DownloadStatus
from utils.common.thread import Thread
from utils.tool_v2 import DownloadFileTool
from utils.config import Config

from gui.templates import ActionButton, ScrolledPanel
from gui.download_item_v3 import DownloadTaskItemPanel, EmptyItemPanel, LoadMoreTaskItemPanel

class DownloadManagerWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "下载管理 V3 Demo")

        self.SetSize(self.FromDIP((930, 550)))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        icon_manager = IconManager(self)

        top_panel = wx.Panel(self, -1)
        top_panel.SetBackgroundColour("white")

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 5))

        self.top_title_lab = wx.StaticText(top_panel, -1, "下载管理")
        self.top_title_lab.SetFont(font)

        top_panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_panel_hbox.AddSpacer(20)
        top_panel_hbox.Add(self.top_title_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        top_panel_vbox = wx.BoxSizer(wx.VERTICAL)
        top_panel_vbox.AddSpacer(10)
        top_panel_vbox.Add(top_panel_hbox, 0, wx.EXPAND)
        top_panel_vbox.AddSpacer(10)

        top_panel.SetSizerAndFit(top_panel_vbox)

        top_separate_line = wx.StaticLine(self, -1)

        left_panel = wx.Panel(self, -1)
        left_panel.SetBackgroundColour("white")

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

        right_panel = wx.Panel(self, -1)
        right_panel.SetBackgroundColour("white")

        self.book = wx.Simplebook(right_panel, -1)

        self.downloading_page = DownloadingPage(self.book, self.setTitleLabel, self)
        self.completed_page = CompeltedPage(self.book, self.setTitleLabel, self)

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
    
    def init_utils(self):
        self.downloading_page_btn.setActiveState()

        self.load_local_file()
    
    def load_local_file(self):
        def callback():
            pass
        
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

        downloading_temp_download_list = []
        completed_temp_donwload_list = []

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
        
        self.add_to_download_list(downloading_temp_download_list, callback)
        self.add_to_completed_list(completed_temp_donwload_list)

    def add_to_download_list(self, download_list: List[DownloadTaskInfo], callback: Callable):
        def create_local_file():
            def update_index():
                if len(download_list) and Config.Download.add_number:
                    entry.index = index + 1
                    entry.index_with_zero = str(index + 1).zfill(len(str(len(download_list))))

            for index, entry in enumerate(download_list):
                # 记录时间戳
                if not entry.timestamp:
                    entry.timestamp = self.get_timestamp() + index

                # 更新序号
                if not entry.index:
                    update_index()

                download_local_file = DownloadFileTool(entry.id)

                # 如果本地文件为空，则写入内容
                if not download_local_file.get_info("task_info"):
                    download_local_file.write_file(entry)
            
            self.downloading_page.temp_download_list.extend(download_list)
        
        create_local_file()
        
        # 显示下载项
        wx.CallAfter(self.downloading_page.load_more_panel_item, callback)

    def add_to_completed_list(self, completed_list: List[DownloadTaskInfo]):
        def callback():
            pass

        self.completed_page.temp_download_list.extend(completed_list)

        wx.CallAfter(self.completed_page.load_more_panel_item, callback, update_title = False)

    def onCloseEVT(self, event):
        self.Hide()

    def onDownloadingPageBtnEVT(self):
        self.book.SetSelection(0)

        self.setTitleLabel("正在下载", self.downloading_page.total_count)

        self.completed_page_btn.setUnactiveState()

    def onCompletedPageBtnEVT(self):
        self.book.SetSelection(1)

        self.setTitleLabel("下载完成", self.completed_page.total_count)

        self.downloading_page_btn.setUnactiveState()

    def setTitleLabel(self, name: str, count: int):
        if count:
            title = f"{count} 个任务{name}"
        else:
            title = "下载管理"

        self.top_title_lab.SetLabel(title)

        if name == "正在下载":
            self.downloading_page_btn.setTitle(f"正在下载({count})")
            self.downloading_page_btn.Refresh()
        else:
            self.completed_page_btn.setTitle(f"下载完成({count})")
            self.downloading_page_btn.Refresh()

    def get_timestamp(self):
        return int(datetime.now().timestamp())

class SimplePage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

    def load_more_panel_item(self, callback: Callable = None, update_title = True):
        def get_download_list():
            # 当前限制每次加载 50 个
            item_threshold = 50

            temp_download_list = self.temp_download_list[:item_threshold]
            self.temp_download_list = self.temp_download_list[item_threshold:]

            return temp_download_list

        def get_items():
            def get_callback():
                callback = TaskPanelCallback()
                callback.onUpdateCountTitleCallback = self.refresh_scroller

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
        
        # 隐藏显示更多项目
        self.hide_other_item()

        # 批量添加下载项
        self.scroller.Freeze()
        self.scroller.sizer.AddMany(get_items())
        self.scroller.Thaw()

        if update_title:
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

    def refresh_scroller(self):
        if not self.total_count:
            self.hide_other_item()

            item = EmptyItemPanel(self.scroller, self.name)
            self.scroller.sizer.Add(item, 1, wx.EXPAND)

        elif not self.scroller_count:
            wx.CallAfter(self.load_more_panel_item)

        self.scroller.Layout()
        self.scroller.SetupScrolling(scroll_x = False, scrollToTop = False)

        self.callback(self.name, self.total_count)

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

class DownloadingPage(SimplePage):
    def __init__(self, parent, callback: Callable, download_window):
        self.callback, self.name, self.download_window = callback, "正在下载", download_window

        SimplePage.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()
    
    def init_UI(self):
        max_download_lab = wx.StaticText(self, -1, "并行下载数")
        self.max_download_choice = wx.Choice(self, -1, choices = [f"{i + 1}" for i in range(8)])
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
        self.scroller.SetBackgroundColour("white")
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_separate_line, 0, wx.EXPAND)
        vbox.Add(self.scroller, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def init_utils(self):
        self.temp_download_list: List[DownloadTaskInfo] = []

    def Bind_EVT(self):
        self.cancel_all_btn.Bind(wx.EVT_BUTTON, self.onCancelAllEVT)

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

    @property
    def scroller_count(self):
        return self.get_scroller_task_count(DownloadStatus.Alive.value)
    
    @property
    def total_count(self):
        return self.scroller_count + len(self.temp_download_list)

class CompeltedPage(SimplePage):
    def __init__(self, parent, callback: Callable, download_window):
        self.callback, self.name, self.download_window = callback, "下载完成", download_window

        SimplePage.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.clear_history_btn = wx.Button(self, -1, "清除下载记录")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.clear_history_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        top_separate_line = wx.StaticLine(self, -1)

        self.scroller = ScrolledPanel(self)
        self.scroller.SetBackgroundColour("white")
        
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

    @property
    def scroller_count(self):
        return self.get_scroller_task_count([DownloadStatus.Complete.value])
    
    @property
    def total_count(self):
        return self.scroller_count + len(self.temp_download_list)