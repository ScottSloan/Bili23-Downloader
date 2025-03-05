import wx

from utils.common.icon_v2 import IconManager, IconType

from gui.templates import ActionButton, ScrolledPanel
from gui.download_item_v3 import DownloadTaskItemPanel, EmptyItemPanel

class DownloadManagerWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "下载管理 V3 Demo")

        self.SetSize(self.FromDIP((910, 550)))

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

        self.top_title_lab = wx.StaticText(top_panel, -1, "2 个任务正在下载")
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

        self.downloading_page_btn = ActionButton(left_panel, "正在下载(2)")
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

        self.downloading_page = DownloadingPage(self.book)
        self.completed_page = CompeltedPage(self.book)

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
    
    def init_utils(self):
        self.downloading_page_btn.setActiveState()
        
    def onDownloadingPageBtnEVT(self):
        self.book.SetSelection(0)

        self.completed_page_btn.setUnactiveState()

    def onCompletedPageBtnEVT(self):
        self.book.SetSelection(1)

        self.downloading_page_btn.setUnactiveState()

class DownloadingPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.init_utils()
    
    def init_UI(self):
        max_download_lab = wx.StaticText(self, -1, "并行下载数")
        self.max_download_choice = wx.Choice(self, -1, choices = [f"{i + 1}" for i in range(8)])

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
        test = DownloadTaskItemPanel(self.scroller)
        test.title_lab.SetLabel("500 ways to thrashing Hanloth")
        test.video_quality_lab.SetLabel("超高清 8K")
        test.video_codec_lab.SetLabel("H.264/AVC")
        test.video_size_lab.SetLabel("605.2 MB/2.3 GB")
        test.speed_lab.SetLabel("23.3 MB/s")
        test.progress_bar.SetValue(40)

        trick = DownloadTaskItemPanel(self.scroller)
        trick.title_lab.SetLabel("Tricking on Hanloth")
        trick.video_quality_lab.SetLabel("超高清 8K")
        trick.video_codec_lab.SetLabel("H.264/AVC")
        trick.video_size_lab.SetLabel("105.2 MB/1.5 GB")
        trick.speed_lab.SetLabel("18.9 MB/s")
        trick.progress_bar.SetValue(8)

        self.scroller.sizer.Add(test, 0, wx.EXPAND)
        self.scroller.sizer.Add(trick, 0, wx.EXPAND)

        self.scroller.Layout()
        self.scroller.SetupScrolling(scroll_x = False, scrollToTop = False)

class CompeltedPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

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
        empty = EmptyItemPanel(self.scroller)
    
        self.scroller.sizer.Add(empty, 1, wx.EXPAND)

        self.scroller.Layout()
        self.scroller.SetupScrolling(scroll_x = False, scrollToTop = False)