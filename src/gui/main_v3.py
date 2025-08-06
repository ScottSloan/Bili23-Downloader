import wx
import asyncio
import webbrowser

from utils.config import Config
from utils.auth.login_v2 import Login

from utils.common.regex import Regex
from utils.common.enums import ParseType, Platform, EpisodeDisplayType, ProcessingType, StatusCode, ExitOption, ParseStatus, LiveStatus
from utils.common.model.data_type import ParseCallback, Callback
from utils.common.style.icon_v4 import Icon, IconID
from utils.common.thread import Thread
from utils.common.update import Update
from utils.common.exception import GlobalException, GlobalExceptionInfo

from utils.module.pic.face import Face
from utils.module.clipboard import ClipBoard
from utils.module.pic.cover import Cover
from utils.module.ffmpeg_v2 import FFmpeg
from utils.module.web.page import WebPage

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.live import LiveInfo, LiveParser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.b23 import B23Parser
from utils.parse.activity import ActivityParser
from utils.parse.preview import VideoPreview
from utils.parse.popular import PopularParser
from utils.parse.list import ListParser

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel

from gui.id import ID

from gui.dialog.misc.about import AboutWindow
from gui.dialog.misc.processing import ProcessingWindow
from gui.dialog.misc.update import UpdateDialog
from gui.dialog.misc.changelog import ChangeLogDialog
from gui.dialog.error import ErrorInfoDialog
from gui.dialog.setting.edit_title import EditTitleDialog
from gui.dialog.detail import DetailDialog
from gui.dialog.download_option_v3 import DownloadOptionDialog
from gui.dialog.login.login_v2 import LoginDialog

from gui.window.debug import DebugWindow
from gui.window.format_factory import FormatFactoryWindow
from gui.window.settings.settings_v2 import SettingWindow
from gui.window.download.download_v4 import DownloadManagerWindow
from gui.window.live_recording import LiveRecordingWindow

from gui.component.text_ctrl.search_ctrl import SearchCtrl
from gui.component.button.flat_button import FlatButton
from gui.component.button.bitmap_button import BitmapButton
from gui.component.button.button import Button
from gui.component.misc.info_bar import InfoBar
from gui.component.misc.taskbar_icon import TaskBarIcon
from gui.component.tree_list_v2 import TreeListCtrl

from gui.component.menu.episode_option import EpisodeOptionMenu
from gui.component.menu.user import UserMenu

