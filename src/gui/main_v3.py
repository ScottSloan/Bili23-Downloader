import wx
import webbrowser

from utils.config import Config
from utils.auth.login import QRLogin
from utils.common.regex import Regex
from utils.common.enums import ParseType, Platform, EpisodeDisplayType, ProcessingType, StatusCode
from utils.common.data_type import ParseCallback
from utils.common.icon_v4 import Icon, IconID
from utils.common.thread import Thread
from utils.common.update import Update
from utils.common.exception import GlobalException, GlobalExceptionInfo

from utils.module.face import Face

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.live import LiveParser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.b23 import B23Parser
from utils.parse.activity import ActivityParser
from utils.parse.preview import Preview

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel

from gui.dialog.about import AboutWindow
from gui.dialog.processing import ProcessingWindow
from gui.dialog.misc.update import UpdateDialog
from gui.dialog.misc.changelog import ChangeLogDialog
from gui.dialog.error import ErrorInfoDialog

from gui.window.debug import DebugWindow
from gui.window.format_factory import FormatFactoryWindow
from gui.window.settings import SettingWindow
from gui.window.download_v3 import DownloadManagerWindow
from gui.window.login import LoginWindow

from gui.component.text_ctrl.search_ctrl import SearchCtrl
from gui.component.button.flat_button import FlatButton
from gui.component.button.bitmap_button import BitmapButton
from gui.component.button.button import Button
from gui.component.info_bar import InfoBar
from gui.component.taskbar_icon import TaskBarIcon
from gui.component.tree_list_v2 import TreeListCtrl

class Parser:
    def __init__(self, parent: wx.Window):
        self.main_window: MainWindow = parent

    def init_utils(self):
        self.parse_type: ParseType = None

    def parse_url(self, url: str):
        match Regex.find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival", url):
            case "cheese":
                self.set_parse_type(ParseType.Cheese)

                self.parser = CheeseParser(self.parser_callback)

            case "av" | "BV":
                self.set_parse_type(ParseType.Video)

                self.parser = VideoParser(self.parser_callback)

            case "ep" | "ss" | "md":
                self.set_parse_type(ParseType.Bangumi)

                self.parser = BangumiParser(self.parser_callback)

            case "live":
                self.set_parse_type(ParseType.Live)

                self.parser = LiveParser(self.parser_callback)

            case "b23.tv" | "bili2233.cn":
                self.parser = B23Parser(self.parser_callback)

            case "blackboard" | "festival":
                self.parser = ActivityParser(self.parser_callback)

            case _:
                raise GlobalException(code = StatusCode.URL.value, callback = self.onError)
        
        rtnVal = self.parser.parse_url(url)

        if StatusCode(rtnVal) == StatusCode.Success:
            wx.CallAfter(self.parse_success)
    
    def parse_success(self):
        self.main_window.show_episode_list()

        self.set_video_quality_id()

        self.set_stream_type()

        self.parse_type_str = self.get_parse_type_str()

    def set_video_quality_id(self):
        data = Preview.get_download_json(self.parse_type)

        self.video_quality_id_list, self.video_quality_desc_list = Preview.get_video_quality_id_desc_list(data)

        self.video_quality_id = Config.Download.video_quality_id if Config.Download.video_quality_id in self.video_quality_id_list else self.video_quality_id_list[1]

    def set_stream_type(self):
        match self.parse_type:
            case ParseType.Video:
                self.stream_type = VideoInfo.stream_type
            
            case ParseType.Bangumi:
                self.stream_type = BangumiInfo.stream_type
            
            case ParseType.Cheese:
                self.stream_type = CheeseInfo.stream_type

    def set_parse_type(self, parse_type: ParseType):
        self.parse_type = parse_type

    def get_parse_type_str(self):
        match self.parse_type:
            case ParseType.Video:
                if VideoInfo.is_interactive:
                    return "互动视频"
                else:
                    return "投稿视频"

            case ParseType.Bangumi:
                return BangumiInfo.type_name
            
            case ParseType.Live:
                return "直播"
            
            case ParseType.Cheese:
                return "课程"

    def parse_episode(self):
        self.parser.parse_episodes()

    def onError(self):
        def worker():
            info = GlobalExceptionInfo.info.copy()

            dlg = wx.MessageDialog(self.main_window, f"解析失败\n\n错误码：{info.get('code')}\n描述：{info.get('message')}", "错误", wx.ICON_ERROR | wx.YES_NO)
            dlg.SetYesNoLabels("详细信息", "确定")

            if dlg.ShowModal() == wx.ID_YES:
                dlg = ErrorInfoDialog(self.main_window, info)
                dlg.ShowModal()

        wx.CallAfter(worker)

    def onBangumi(self, url: str):
        Thread(target = self.parse_url, args = (url, )).start()

    def onInteractVideo(self):
        def worker():
            self.main_window.processing_window.SetType(ProcessingType.Interact)

        wx.CallAfter(worker)

    @property
    def parser_callback(self):
        class Callback(ParseCallback):
            @staticmethod
            def onError():
                self.onError()
            
            @staticmethod
            def onBangumi(url: str):
                self.onBangumi(url)

            @staticmethod
            def onInteractVideo():
                self.onInteractVideo()

            @staticmethod
            def onUpdateInteractVideo(title: str):
                self.main_window.processing_window.onUpdateNode(title)

        return Callback

