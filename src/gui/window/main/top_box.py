import wx

from utils.common.style.icon_v4 import Icon, IconID

from utils.module.web.page import WebPage

from gui.window.main.utils import Window

from gui.component.text_ctrl.search_ctrl import SearchCtrl
from gui.component.button.flat_button import FlatButton
from gui.component.button.bitmap_button import BitmapButton
from gui.component.panel.panel import Panel

from gui.component.menu.url import URLMenu
from gui.component.menu.episode_option import EpisodeOptionMenu

class TopBox(Panel):
    def __init__(self, parent: wx.Window, main_window: wx.Window):
        from gui.window.main.main_v3 import MainWindow

        self.main_window: MainWindow = main_window

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        url_lab = wx.StaticText(self, -1, "链接")
        self.url_box = SearchCtrl(self, "在此处粘贴链接进行解析", search_btn = True, clear_btn = True)
        self.url_box.SetMenu(URLMenu())

        self.get_btn = wx.Button(self, -1, "Get")

        url_hbox = wx.BoxSizer(wx.HORIZONTAL)
        url_hbox.Add(url_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        url_hbox.Add(self.url_box, 1, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        url_hbox.Add(self.get_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.processing_icon = wx.StaticBitmap(self, -1, Icon.get_icon_bitmap(IconID.Loading), size = self.FromDIP((24, 24)))
        self.processing_icon.Hide()
        self.type_lab = wx.StaticText(self, -1, "")
        self.detail_btn = FlatButton(self, "详细信息", IconID.Info, split = True)
        self.detail_btn.setToolTip("查看视频详细信息")
        self.detail_btn.Hide()
        self.graph_btn = FlatButton(self, "剧情树", IconID.Tree_Structure)
        self.graph_btn.setToolTip("查看互动视频剧情树")
        self.graph_btn.Hide()
        self.search_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Search))
        self.search_btn.SetToolTip("搜索剧集列表")
        self.episode_option_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.List))
        self.episode_option_btn.SetToolTip("剧集列表显示设置")
        self.episode_option_btn.Enable(False)
        self.download_option_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Setting))
        self.download_option_btn.SetToolTip("下载选项")
        self.download_option_btn.Enable(False)

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.Add(self.processing_icon, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.AddSpacer(self.FromDIP(6))
        info_hbox.Add(self.detail_btn, 0, wx.EXPAND, self.FromDIP(6))
        info_hbox.Add(self.graph_btn, 0, wx.EXPAND, self.FromDIP(6))
        info_hbox.AddStretchSpacer()
        info_hbox.Add(self.search_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.episode_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.download_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(url_hbox, 0, wx.EXPAND)
        vbox.Add(info_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.search_btn.Bind(wx.EVT_BUTTON, self.onShowSearchDialogEVT)
        self.episode_option_btn.Bind(wx.EVT_BUTTON, self.onShowEpisodeOptionMenuEVT)
        self.download_option_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadOptionDialogEVT)

        self.url_box.Bind(wx.EVT_KEY_DOWN, self.onSearchKeyDownEVT)

        self.graph_btn.onClickCustomEVT = self.onShowGraphWindowEVT
        self.detail_btn.onClickCustomEVT = self.onShowDetailInfoDialogEVT

    def onShowSearchDialogEVT(self, event: wx.CommandEvent):
        Window.search_dialog(self)

    def onShowEpisodeOptionMenuEVT(self, event: wx.CommandEvent):
        menu = EpisodeOptionMenu()

        self.PopupMenu(menu)

    def onShowDownloadOptionDialogEVT(self, event: wx.CommandEvent):
        return Window.download_option_dialog(self)
    
    def onSearchKeyDownEVT(self, event: wx.KeyEvent):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.main_window.onParseEVT(event)
        
        event.Skip()

    def onShowGraphWindowEVT(self):
        WebPage.show_webpage(self, "graph.html")

    def onShowDetailInfoDialogEVT(self):
        Window.detail_dialog(self, self.main_window.parser.parse_type)