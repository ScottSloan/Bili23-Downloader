import wx

from gui.templates import ActionButton, ScrolledPanel

class DownloadManagerWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "下载管理")

        self.SetSize(self.FromDIP((850, 500)))

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        left_panel = wx.Panel(self, -1)
        left_panel.SetBackgroundColour("white")

        self.downloading_page_btn = ActionButton(left_panel, "正在下载(0)")
        self.completed_page_btn = ActionButton(left_panel, "下载完成(0)")

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

        separate_line = wx.StaticLine(self, -1, style = wx.LI_VERTICAL)

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
        hbox.Add(separate_line, 0, wx.EXPAND)
        hbox.Add(right_panel, 1, wx.EXPAND)

        self.SetSizer(hbox)

    def Bind_EVT(self):
        self.downloading_page_btn.Bind(wx.EVT_LEFT_DOWN, self.onDownloadingPageBtnEVT)
        self.completed_page_btn.Bind(wx.EVT_LEFT_DOWN, self.onCompletedPageBtnEVT)

    def onDownloadingPageBtnEVT(self, event):
        self.book.SetSelection(0)

        self.completed_page_btn.setUnactiveState()
        event.Skip()

    def onCompletedPageBtnEVT(self, event):
        self.book.SetSelection(1)

        self.downloading_page_btn.setUnactiveState()
        event.Skip()

class DownloadingPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()
    
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

class CompeltedPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

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