class Utils:
    def __init__(self, parent: wx.Window):
        self.main_window: MainWindow = parent

    def check_url(self, url: str):
        if not url:
            self.show_message_dialog("解析失败\n\n链接不能为空", "警告", wx.ICON_WARNING)
            return True

    def check_update(self, info_bar: bool = False):
        def show_update_dialog():
            window = UpdateDialog(self.main_window, info)
            window.ShowModal()

        info = Update.get_update_json()

        if info:
            if info["version_code"] > Config.APP.version_code:
                wx.CallAfter(show_update_dialog)
            else:
                self.show_message_dialog("当前没有可用的更新。", "检查更新", wx.ICON_INFORMATION)
        else:
            self.show_message_dialog("检查更新失败\n\n当前无法检查更新，请稍候再试。", "检查更新", wx.ICON_ERROR)

    def get_changelog(self):
        def show_changelog_dialog():
            dlg = ChangeLogDialog(self.main_window)
            dlg.ShowModal()

        info = Update.get_changelog()

        if info:
            wx.CallAfter(show_changelog_dialog)
        else:
            self.show_message_dialog("获取更新日志失败\n\n当前无法获取更新日志，请稍候再试", "获取更新日志", wx.ICON_ERROR)

    def user_logout(self):
        QRLogin().logout()

        self.show_user_info()

    def user_refresh(self):
        QRLogin().refresh

        self.show_user_info()

    def show_user_info(self):
        def show_user_face():
            self.main_window.face_icon.Show()
            self.main_window.face_icon.SetBitmap(Face.crop_round_face_bmp(image))
            self.main_window.uname_lab.SetLabel(Config.User.username)

            self.main_window.panel.Layout()

        def hide_user_info():
            self.main_window.face_icon.Hide()
            self.main_window.uname_lab.Hide()

            self.main_window.panel.Layout()

        def not_login():
            self.main_window.uname_lab.SetLabel("未登录")
            self.main_window.face_icon.Hide()

            self.main_window.panel.Layout()

        if Config.Misc.show_user_info:
            if Config.User.login:
                image = Face.get_scaled_face(self.main_window.FromDIP((32, 32)))

                worker = show_user_face
            else:
                worker = not_login
        else:
            worker = hide_user_info

        wx.CallAfter(worker)

    def show_message_dialog(self, message: str, caption: str, style: int):
        def worker():
            dlg = wx.MessageDialog(self.main_window, message, caption, style)
            dlg.ShowModal()

        wx.CallAfter(worker)

class MainWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, Config.APP.name)

        self.set_window_params()

        self.get_sys_settings()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.init_id()

        self.panel = Panel(self)

        self.infobar = InfoBar(self.panel)

        url_lab = wx.StaticText(self.panel, -1, "链接")
        self.url_box = SearchCtrl(self.panel, "在此处粘贴链接进行解析", search = False, clear = True)
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
        info_hbox.Add(self.episode_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.download_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.episode_list = TreeListCtrl(self.panel, self)

        self.face_icon = wx.StaticBitmap(self.panel, -1, size = self.FromDIP((32, 32)))
        self.face_icon.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.face_icon.Hide()
        self.uname_lab = wx.StaticText(self.panel, -1, "未登录", style = wx.ELLIPSIZE_END)
        self.uname_lab.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.download_mgr_btn = Button(self.panel, "下载管理", size = self.get_scaled_size((100, 30)))
        self.download_btn = Button(self.panel, "开始下载", size = self.get_scaled_size((100, 30)))
        self.download_btn.Enable(False)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.face_icon, 0, wx.ALL & (~wx.RIGHT), self.FromDIP(6))
        bottom_hbox.Add(self.uname_lab, 1, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.download_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.infobar, 0, wx.EXPAND)
        vbox.Add(url_hbox, 0, wx.EXPAND)
        vbox.Add(info_hbox, 0, wx.EXPAND)
        vbox.Add(self.episode_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)

        self.init_menubar()

        self.clipboard_timer = wx.Timer(self, -1)

        self.taskbar_icon = TaskBarIcon(self)

    def init_id(self):
        self.ID_REFRESH_MENU = wx.NewIdRef()
        self.ID_LOGIN_MENU = wx.NewIdRef()
        self.ID_LOGOUT_MENU = wx.NewIdRef()
        self.ID_DEBUG_MENU = wx.NewIdRef()
        self.ID_CONVERTER_MENU = wx.NewIdRef()
        self.ID_FORMAT_FACTORY_MENU = wx.NewIdRef()
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

        tool_manu.Append(self.ID_FORMAT_FACTORY_MENU, "视频工具箱(&F)")
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

        self.url_box.Bind(wx.EVT_SEARCH, self.onParseEVT)
        self.get_btn.Bind(wx.EVT_BUTTON, self.onParseEVT)

        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadWindowEVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.onDownloadEVT)

    def init_utils(self):
        self.utils = Utils(self)
        self.parser = Parser(self)

        self.processing_window = ProcessingWindow(self)
        self.download_window = DownloadManagerWindow(self)

    def onMenuEVT(self, event):
        match event.GetId():
            case self.ID_LOGIN_MENU:
                window = LoginWindow()
                window.Show()

            case self.ID_LOGOUT_MENU:
                dlg = wx.MessageDialog(self, '退出登录\n\n是否要退出登录？', "警告", wx.ICON_WARNING | wx.YES_NO)

                if dlg.ShowModal() == wx.ID_YES:
                    self.utils.user_logout()

            case self.ID_REFRESH_MENU:
                Thread(target = self.utils.user_refresh).start()

            case self.ID_DEBUG_MENU:
                window = DebugWindow(self)
                window.Show()

            case self.ID_FORMAT_FACTORY_MENU:
                window = FormatFactoryWindow(self)
                window.Show()

            case self.ID_SETTINGS_MENU:
                window = SettingWindow(self)
                window.ShowModal()

            case self.ID_CHECK_UPDATE_MENU:
                Thread(target = self.utils.check_update).start()

            case self.ID_CHANGELOG_MENU:
                Thread(target = self.utils.get_changelog).start()

            case self.ID_HELP_MENU:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/use/basic.html")

            case self.ID_FEEDBACK_MENU:
                webbrowser.open("https://github.com/ScottSloan/Bili23-Downloader/issues")

            case self.ID_ABOUT_MENU:
                dlg = AboutWindow(self)
                dlg.ShowModal()

            case self.ID_EPISODE_SINGLE_MENU:
                Config.Misc.episode_display_mode = EpisodeDisplayType.Single.value

                self.show_episode_list()

            case self.ID_EPISODE_IN_SECTION_MENU:
                Config.Misc.episode_display_mode = EpisodeDisplayType.In_Section.value

                self.show_episode_list()

            case self.ID_EPISODE_ALL_SECTIONS_MENU:
                Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

                self.show_episode_list()

            case self.ID_EPISODE_FULL_NAME_MENU:
                Config.Misc.show_episode_full_name = not Config.Misc.show_episode_full_name

                self.show_episode_list()

    def onCloseEVT(self, event):
        pass

    def onShowDownloadWindowEVT(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()
        
        elif self.download_window.IsIconized():
            if Config.Basic.auto_show_download_window:
                self.download_window.Iconize(False)
        
        if Config.Basic.auto_show_download_window:
            self.download_window.downloading_page_btn.onClickEVT(event)
            self.download_window.Raise()

    def onDownloadEVT(self, event):
        pass

    def onParseEVT(self, event):
        url = self.url_box.GetValue()

        if self.utils.check_url(url):
            return

        self.episode_list.init_episode_list()

        Thread(target = self.parser.parse_url, args = (url, )).start()

    def onUpdateCheckedItemCount(self, count: int):
        label = f"(共 {self.episode_list.count} 个{f"，已选择 {count} 个)" if count else ")"}"

        self.type_lab.SetLabel(f"{self.parser.parse_type_str} {label}")

        self.panel.Layout()

    def show_episode_list(self):
        self.parser.parse_episode()

        self.episode_list.show_episode_list()

        if Config.Misc.auto_check_episode_item or self.episode_list.count == 1:
            self.episode_list.CheckAllItems()

        self.onUpdateCheckedItemCount(self.episode_list.GetCheckedItemCount())

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

        for key in ["danmaku", "subtitle"]:
            if Config.Basic.ass_style.get(key).get("font_name") == "default":
                Config.Basic.ass_style[key]["font_name"] = self.GetFont().GetFaceName()

    def show_processing_window(self, type: ProcessingType):
        wx.CallAfter(self.processing_window.ShowModal, type)

    def hide_processing_window(self):
        wx.CallAfter(self.processing_window.Close)

    @property
    def stream_type(self):
        return self.parser.stream_type

    @property
    def video_quality_id(self):
        return self.parser.video_quality_id