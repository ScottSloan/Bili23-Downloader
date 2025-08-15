import wx
import asyncio
import webbrowser

from utils.config import Config

from utils.common.enums import Platform, EpisodeDisplayType, ProcessingType, ExitOption
from utils.common.thread import Thread
from utils.common.exception import GlobalException

from utils.module.pic.cover import Cover
from utils.module.ffmpeg_v2 import FFmpeg

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel

from gui.id import ID

from gui.dialog.misc.processing import ProcessingWindow

from gui.window.main.parser import Parser
from gui.window.main.utils import Utils, Window, TheClipBoard, Async
from gui.window.main.top_box import TopBox
from gui.window.main.bottom_box import BottomBox

from gui.window.download.download_v4 import DownloadManagerWindow
from gui.window.live_recording import LiveRecordingWindow

from gui.component.misc.taskbar_icon import TaskBarIcon
from gui.component.tree_list_v2 import TreeListCtrl

class MainWindow(Frame):
    def __init__(self, parent):
        self.url = None

        self.utils = Utils(self)

        Frame.__init__(self, parent, Config.APP.name, name = "main")

        self.set_window_params()

        self.get_sys_settings()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.panel = Panel(self)

        self.top_box = TopBox(self.panel)

        self.episode_list = TreeListCtrl(self.panel)

        self.bottom_box = BottomBox(self.panel)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.top_box, 0, wx.EXPAND)
        vbox.Add(self.episode_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.bottom_box, 0, wx.EXPAND)

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
        
        self.top_box.get_btn.Bind(wx.EVT_BUTTON, self.onParseEVT)

        self.bottom_box.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadWindowEVT)
        self.bottom_box.download_btn.Bind(wx.EVT_BUTTON, self.onDownloadEVT)

        self.episode_list.Bind(wx.EVT_MENU, self.onEpisodeListContextMenuEVT)

        self.Bind(wx.EVT_TIMER, TheClipBoard.read, self.clipboard_timer)

    def init_utils(self):
        def worker():
            FFmpeg.Env.detect()

            asyncio.run(Async.async_worker())

            if Config.Basic.is_new_user:
                Window.welcome_dialog(self)

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
                self.top_box.set_episode_display_mode(EpisodeDisplayType.Single)

            case ID.EPISODE_IN_SECTION_MENU:
                self.top_box.set_episode_display_mode(EpisodeDisplayType.In_Section)

            case ID.EPISODE_ALL_SECTIONS_MENU:
                self.top_box.set_episode_display_mode(EpisodeDisplayType.All)
                
            case ID.EPISODE_FULL_NAME_MENU:
                self.top_box.set_episode_full_name()

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
            Window.processing_window(show = False)
            
            self.onShowDownloadWindowEVT()

        try:
            if self.episode_list.check_download_items():
                return
            
            if Config.Basic.auto_popup_option_dialog:
                if self.top_box.onShowDownloadOptionDialogEVT(event) != wx.ID_OK:
                    return

            self.episode_list.GetAllCheckedItem()

            Thread(target = self.download_window.add_to_download_list, args = (self.episode_list.download_task_info_list, after_show_items_callback, True, True)).start()

            Window.processing_window(show = True)
        
        except Exception as e:
            raise GlobalException(callback = self.parser.onError) from e
        
    def onParseEVT(self, event):
        url = self.top_box.url_box.GetValue()

        if self.top_box.check_url():
            return

        self.episode_list.init_episode_list()

        Thread(target = self.parser.parse_url, args = (url, )).start()

        self.url = url

    def onEpisodeListContextMenuEVT(self, event: wx.MenuEvent):
        match event.GetId():
            case ID.EPISODE_LIST_VIEW_COVER_MENU:
                item_data = self.episode_list.GetItemData(self.episode_list.GetSelection())

                if item_data.cover_url:
                    Cover.view_cover(self, item_data.cover_url)
                
            case ID.EPISODE_LIST_COPY_TITLE_MENU:
                TheClipBoard.write(self.episode_list.GetItemTitle())

            case ID.EPISODE_LIST_COPY_URL_MENU:
                self.utils.copy_from_menu = True

                item_data = self.episode_list.GetItemData(self.episode_list.GetSelection())

                TheClipBoard.write(item_data.link)

            case ID.EPISODE_LIST_EDIT_TITLE_MENU:
                item = self.episode_list.GetSelection()

                if (title := Window.edit_title_dialog(self, self.episode_list.GetItemTitle())):
                    self.episode_list.SetItemTitle(item, title)

            case ID.EPISODE_LIST_CHECK_MENU:
                self.episode_list.CheckCurrentItem()

            case ID.EPISODE_LIST_COLLAPSE_MENU:
                self.episode_list.CollapseCurrentItem()

    def show_episode_list(self, from_menu: bool = True):
        if from_menu:
            self.parser.parse_episode()

        self.episode_list.show_episode_list()

        if Config.Misc.auto_check_episode_item or self.episode_list.count == 1:
            self.episode_list.CheckAllItems()

        self.top_box.update_checked_item_count(self.episode_list.GetCheckedItemCount())

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