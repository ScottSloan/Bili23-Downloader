import wx
import asyncio
import webbrowser

from utils.config import Config

from utils.common.enums import Platform, EpisodeDisplayType, ProcessingType, ExitOption, ParseStatus
from utils.common.style.icon_v4 import Icon, IconID
from utils.common.thread import Thread
from utils.common.exception import GlobalException

from utils.module.clipboard import ClipBoard
from utils.module.pic.cover import Cover
from utils.module.ffmpeg_v2 import FFmpeg
from utils.module.web.page import WebPage

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel

from gui.id import ID

from gui.dialog.misc.processing import ProcessingWindow

from gui.window.main.parser import Parser
from gui.window.main.utils import Utils, Window

from gui.window.download.download_v4 import DownloadManagerWindow
from gui.window.live_recording import LiveRecordingWindow

from gui.component.text_ctrl.search_ctrl import SearchCtrl
from gui.component.button.flat_button import FlatButton
from gui.component.button.bitmap_button import BitmapButton
from gui.component.button.button import Button
from gui.component.misc.taskbar_icon import TaskBarIcon
from gui.component.tree_list_v2 import TreeListCtrl

from gui.component.menu.episode_option import EpisodeOptionMenu
from gui.component.menu.user import UserMenu
from gui.component.menu.url import URLMenu