class Parser:
    def __init__(self, parent: wx.Window):
        self.main_window: MainWindow = parent
        self.url = None

    def init_utils(self):
        self.parse_type: ParseType = None

    def parse_url(self, url: str):
        self.url = url

        match Regex.find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival|popular|list", url):
            case "cheese":
                self.set_parse_type(ParseType.Cheese)

                self.parser = CheeseParser(self.parser_callback)

            case "list":
                self.set_parse_type(ParseType.Video)

                self.parser = ListParser(self.parser_callback)

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

            case "popular":
                self.set_parse_type(ParseType.Video)

                self.parser = PopularParser(self.parser_callback)

            case _:
                raise GlobalException(code = StatusCode.URL.value, callback = self.onError)
    
        rtnVal = self.parser.parse_url(url)

        if StatusCode(rtnVal) == StatusCode.Success:
            wx.CallAfter(self.parse_success)
    
    def parse_success(self):
        self.main_window.utils.set_status(ParseStatus.Success)

        match self.parse_type:
            case ParseType.Live:
                wx.CallAfter(self.live_recording)

            case _:
                self.parse_type_str = self.get_parse_type_str()

                self.main_window.show_episode_list(from_menu = False)

                self.set_video_quality_id()

                self.set_stream_type()

    def set_video_quality_id(self):
        data = VideoPreview.get_download_json(self.parse_type)

        self.video_quality_id_list, self.video_quality_desc_list = VideoPreview.get_video_quality_id_desc_list(data)

        self.video_quality_id =  Config.Download.video_quality_id if Config.Download.video_quality_id in self.video_quality_id_list else max(VideoPreview.get_video_available_quality_id_list(data))

        self.video_codec_id = Config.Download.video_codec_id

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

    def live_recording(self):
        self.main_window.onShowLiveRecordingWindowEVT(0)

        self.main_window.live_recording_window.add_new_live_room(self.parser.get_live_info())

    def onError(self):
        def worker():
            self.main_window.utils.set_status(ParseStatus.Error)

            info = GlobalExceptionInfo.info.copy()

            self.main_window.utils.show_error_message_dialog(f"解析失败\n\n错误码：{info.get('code')}\n描述：{info.get('message')}", "错误", info)

        wx.CallAfter(worker)

    def onJump(self, url: str):
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
            def onJump(url: str):
                self.onJump(url)

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
        self.status = ParseStatus.Success

    def init_timer(self):
        if Config.Basic.listen_clipboard:
            if not self.main_window.clipboard_timer.IsRunning():
                self.main_window.clipboard_timer.Start(1000)
        else:
            if self.main_window.clipboard_timer.IsRunning():
                self.main_window.clipboard_timer.Stop()

    def check_url(self, url: str):
        if not url:
            self.show_message_dialog("解析失败\n\n链接不能为空", "警告", wx.ICON_WARNING)
            return True

    def check_update(self, info_bar: bool = False):
        def onError():
            if info_bar:
                self.show_infobar_message("检查更新：当前无法检查更新，请稍候再试。", wx.ICON_ERROR)
            else:
                self.show_error_message_dialog("检查更新失败\n\n当前无法检查更新，请稍候再试。", "检查更新", GlobalExceptionInfo.info.copy())

        def worker():
            def show_update_dialog():
                window = UpdateDialog(self.main_window, info)
                window.ShowModal()

            info = Update.get_update_json()

            if info["version_code"] > Config.APP.version_code:
                if info_bar:
                    self.show_infobar_message("检查更新：有新的更新可用。", wx.ICON_INFORMATION)
                else:
                    wx.CallAfter(show_update_dialog)
            else:
                if not info_bar:
                    self.show_message_dialog("当前没有可用的更新。", "检查更新", wx.ICON_INFORMATION)

        try:
            worker()

        except Exception as e:
            raise GlobalException(callback = onError) from e

    def check_download_items(self):
        if not self.main_window.episode_list.GetCheckedItemCount():
            self.show_message_dialog("下载失败\n\n请选择要下载的项目。", "警告", wx.ICON_WARNING)
            return True

    def check_live_status(self):
        if LiveStatus(LiveInfo.status) == LiveStatus.Not_Started:
            self.show_message_dialog("直播间未开播\n\n当前直播间未开播，请开播后再进行解析", "警告", wx.ICON_WARNING)
            return True
        
        self.show_message_dialog("解析失败\n\n当前版本暂不支持直播链接解析，请等待后续版本支持", "警告", wx.ICON_WARNING)
        return True

    def check_parse_status(self):
        if self.main_window.IsShown():
            if self.status != ParseStatus.Parsing:
                return True

    def get_changelog(self):
        def show_changelog_dialog():
            dlg = ChangeLogDialog(self.main_window, info)
            dlg.ShowModal()

        def onError():
            self.show_error_message_dialog("获取更新日志失败\n\n当前无法获取更新日志，请稍候再试。", "获取更新日志", GlobalExceptionInfo.info.copy())

        try:
            info = Update.get_changelog()

            wx.CallAfter(show_changelog_dialog)

        except Exception as e:
            raise GlobalException(callback = onError) from e

    def user_logout(self):
        Login.logout()

        self.show_user_info()

    def user_refresh(self):
        Login.refresh()

        self.show_user_info()

    def show_user_info(self):
        def show_user_face():
            self.main_window.face_icon.Show()
            self.main_window.face_icon.SetBitmap(Face.crop_round_face_bmp(image))
            self.main_window.uname_lab.SetLabel(Config.User.username)

            self.main_window.panel.GetSizer().Layout()

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

    def set_episode_display_mode(self, mode: EpisodeDisplayType):
        Config.Misc.episode_display_mode = mode.value

        self.main_window.show_episode_list()

    def set_episode_full_name(self):
        Config.Misc.show_episode_full_name = not Config.Misc.show_episode_full_name

        self.main_window.show_episode_list()

    def update_checked_item_count(self, count: int):
        label = f"(共 {self.main_window.episode_list.count} 个{f'，已选择 {count} 个)' if count else ')'}"

        self.main_window.type_lab.SetLabel(f"{self.main_window.parser.parse_type_str} {label}")

        self.main_window.panel.Layout()

    def read_clipboard(self, event):
        url: str = ClipBoard.Read()

        if url and url != self.main_window.parser.url:
            if self.validate_url(url) and self.check_parse_status():
                self.main_window.url_box.SetValue(url)

                wx.CallAfter(self.main_window.onParseEVT, event)

    def validate_url(self, url: str):
        if url.startswith(("http", "https")) and "bilibili.com" in url:
            if url != self.main_window.url_box.GetValue():
                if Regex.find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival|popular|list", url):
                    return True

    def get_episode_title(self):
        return self.main_window.episode_list.GetItemText(self.main_window.episode_list.GetSelection(), 1)
    
    def set_episode_title(self, item, title: str):
        self.main_window.episode_list.SetItemTitle(item, title)

        if self.main_window.parser.parse_type == ParseType.Live:
            LiveInfo.title = title

    def save_exit_dialog_settings(self, flag: int): 
        save = ExitOption(Config.Basic.exit_option) == ExitOption.AskOnce

        match flag:
            case wx.ID_YES:
                Config.Basic.exit_option = ExitOption.TaskIcon.value

            case wx.ID_NO:
                Config.Basic.exit_option = ExitOption.Exit.value

        if save:
            Config.save_app_config()

    def save_window_params_settings(self):
        if Config.Basic.remember_window_status:
            Config.Basic.window_pos = list(self.main_window.GetPosition())
            Config.Basic.window_size = list(self.main_window.GetSize())
            Config.Basic.window_maximized = self.main_window.IsMaximized()

            Config.save_app_config()

    def check_ffmpeg(self):
        class FFmpegCallback(Callback):
            @staticmethod
            def onSuccess(*process):
                pass
            
            @staticmethod
            def onError(*process):
                def worker():
                    dlg = wx.MessageDialog(self.main_window, "未检测到 FFmpeg\n\n未检测到 FFmpeg，无法进行视频合并、截取和转换。\n\n请检查是否为 FFmpeg 创建环境变量或 FFmpeg 是否已在运行目录中。", "警告", wx.ICON_WARNING | wx.YES_NO)
                    dlg.SetYesNoLabels("安装 FFmpeg", "忽略")

                    if dlg.ShowModal() == wx.ID_YES:
                        webbrowser.open("https://bili23.scott-sloan.cn/doc/install/ffmpeg.html")
                    
                wx.CallAfter(worker)

        FFmpeg.Env.check_availability(FFmpegCallback)

    def set_status(self, status: ParseStatus):
        def update():
            self.main_window.processing_icon.Show(processing_icon)
            self.main_window.type_lab.SetLabel(type_lab)

            self.main_window.detail_btn.Show(detail_btn)
            self.main_window.graph_btn.Show(graph_btn)

        def enable_controls(enable: bool, option_enable: bool = True, not_live: bool = True):
            self.main_window.url_box.Enable(enable)
            self.main_window.get_btn.Enable(enable)
            self.main_window.episode_list.Enable(enable)
            self.main_window.download_btn.Enable(enable and not_live)
            self.main_window.episode_option_btn.Enable(enable and option_enable and not graph_btn and not_live)
            self.main_window.download_option_btn.Enable(enable and option_enable and not_live)

        self.status = status

        match status:
            case ParseStatus.Parsing:
                processing_icon = True
                type_lab = "正在解析中"

                detail_btn = False
                graph_btn = False

                enable_controls(False)

                self.show_processing_window(ProcessingType.Parse)

            case ParseStatus.Success:
                processing_icon = False
                type_lab = ""

                not_live = self.main_window.parser.parse_type != ParseType.Live

                detail_btn = True and not_live
                graph_btn = VideoInfo.is_interactive

                enable_controls(True, not_live = not_live)

                self.hide_processing_window()

            case ParseStatus.Error:
                processing_icon = False
                type_lab = ""

                detail_btn = False
                graph_btn = False

                enable_controls(True, option_enable = False)

                self.hide_processing_window()

        update()

        self.main_window.panel.Layout()

    def show_message_dialog(self, message: str, caption: str, style: int):
        def worker():
            dlg = wx.MessageDialog(self.main_window, message, caption, style)
            dlg.ShowModal()

        wx.CallAfter(worker)

    def show_error_message_dialog(self, message: str, caption: str, info: dict):
        def worker():
            dlg = wx.MessageDialog(self.main_window, message, caption, wx.ICON_ERROR | wx.YES_NO)
            dlg.SetYesNoLabels("详细信息", "确定")

            if dlg.ShowModal() == wx.ID_YES:
                err_dlg = ErrorInfoDialog(self.main_window, info)
                err_dlg.ShowModal()

        wx.CallAfter(worker)

    def show_infobar_message(self, message: str, flag: int):
        wx.CallAfter(self.main_window.infobar.ShowMessage, message, flag)

    def show_processing_window(self, type: ProcessingType):
        wx.CallAfter(self.main_window.processing_window.ShowModal, type)

    def hide_processing_window(self):
        wx.CallAfter(self.main_window.processing_window.Close)

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
        vbox.Add(self.infobar, 0, wx.EXPAND)
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
        help_menu.Append(ID.FEEDBACK_MENU, "意见反馈(&B)")
        help_menu.Append(ID.ABOUT_MENU, "关于(&A)")

        menu_bar.Append(tool_menu, "工具(&T)")
        menu_bar.Append(help_menu, "帮助(&H)")

        self.SetMenuBar(menu_bar)

    def Bind_EVT(self):
        self.Bind(wx.EVT_MENU, self.onMenuEVT)
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.url_box.Bind(wx.EVT_SEARCH, self.onParseEVT)
        self.get_btn.Bind(wx.EVT_BUTTON, self.onParseEVT)

        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadWindowEVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.onDownloadEVT)

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
            async def check_ffmpeg():
                if Config.Merge.ffmpeg_check_available_when_launch:
                    self.utils.check_ffmpeg()

            async def check_update():
                if Config.Merge.ffmpeg_check_available_when_launch:
                    self.utils.check_update(info_bar = True)

            async def show_user_info():
                self.utils.show_user_info()

            FFmpeg.Env.detect()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            tasks = [
                loop.create_task(check_ffmpeg()),
                loop.create_task(check_update()),
                loop.create_task(show_user_info())
            ]

            loop.run_until_complete(asyncio.wait(tasks))

        self.parser = Parser(self)

        self.processing_window = ProcessingWindow(self)
        self.download_window = DownloadManagerWindow(self)
        self.live_recording_window = LiveRecordingWindow(self)

        self.utils.init_timer()

        Thread(target = worker).start()

    def onMenuEVT(self, event):
        match event.GetId():
            case ID.LOGIN_MENU:
                dlg = LoginDialog(self)
                dlg.ShowModal()

            case ID.LOGOUT_MENU:
                dlg = wx.MessageDialog(self, '退出登录\n\n是否要退出登录？', "警告", wx.ICON_WARNING | wx.YES_NO)

                if dlg.ShowModal() == wx.ID_YES:
                    self.utils.user_logout()

            case ID.REFRESH_MENU:
                Thread(target = self.utils.user_refresh).start()

            case ID.DEBUG_MENU:
                window = DebugWindow(self)
                window.Show()

            case ID.LIVE_RECORDING_MENU:
                self.onShowLiveRecordingWindowEVT(event)

            case ID.FORMAT_FACTORY_MENU:
                window = FormatFactoryWindow(self)
                window.Show()

            case ID.SETTINGS_MENU:
                window = SettingWindow(self)
                window.ShowModal()

            case ID.CHECK_UPDATE_MENU:
                Thread(target = self.utils.check_update).start()

            case ID.CHANGELOG_MENU:
                Thread(target = self.utils.get_changelog).start()

            case ID.HELP_MENU:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/use/basic.html")

            case ID.FEEDBACK_MENU:
                webbrowser.open("https://github.com/ScottSloan/Bili23-Downloader/issues")

            case ID.ABOUT_MENU:
                dlg = AboutWindow(self)
                dlg.ShowModal()

            case ID.EPISODE_SINGLE_MENU:
                self.utils.set_episode_display_mode(EpisodeDisplayType.Single)

            case ID.EPISODE_IN_SECTION_MENU:
                self.utils.set_episode_display_mode(EpisodeDisplayType.In_Section)

            case ID.EPISODE_ALL_SECTIONS_MENU:
                self.utils.set_episode_display_mode(EpisodeDisplayType.All)
                
            case ID.EPISODE_FULL_NAME_MENU:
                self.utils.set_episode_full_name()

    def onCloseEVT(self, event):
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

    def onShowDownloadWindowEVT(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()
        
        elif self.download_window.IsIconized():
            if Config.Basic.auto_show_download_window:
                self.download_window.Iconize(False)
        
        if Config.Basic.auto_show_download_window:
            #self.download_window.downloading_page_btn.onClickEVT(event)
            self.download_window.Raise()

    def onShowLiveRecordingWindowEVT(self, event):
        if not self.live_recording_window.IsShown():
            self.live_recording_window.Show()

        elif self.live_recording_window.IsIconized():
            self.Iconize(False)

        self.live_recording_window.Raise()

    def onDownloadEVT(self, event):
        def download_video():
            def after_show_items_callback():
                self.utils.hide_processing_window()
                self.onShowDownloadWindowEVT(event)

            # 确认下载选项
            if Config.Basic.auto_popup_option_dialog:
                if self.onShowDownloadOptionDialogEVT(event) != wx.ID_OK:
                    return

            self.episode_list.GetAllCheckedItem(self.parser.parse_type, self.parser.video_quality_id, self.parser.video_codec_id)

            Thread(target = self.download_window.add_to_download_list, args = (self.episode_list.download_task_info_list, after_show_items_callback, True, True)).start()

            self.processing_window.ShowModal(ProcessingType.Process)

        if self.utils.check_download_items():
            return
        
        download_video()

    def onParseEVT(self, event):
        url = self.url_box.GetValue()

        if self.utils.check_url(url):
            return

        self.episode_list.init_episode_list()

        Thread(target = self.parser.parse_url, args = (url, )).start()

        self.utils.set_status(ParseStatus.Parsing)

    def onShowEpisodeOptionMenuEVT(self, event):
        menu = EpisodeOptionMenu()

        self.PopupMenu(menu)

    def onShowUserMenuEVT(self, event):
        if Config.User.login:
            menu = UserMenu()

            self.PopupMenu(menu)
        else:
            evt = wx.PyCommandEvent(wx.EVT_MENU.typeId, id = ID.LOGIN_MENU)
            wx.PostEvent(self.GetEventHandler(), evt)

    def onEpisodeListContextMenuEVT(self, event):
        match event.GetId():
            case ID.EPISODE_LIST_VIEW_COVER_MENU:
                item_data = self.episode_list.GetItemData(self.episode_list.GetSelection())

                if item_data.cover_url:
                    Cover.view_cover(self, item_data.cover_url)
                
            case ID.EPISODE_LIST_COPY_TITLE_MENU:
                ClipBoard.Write(self.utils.get_episode_title())

            case ID.EPISODE_LIST_COPY_URL_MENU:
                item_data = self.episode_list.GetItemData(self.episode_list.GetSelection())

                ClipBoard.Write(item_data.link)

            case ID.EPISODE_LIST_EDIT_TITLE_MENU:
                item = self.episode_list.GetSelection()

                dlg = EditTitleDialog(self, self.utils.get_episode_title())

                if dlg.ShowModal() == wx.ID_OK:
                    self.utils.set_episode_title(item, dlg.title_box.GetValue())

            case ID.EPISODE_LIST_CHECK_MENU:
                self.episode_list.CheckCurrentItem()

            case ID.EPISODE_LIST_COLLAPSE_MENU:
                self.episode_list.CollapseCurrentItem()

    def onShowGraphWindowEVT(self):
        WebPage.show_webpage(self, "graph.html")

    def onShowDetailInfoDialogEVT(self):
        dlg = DetailDialog(self, self.parser.parse_type)
        dlg.ShowModal()

    def onShowDownloadOptionDialogEVT(self, event):
        dlg = DownloadOptionDialog(self)
        return dlg.ShowModal()
    
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
    def video_quality_desc_list(self):
        return self.parser.video_quality_desc_list