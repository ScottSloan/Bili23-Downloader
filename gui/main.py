import wx

from utils.config import Config

from gui.templates import *
from gui.taskbar import TaskBarIcon

class MainWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Bili23 Downloader")

        self.SetIcon(wx.Icon(Config.res_logo))
        self.SetSize(self.FromDIP((800, 480)))
        self.Center()
        self.panel = wx.Panel(self, -1)

        self.init_controls()

    def init_controls(self):
        self.infobar = InfoBar(self.panel)

        self.address_lb = wx.StaticText(self.panel, -1, "地址")
        self.address_tc = wx.TextCtrl(self.panel, -1, style = wx.TE_PROCESS_ENTER)
        self.get_button = wx.Button(self.panel, -1, "Get")

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.address_lb, 0, wx.ALL | wx.CENTER, 10)
        hbox1.Add(self.address_tc, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)
        hbox1.Add(self.get_button, 0, wx.ALL, 10)

        self.list_lb = wx.StaticText(self.panel, -1, "视频")
        self.quality_lb = wx.StaticText(self.panel, -1, "清晰度")
        self.quality_cb = wx.Choice(self.panel, -1)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(self.list_lb, 0, wx.LEFT | wx.CENTER, 10)
        hbox2.AddStretchSpacer(1)
        hbox2.Add(self.quality_lb, 0, wx.CENTER | wx.RIGHT, 10)
        hbox2.Add(self.quality_cb, 0, wx.RIGHT, 10)

        self.list_lc = TreeListCtrl(self.panel)

        self.info_btn = wx.Button(self.panel, -1, "视频信息", size = self.FromDIP((90, 30)))
        self.info_btn.Enable(False)
        self.download_manager_btn = wx.Button(self.panel, -1, "下载管理", size = self.FromDIP((90, 30)))
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = self.FromDIP((90, 30)))
        self.download_btn.Enable(False)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(self.info_btn, 0, wx.BOTTOM | wx.LEFT, 10)
        hbox3.AddStretchSpacer(1)
        hbox3.Add(self.download_manager_btn)
        hbox3.Add(self.download_btn, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.infobar, 0, wx.EXPAND)
        vbox.Add(hbox1, 0, wx.EXPAND, 10)
        vbox.Add(hbox2, 0, wx.EXPAND)
        vbox.Add(self.list_lc, 1, wx.EXPAND | wx.ALL, 10)
        vbox.Add(hbox3, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)

        self.init_menu_bar()
        self.init_taskbar()

    def init_menu_bar(self):
        menu_bar = wx.MenuBar()
        self.about_menu = wx.Menu()
        self.tool_menu = wx.Menu()

        check_menuitem = wx.MenuItem(self.about_menu, 110, "检查更新(&U)")
        help_menuitem = wx.MenuItem(self.about_menu, 120, "使用帮助(&C)")
        about_menuitem = wx.MenuItem(self.about_menu, 130, "关于(&A)")

        option_menuitem = wx.MenuItem(self.tool_menu, 140, "设置(&S)")

        menu_bar.Append(self.tool_menu, "工具(&T)")
        menu_bar.Append(self.about_menu, "帮助(&H)")

        self.tool_menu.Append(option_menuitem)
        self.about_menu.Append(check_menuitem)
        self.about_menu.AppendSeparator()
        self.about_menu.Append(help_menuitem)
        self.about_menu.Append(about_menuitem)

        self.SetMenuBar(menu_bar)
    
    def init_taskbar(self):
        if not Config.show_icon: return

        TaskBarIcon()