class MainWindow(Frame):
    def __init__(self, parent):
        self.utils = Utils(self)

        Frame.__init__(self, parent, Config.APP.name)

        self.set_window_params()

        self.get_sys_settings()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.panel = Panel(self)

        url_lab = wx.StaticText(self.panel, -1, "链接")
        self.url_box = SearchCtrl(self.panel, "在此处粘贴链接进行解析", search_btn = True, clear_btn = True)
        self.url_box.SetMenu(URLMenu())

        self.get_btn = wx.Button(self.panel, -1, "Get")

        url_hbox = wx.BoxSizer(wx.HORIZONTAL)
        url_hbox.Add(url_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        url_hbox.Add(self.url_box, 1, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        url_hbox.Add(self.get_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.processing_icon = wx.StaticBitmap(self.panel, -1, Icon.get_icon_bitmap(IconID.Loading), size = self.FromDIP((24, 24)))
        self.processing_icon.Hide()
        self.type_lab = wx.StaticText(self.panel, -1, "")
        self.detail_btn = FlatButton(self.panel, "详细信息", IconID.Info, split = True)
        self.detail_btn.setToolTip("查看视频详细信息")
        self.detail_btn.Hide()
        self.graph_btn = FlatButton(self.panel, "剧情树", IconID.Tree_Structure)
        self.graph_btn.setToolTip("查看互动视频剧情树")
        self.graph_btn.Hide()
        self.search_btn = BitmapButton(self.panel, Icon.get_icon_bitmap(IconID.Search))
        self.search_btn.SetToolTip("搜索剧集列表")
        self.episode_option_btn = BitmapButton(self.panel, Icon.get_icon_bitmap(IconID.List))
        self.episode_option_btn.SetToolTip("剧集列表显示设置")
        self.episode_option_btn.Enable(False)
        self.download_option_btn = BitmapButton(self.panel, Icon.get_icon_bitmap(IconID.Setting))
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

        self.episode_list = TreeListCtrl(self.panel, self)

        self.face_icon = wx.StaticBitmap(self.panel, -1, size = self.FromDIP((32, 32)))
        self.face_icon.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.face_icon.Hide()
        self.uname_lab = wx.StaticText(self.panel, -1, "未登录")
        self.uname_lab.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.download_mgr_btn = Button(self.panel, "下载管理", size = self.get_scaled_size((100, 30)))
        self.download_btn = Button(self.panel, "开始下载", size = self.get_scaled_size((100, 30)))
        self.download_btn.Enable(False)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.face_icon, 0, wx.ALL & (~wx.RIGHT), self.FromDIP(6))
        bottom_hbox.Add(self.uname_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.Add(self.download_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(url_hbox, 0, wx.EXPAND)
        vbox.Add(info_hbox, 0, wx.EXPAND)
        vbox.Add(self.episode_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)

        self.init_menubar()

        self.clipboard_timer = wx.Timer(self, -1)

        self.taskbar_icon = TaskBarIcon(self)

    def init_menubar(self):
        menu_bar = wx.MenuBar()

        tool_menu = wx.Menu()
        help_menu = wx.Menu()

        if Config.User.login:
            tool_menu.Append(ID.LOGOUT_MENU, "注销(&L)")
        else:
            tool_menu.Append(ID.LOGIN_MENU, "登录(&L)")

        tool_menu.AppendSeparator()

        if Config.Misc.enable_debug:
            tool_menu.Append(ID.DEBUG_MENU, "调试(&D)")

        tool_menu.Append(ID.LIVE_RECORDING_MENU, "直播录制(&R)")
        tool_menu.Append(ID.FORMAT_FACTORY_MENU, "视频工具箱(&F)")
        tool_menu.AppendSeparator()
        tool_menu.Append(ID.SETTINGS_MENU, "设置(&S)")

        help_menu.Append(ID.CHECK_UPDATE_MENU, "检查更新(&U)")
        help_menu.Append(ID.CHANGELOG_MENU, "更新日志(&P)")
        help_menu.AppendSeparator()
        help_menu.Append(ID.HELP_MENU, "使用帮助(&C)")
        help_menu.AppendSeparator()
        help_menu.Append(ID.FEEDBACK_MENU, "报告问题(&B)")
        help_menu.Append(ID.COMMUNITY_MENU, "社区交流(&G)")
        help_menu.AppendSeparator()
        help_menu.Append(ID.ABOUT_MENU, "关于(&A)")

        menu_bar.Append(tool_menu, "工具(&T)")
        menu_bar.Append(help_menu, "帮助(&H)")

        self.SetMenuBar(menu_bar)

    def Bind_EVT(self):
        self.Bind(wx.EVT_MENU, self.onMenuEVT)
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)
        
        self.url_box.Bind(wx.EVT_KEY_DOWN, self.onSearchKeyDownEVT)
        self.get_btn.Bind(wx.EVT_BUTTON, self.onParseEVT)

        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadWindowEVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.onDownloadEVT)

        self.search_btn.Bind(wx.EVT_BUTTON, self.onShowSearchDialogEVT)
        self.episode_option_btn.Bind(wx.EVT_BUTTON, self.onShowEpisodeOptionMenuEVT)
        self.download_option_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadOptionDialogEVT)

        self.face_icon.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)
        self.uname_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)

        self.detail_btn.onClickCustomEVT = self.onShowDetailInfoDialogEVT
        self.graph_btn.onClickCustomEVT = self.onShowGraphWindowEVT

        self.episode_list.Bind(wx.EVT_MENU, self.onEpisodeListContextMenuEVT)

        self.Bind(wx.EVT_TIMER, self.utils.read_clipboard, self.clipboard_timer)

    def init_utils(self):
        def worker():
            FFmpeg.Env.detect()

            asyncio.run(self.utils.async_worker())

            self.utils.show_welcome_dialog()

        self.parser = Parser(self)

        self.processing_window = ProcessingWindow(self)
        self.download_window = DownloadManagerWindow(self)
        self.live_recording_window = LiveRecordingWindow(self)

        self.utils.init_timer()

        Thread(target = worker).start()

    def onMenuEVT(self, event: wx.MenuEvent):
        match event.GetId():
            case ID.LOGIN_MENU:
                Window.login_dialog(self)

            case ID.LOGOUT_MENU:
                dlg = wx.MessageDialog(self, '退出登录\n\n是否要退出登录？', "警告", wx.ICON_WARNING | wx.YES_NO)

                if dlg.ShowModal() == wx.ID_YES:
                    self.utils.user_logout()

            case ID.REFRESH_MENU:
                Thread(target = self.utils.user_refresh).start()

            case ID.DEBUG_MENU:
                Window.debug_window(self)

            case ID.LIVE_RECORDING_MENU:
                self.onShowLiveRecordingWindowEVT(event)

            case ID.FORMAT_FACTORY_MENU:
                Window.format_factory_window(self)

            case ID.SETTINGS_MENU:
                Window.settings_window(self)

            case ID.CHECK_UPDATE_MENU:
                Thread(target = self.utils.check_update, args = (True,)).start()

            case ID.CHANGELOG_MENU:
                Thread(target = self.utils.get_changelog).start()

            case ID.HELP_MENU:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/use/basic.html")

            case ID.FEEDBACK_MENU:
                webbrowser.open("https://github.com/ScottSloan/Bili23-Downloader/issues")

            case ID.COMMUNITY_MENU:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/community.html")

            case ID.SUPPORTTED_URL_MENU:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/use/url.html")

            case ID.ABOUT_MENU:
                Window.about_window(self)

            case ID.EPISODE_SINGLE_MENU:
                self.utils.set_episode_display_mode(EpisodeDisplayType.Single)

            case ID.EPISODE_IN_SECTION_MENU:
                self.utils.set_episode_display_mode(EpisodeDisplayType.In_Section)

            case ID.EPISODE_ALL_SECTIONS_MENU:
                self.utils.set_episode_display_mode(EpisodeDisplayType.All)
                
            case ID.EPISODE_FULL_NAME_MENU:
                self.utils.set_episode_full_name()

    def onCloseEVT(self, event: wx.CloseEvent):
        def show_exit_dialog():
            dlg = wx.MessageDialog(self, "退出程序\n\n确定要退出程序吗？", "提示", style = wx.ICON_INFORMATION | wx.YES_NO | wx.CANCEL)
            dlg.SetYesNoCancelLabels("最小化到托盘", "退出程序", "取消")

            return dlg.ShowModal()
        
        if ExitOption(Config.Basic.exit_option) in [ExitOption.Ask, ExitOption.AskOnce]:
            flag = show_exit_dialog()

            if flag == wx.ID_CANCEL:
                return
        
            self.utils.save_exit_dialog_settings(flag)

        self.utils.save_window_params_settings()

        match ExitOption(Config.Basic.exit_option):
            case ExitOption.TaskIcon:
                self.Hide()
                return
            
            case ExitOption.Exit:
                self.clipboard_timer.Stop()
                self.taskbar_icon.Destroy()

                event.Skip()

    def onShowDownloadWindowEVT(self, event: wx.CommandEvent = None):
        if not event and not Config.Basic.auto_show_download_window:
            return

        if not self.download_window.IsShown():
            self.download_window.Show()
        
        elif self.download_window.IsIconized():
            if Config.Basic.auto_show_download_window:
                self.download_window.Iconize(False)
        
        self.download_window.Raise()

    def onShowLiveRecordingWindowEVT(self, event: wx.CommandEvent):
        if not self.live_recording_window.IsShown():
            self.live_recording_window.Show()

        elif self.live_recording_window.IsIconized():
            self.Iconize(False)

        self.live_recording_window.Raise()

    def onDownloadEVT(self, event):
        def after_show_items_callback():
            self.utils.hide_processing_window()
            self.onShowDownloadWindowEVT()

        try:
            if self.utils.check_download_items():
                return
            
            if Config.Basic.auto_popup_option_dialog:
                if self.onShowDownloadOptionDialogEVT(event) != wx.ID_OK:
                    return

            self.episode_list.GetAllCheckedItem(self.parser.video_quality_id, self.parser.video_codec_id)

            Thread(target = self.download_window.add_to_download_list, args = (self.episode_list.download_task_info_list, after_show_items_callback, True, True)).start()

            self.utils.show_processing_window(ProcessingType.Process)
        
        except Exception as e:
            raise GlobalException(callback = self.parser.onError) from e
        
    def onParseEVT(self, event):
        url = self.url_box.GetValue()

        if self.utils.check_url(url):
            return

        self.episode_list.init_episode_list()

        self.utils.set_status(ParseStatus.Parsing)

        Thread(target = self.parser.parse_url, args = (url, )).start()

    def onSearchKeyDownEVT(self, event: wx.KeyEvent):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.onParseEVT(event)
        
        event.Skip()

    def onShowSearchDialogEVT(self, event: wx.CommandEvent):
        Window.search_dialog(self)

    def onShowEpisodeOptionMenuEVT(self, event: wx.CommandEvent):
        menu = EpisodeOptionMenu()

        self.PopupMenu(menu)

    def onShowUserMenuEVT(self, event: wx.MouseEvent):
        if Config.User.login:
            menu = UserMenu()

            self.PopupMenu(menu)
        else:
            evt = wx.PyCommandEvent(wx.EVT_MENU.typeId, id = ID.LOGIN_MENU)
            wx.PostEvent(self.GetEventHandler(), evt)

    def onEpisodeListContextMenuEVT(self, event: wx.MenuEvent):
        match event.GetId():
            case ID.EPISODE_LIST_VIEW_COVER_MENU:
                item_data = self.episode_list.GetItemData(self.episode_list.GetSelection())

                if item_data.cover_url:
                    Cover.view_cover(self, item_data.cover_url)
                
            case ID.EPISODE_LIST_COPY_TITLE_MENU:
                ClipBoard.Write(self.utils.get_episode_title())

            case ID.EPISODE_LIST_COPY_URL_MENU:
                self.utils.copy_from_menu = True

                item_data = self.episode_list.GetItemData(self.episode_list.GetSelection())

                ClipBoard.Write(item_data.link)

            case ID.EPISODE_LIST_EDIT_TITLE_MENU:
                item = self.episode_list.GetSelection()

                if (title := Window.edit_title_dialog(self, self.utils.get_episode_title())):
                    self.utils.set_episode_title(item, title)

            case ID.EPISODE_LIST_CHECK_MENU:
                self.episode_list.CheckCurrentItem()

            case ID.EPISODE_LIST_COLLAPSE_MENU:
                self.episode_list.CollapseCurrentItem()

    def onShowGraphWindowEVT(self):
        WebPage.show_webpage(self, "graph.html")

    def onShowDetailInfoDialogEVT(self):
        Window.detail_dialog(self, self.parser.parse_type)

    def onShowDownloadOptionDialogEVT(self, event: wx.CommandEvent):
        return Window.download_option_dialog(self)
    
    def show_episode_list(self, from_menu: bool = True):
        if from_menu:
            self.parser.parse_episode()

        self.episode_list.show_episode_list()

        if Config.Misc.auto_check_episode_item or self.episode_list.count == 1:
            self.episode_list.CheckAllItems()

        self.utils.update_checked_item_count(self.episode_list.GetCheckedItemCount())

    def set_window_params(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows | Platform.macOS:
                self.SetSize(self.FromDIP((800, 450)))

            case Platform.Linux:
                self.SetSize(self.FromDIP((900, 550)))
        
        self.CenterOnParent()

        if Config.Basic.remember_window_status:
            if Config.Basic.window_maximized:
                self.Maximize()
            else:
                if Config.Basic.window_size:
                    self.SetSize(Config.Basic.window_size)
                
                if Config.Basic.window_pos:
                    self.SetPosition(Config.Basic.window_pos)

    def get_sys_settings(self):
        Config.Sys.dark_mode = False if Platform(Config.Sys.platform) == Platform.Windows else wx.SystemSettings.GetAppearance().IsDark()
        Config.Sys.dpi_scale_factor = self.GetDPIScaleFactor()
        Config.Sys.default_font = self.GetFont().GetFaceName()

        for key in ["danmaku", "subtitle"]:
            if Config.Basic.ass_style.get(key).get("font_name") == "default":
                Config.Basic.ass_style[key]["font_name"] = Config.Sys.default_font

    @property
    def stream_type(self):
        return self.parser.stream_type

    @property
    def video_quality_id(self):
        return self.parser.video_quality_id
    
    @property
    def video_quality_data_dict(self):
        return self.parser.video_quality_data_dict