import wx
import webbrowser

from utils.config import Config
from utils.tool_v2 import UniversalTool
from utils.common.thread import Thread
from utils.common.icon_v2 import IconManager, IconType
from utils.common.update import Update
from utils.common.enums import ParseStatus, ParseType, StatusCode, EpisodeDisplayType
from utils.common.data_type import ParseCallback
from utils.common.exception import GlobalException

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.live import LiveInfo, LiveParser
from utils.parse.b23 import B23Parser
from utils.parse.activity import ActivityInfo, ActivityParser

from gui.window.download_v3 import DownloadManagerWindow
from gui.window.settings import SettingWindow
from gui.window.debug import DebugWindow

from gui.dialog.about import AboutWindow
from gui.dialog.changelog import ChangeLogDialog
from gui.dialog.update import UpdateWindow
from gui.dialog.converter import ConverterWindow
from gui.dialog.cut_clip import CutClipDialog

from gui.component.frame import Frame
from gui.component.panel import Panel
from gui.component.search_ctrl import SearchCtrl
from gui.component.tree_list import TreeListCtrl
from gui.component.button import Button
from gui.component.bitmap_button import BitmapButton

class MainWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, Config.APP.name)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.init_id()

        icon_mgr = IconManager(self)

        self.panel = Panel(self)

        url_lab = wx.StaticText(self.panel, -1, "链接")
        self.url_box = SearchCtrl(self.panel, "在此处粘贴链接进行解析", search = False, clear = True)
        self.get_btn = wx.Button(self.panel, -1, "Get")

        url_hbox = wx.BoxSizer(wx.HORIZONTAL)
        url_hbox.Add(url_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        url_hbox.Add(self.url_box, 1, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.EXPAND, 10)
        url_hbox.Add(self.get_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)

        self.processing_icon = wx.StaticBitmap(self.panel, -1, icon_mgr.get_icon_bitmap(IconType.LOADING_ICON), size = self.FromDIP((24, 24)))
        self.processing_icon.Hide()
        self.type_lab = wx.StaticText(self.panel, -1, "")
        self.detail_icon = wx.StaticBitmap(self.panel, -1, icon_mgr.get_icon_bitmap(IconType.INFO_ICON), size = self.FromDIP((24, 24)))
        self.detail_icon.Hide()
        self.video_quality_lab = wx.StaticText(self.panel, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self.panel, -1)
        self.episode_option_btn = BitmapButton(self.panel, icon_mgr.get_icon_bitmap(IconType.LIST_ICON))
        self.episode_option_btn.Enable(False)
        self.download_option_btn = BitmapButton(self.panel, icon_mgr.get_icon_bitmap(IconType.SETTING_ICON))
        self.download_option_btn.Enable(False)

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.Add(self.processing_icon, 0, wx.ALL & (~wx.RIGHT), 10)
        info_hbox.Add(self.type_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        info_hbox.Add(self.detail_icon, 0, wx.ALL & (~wx.LEFT), 10)
        info_hbox.AddStretchSpacer()
        info_hbox.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        info_hbox.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT), 10)
        info_hbox.Add(self.episode_option_btn, 0, wx.ALL & (~wx.LEFT), 10)
        info_hbox.Add(self.download_option_btn, 0, wx.ALL & (~wx.LEFT), 10)

        self.episode_list = TreeListCtrl(self.panel, self.update_checked_count)

        self.download_mgr_btn = Button(self.panel, "下载管理", size = self.get_scaled_size((100, 30)))
        self.download_btn = Button(self.panel, "开始下载", size = self.get_scaled_size((100, 30)))
        self.download_btn.Enable(False)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.download_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(url_hbox, 0, wx.EXPAND)
        vbox.Add(info_hbox, 0, wx.EXPAND)
        vbox.Add(self.episode_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

        self.Fit()

        self.init_menubar()

    def init_id(self):
        self.ID_LOGIN_MENU = wx.NewIdRef()
        self.ID_LOGOUT_MENU = wx.NewIdRef()
        self.ID_DEBUG_MENU = wx.NewIdRef()
        self.ID_CONVERTER_MENU = wx.NewIdRef()
        self.ID_CUT_CLIP_MENU = wx.NewIdRef()
        self.ID_SETTINGS_MENU = wx.NewIdRef()

        self.ID_CHECK_UPDATE_MENU = wx.NewIdRef()
        self.ID_CHANGELOG_MENU = wx.NewIdRef()
        self.ID_HELP_MENU = wx.NewIdRef()
        self.ID_FEEDBACK_MENU = wx.NewIdRef()
        self.ID_ABOUT_MENU = wx.NewIdRef()

        self.ID_EPISODE_SINGLE_MENU = wx.NewIdRef()
        self.ID_EPISODE_IN_SECTION_MENU = wx.NewIdRef()
        self.ID_EPISODE_ALL_SECTIONS_MENU = wx.NewIdRef()
        self.ID_EPISODE_FULL_NAME_MENU = wx.NewIdRef()

    def init_menubar(self):
        menu_bar = wx.MenuBar()

        tool_manu = wx.Menu()
        help_menu = wx.Menu()

        if Config.User.login:
            tool_manu.Append(self.ID_LOGOUT_MENU, "注销(&L)")
        else:
            tool_manu.Append(self.ID_LOGIN_MENU, "登录(&L)")

        tool_manu.AppendSeparator()

        if Config.Misc.enable_debug:
            tool_manu.Append(self.ID_DEBUG_MENU, "调试(&D)")

        tool_manu.Append(self.ID_CONVERTER_MENU, "格式转换(&F)")
        tool_manu.Append(self.ID_CUT_CLIP_MENU, "截取片段(&I)")
        tool_manu.AppendSeparator()
        tool_manu.Append(self.ID_SETTINGS_MENU, "设置(&S)")

        help_menu.Append(self.ID_CHECK_UPDATE_MENU, "检查更新(&U)")
        help_menu.Append(self.ID_CHANGELOG_MENU, "更新日志(&P)")
        help_menu.AppendSeparator()
        help_menu.Append(self.ID_HELP_MENU, "使用帮助(&C)")
        help_menu.Append(self.ID_FEEDBACK_MENU, "意见反馈(&B)")
        help_menu.Append(self.ID_ABOUT_MENU, "关于(&A)")

        menu_bar.Append(tool_manu, "工具(&T)")
        menu_bar.Append(help_menu, "帮助(&H)")

        self.SetMenuBar(menu_bar)

    def Bind_EVT(self):
        self.Bind(wx.EVT_MENU, self.onMenuEVT)

        self.url_box.Bind(wx.EVT_SEARCH, self.onGetEVT)
        self.get_btn.Bind(wx.EVT_BUTTON, self.onGetEVT)

        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadMgrEVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadMgrEVT)

        self.episode_option_btn.Bind(wx.EVT_BUTTON, self.onShowEpisodeOptionMenuEVT)
        self.download_option_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadOptionDlgEVT)

    def init_utils(self):
        self.download_window = DownloadManagerWindow(self)

    def onMenuEVT(self, event):
        def show_episode_list():
            match self.current_parse_type:
                case ParseType.Video:
                    self.video_parser.parse_episodes()

                case ParseType.Bangumi:
                    self.bangumi_parser.parse_episodes()

                case ParseType.Cheese:
                    self.cheese_parser.parse_episodes()

            self.show_episode_list()

        match event.GetId():
            case self.ID_LOGIN_MENU:
                pass

            case self.ID_LOGOUT_MENU:
                pass

            case self.ID_DEBUG_MENU:
                DebugWindow(self).Show()

            case self.ID_CONVERTER_MENU:
                ConverterWindow(self).ShowModal()

            case self.ID_CUT_CLIP_MENU:
                CutClipDialog(self).ShowModal()

            case self.ID_SETTINGS_MENU:
                SettingWindow(self).ShowModal()

            case self.ID_CHECK_UPDATE_MENU:
                def check_update_thread():
                    Update.get_update()

                    if Config.Temp.update_json:
                        if Config.Temp.update_json["version_code"] > Config.APP.version_code:
                            wx.CallAfter(UpdateWindow(self).ShowModal)
                        else:
                            wx.CallAfter(wx.MessageDialog(self, "当前没有可用的更新", "检查更新", wx.ICON_INFORMATION).ShowModal)
                    else:
                        wx.CallAfter(wx.MessageDialog(self, "检查更新失败\n\n当前无法检查更新，请稍候再试", "检查更新", wx.ICON_ERROR).ShowModal)

                Thread(target = check_update_thread).start()

            case self.ID_CHANGELOG_MENU:
                def changelog_thread():
                    Update.get_changelog()

                    if Config.Temp.changelog:
                        wx.CallAfter(ChangeLogDialog(self).ShowModal)
                    else:
                        wx.CallAfter(wx.MessageDialog(self, "获取更新日志失败\n\n当前无法获取更新日志，请稍候再试", "获取更新日志", wx.ICON_ERROR).ShowModal)

                Thread(target = changelog_thread).start()

            case self.ID_HELP_MENU:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/use/basic.html")

            case self.ID_FEEDBACK_MENU:
                webbrowser.open("https://github.com/ScottSloan/Bili23-Downloader/issues")

            case self.ID_ABOUT_MENU:
                AboutWindow(self).ShowModal()

            case self.ID_EPISODE_SINGLE_MENU:
                Config.Misc.episode_display_mode = EpisodeDisplayType.Single.value

                show_episode_list()

            case self.ID_EPISODE_IN_SECTION_MENU:
                Config.Misc.episode_display_mode = EpisodeDisplayType.In_Section.value

                show_episode_list()

            case self.ID_EPISODE_ALL_SECTIONS_MENU:
                Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

                show_episode_list()

            case self.ID_EPISODE_FULL_NAME_MENU:
                Config.Misc.show_episode_full_name = not Config.Misc.show_episode_full_name

                show_episode_list()

    def onGetEVT(self, event):
        url = self.url_box.GetValue()

        if not url:
            wx.MessageDialog(self, "解析失败\n\n链接不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        self.set_parse_status(ParseStatus.Parsing.value)
        
        Thread(target = self.parse_url_thread, args = (url, )).start()

    def onOpenDownloadMgrEVT(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()
            self.download_window.CenterOnParent()
        
        elif self.download_window.IsIconized():
            self.download_window.Iconize(False)
        
        self.download_window.SetFocus()
        self.download_window.downloading_page_btn.onClickEVT(event)

    def onDownloadEVT(self, event):
        pass

    def onShowEpisodeOptionMenuEVT(self, event):
        menu = wx.Menu()

        single_menuitem = wx.MenuItem(menu, self.ID_EPISODE_SINGLE_MENU, "显示单个视频", kind = wx.ITEM_RADIO)
        in_section_menuitem = wx.MenuItem(menu, self.ID_EPISODE_IN_SECTION_MENU, "显示视频所在的列表", kind = wx.ITEM_RADIO)
        all_section_menuitem = wx.MenuItem(menu, self.ID_EPISODE_ALL_SECTIONS_MENU, "显示全部相关视频", kind = wx.ITEM_RADIO)
        show_episode_full_name = wx.MenuItem(menu, self.ID_EPISODE_FULL_NAME_MENU, "显示完整剧集名称", kind = wx.ITEM_CHECK)

        menu.Append(wx.NewIdRef(), "剧集列表显示设置")
        menu.AppendSeparator()
        menu.Append(single_menuitem)
        menu.Append(in_section_menuitem)
        menu.Append(all_section_menuitem)
        menu.AppendSeparator()
        menu.Append(show_episode_full_name)

        match EpisodeDisplayType(Config.Misc.episode_display_mode):
            case EpisodeDisplayType.Single:
                single_menuitem.Check(True)

            case EpisodeDisplayType.In_Section:
                in_section_menuitem.Check(True)

            case EpisodeDisplayType.All:
                all_section_menuitem.Check(True)

        show_episode_full_name.Check(Config.Misc.show_episode_full_name)

        self.PopupMenu(menu)

    def onShowDownloadOptionDlgEVT(self, event):
        pass

    def parse_url_thread(self, url: str):
        def worker():
            self.set_parse_status(ParseStatus.Finish.value)

            self.show_episode_list()

        self.current_parse_type = None
        
        match UniversalTool.re_find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival", url):
            case "cheese":
                self.current_parse_type = ParseType.Cheese
                self.cheese_parser = CheeseParser(self.parse_callback)

                return_code = self.cheese_parser.parse_url(url)

            case "av" | "BV":
                self.current_parse_type = ParseType.Video
                self.video_parser = VideoParser(self.parse_callback)

                return_code = self.video_parser.parse_url(url)

            case "ep" | "ss" | "md":
                self.current_parse_type = ParseType.Bangumi
                self.bangumi_parser = BangumiParser(self.parse_callback)

                return_code = self.bangumi_parser.parse_url(url)

            case "live":
                self.current_parse_type = ParseType.Live
                self.live_parser = LiveParser(self.parse_callback)

                return_code = self.live_parser.parse_url(url)

            case "b23.tv" | "bili2233.cn":
                self.b23_parser = B23Parser(self.parse_callback)

                return_code = self.b23_parser.parse_url(url)

            case "blackboard" | "festival":
                self.activity_parser = ActivityParser(self.parse_callback)

                return_code = self.activity_parser.parse_url(url)
            
            case _:
                raise GlobalException(code = StatusCode.URL.value, callback = self.onErrorCallback)
        
        if return_code == StatusCode.Success.value:
            wx.CallAfter(worker)
    
    def show_episode_list(self):
        self.episode_list.set_list()
        self.update_checked_count()
    
    def update_checked_count(self, count: int = 0):
        if count:
            label = f"(共 {self.episode_list.count} 个，已选择 {count} 个)"
        else:
            label = f"(共 {self.episode_list.count} 个)"

        match self.current_parse_type:
            case ParseType.Video:
                type = "投稿视频"

            case ParseType.Bangumi:
                type = BangumiInfo.type_name

            case ParseType.Live:
                type = "直播"

            case ParseType.Cheese:
                type = "课程"
        
        self.type_lab.SetLabel(f"{type} {label}")

        self.panel.Layout()

    def onErrorCallback(self):
        self.set_parse_status(ParseStatus.Error)

    def onRedirectCallback(self):
        pass

    def set_parse_status(self, status: int):
        def set_enable_status(enable: bool):
            self.url_box.Enable(enable)
            self.get_btn.Enable(enable)
            self.episode_list.Enable(enable)
            self.download_btn.Enable(enable)
            self.episode_option_btn.Enable(enable)
            self.download_option_btn.Enable(enable)
        
        def set_download_btn_label():
            match self.current_parse_type:
                case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                    self.episode_option_btn.Enable(True)
                    self.download_option_btn.Enable(True)
                    self.download_btn.SetLabel("开始下载")

                case ParseType.Live:
                    self.episode_option_btn.Enable(False)
                    self.download_option_btn.Enable(False)
                    self.download_btn.SetLabel("直播录制")

        match ParseStatus(status):
            
            case ParseStatus.Parsing:
                self.processing_icon.Show(True)

                self.type_lab.SetLabel("正在解析中")

                self.detail_icon.Hide()

                self.SetCursor(wx.Cursor(wx.CURSOR_WAIT))

                set_enable_status(False)
            
            case ParseStatus.Finish:
                self.processing_icon.Hide()

                self.type_lab.SetLabel("")

                self.detail_icon.Show()

                self.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))

                set_enable_status(True)
                set_download_btn_label()

            case ParseStatus.Error:
                self.processing_icon.Hide()

                self.type_lab.SetLabel("")

                self.detail_icon.Hide()

                self.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))

                self.url_box.Enable(True)
                self.get_btn.Enable(True)
                self.episode_list.Enable(True)

        self.panel.Layout()
    
    @property
    def parse_callback(self):
        callback = ParseCallback()
        callback.onError = self.onErrorCallback
        callback.onRedirect = self.onRedirectCallback

        return callback