import wx
import asyncio
import webbrowser

from utils.config import Config
from utils.auth.login_v2 import Login

from utils.common.enums import ParseStatus, ParseType, ExitOption, ProcessingType, EpisodeDisplayType
from utils.common.exception import GlobalExceptionInfo, GlobalException
from utils.common.update import Update
from utils.common.regex import Regex

from utils.module.pic.face import Face
from utils.module.ffmpeg_v2 import FFmpeg
from utils.module.clipboard import ClipBoard

from utils.parse.video import VideoInfo
from utils.parse.live import LiveInfo

from gui.dialog.misc.about import AboutWindow
from gui.dialog.setting.edit_title import EditTitleDialog
from gui.dialog.detail import DetailDialog
from gui.dialog.download_option_v3 import DownloadOptionDialog
from gui.dialog.login.login_v2 import LoginDialog
from gui.dialog.search_episode_list import SearchEpisodeListDialog

from gui.window.debug import DebugWindow
from gui.window.format_factory import FormatFactoryWindow
from gui.window.settings.settings_v2 import SettingWindow

from gui.dialog.misc.update import UpdateDialog
from gui.dialog.misc.changelog import ChangeLogDialog
from gui.dialog.error import ErrorInfoDialog

class Window:
    dialog_show = False

    flag_list: list = []
    
    def show_dialog(func):
        def function(*args, **kwargs):
            if not Utils.dialog_show:
                Window.dialog_show = True

                rtn = func(*args, **kwargs)

            Window.dialog_show = False

            return rtn

        return function
    
    def show_frame(func):
        def function(*args, **kwargs):
            frame: wx.Frame = func(*args, **kwargs)

            name = frame.GetName()

            if name in Window.flag_list:
                frame = wx.FindWindowByName(name)

                frame.Raise()

                wx.Bell()
            else:
                frame.Bind(wx.EVT_CLOSE, Window.reset_flag)

                Window.flag_list.append(name)

                frame.Show()

        return function

    @staticmethod
    @show_dialog
    def welcome_dialog(parent: wx.Window):
        dlg = wx.MessageDialog(parent, "欢迎使用 Bili23 Downloader\n\n为了帮助您快速上手并充分利用所有功能，请先阅读程序说明文档。\n\n近期版本更新：\nASS 弹幕/字幕下载、自定义下载文件名/自动分类、合集列表解析\n\n如遇到问题，欢迎加入社区，或在 Github 提出 issue 进行反馈。", "Guide", wx.ICON_INFORMATION | wx.YES_NO)
        dlg.SetYesNoLabels("说明文档", "确定")

        return dlg.ShowModal()
    
    @staticmethod
    def message_dialog(parent: wx.Window, message: str, caption: str, style: int):
        def worker():
            dlg = wx.MessageDialog(parent, message, caption, style)
            dlg.ShowModal()

        wx.CallAfter(worker)

    @staticmethod
    @show_dialog
    def about_window(parent: wx.Window):
        window = AboutWindow(parent)
        window.ShowModal()

    @staticmethod
    @show_dialog
    def edit_title_dialog(parent: wx.Window, title: str):
        dlg = EditTitleDialog(parent, title)

        if dlg.ShowModal() == wx.ID_OK:
            return dlg.title_box.GetValue() 

    @staticmethod
    @show_dialog
    def detail_dialog(parent: wx.Window, parse_type: ParseType):
        dlg = DetailDialog(parent, parse_type)
        dlg.ShowModal()

    @staticmethod
    @show_dialog
    def download_option_dialog(parent: wx.Window):
        dlg = DownloadOptionDialog(parent)
        return dlg.ShowModal()
    
    @staticmethod
    @show_dialog
    def login_dialog(parent: wx.Window):
        dlg = LoginDialog(parent)
        dlg.ShowModal()

    @staticmethod
    @show_dialog
    def settings_window(parent: wx.Window):
        window = SettingWindow(parent)
        window.ShowModal()

    @staticmethod
    @show_frame
    def debug_window(parent: wx.Window):
        return DebugWindow(parent)

    @classmethod
    @show_frame
    def search_dialog(cls, parent: wx.Window):
        return SearchEpisodeListDialog(parent)
    
    @staticmethod
    @show_frame
    def format_factory_window(parent: wx.Window):
        return FormatFactoryWindow(parent)

    @classmethod
    def reset_flag(cls, event: wx.CloseEvent):
        frame: wx.Frame = event.GetEventObject()

        cls.flag_list.remove(frame.GetName())

        event.Skip()

class Utils:
    dialog_show = False

    def __init__(self, parent: wx.Window):
        from gui.window.main.main_v3 import MainWindow

        self.main_window: MainWindow = parent
        self.status = ParseStatus.Success

        self.copy_from_menu = False
        self.dialog_show = False

    def init_timer(self):
        if Config.Basic.listen_clipboard:
            if not self.main_window.clipboard_timer.IsRunning():
                self.main_window.clipboard_timer.Start(1000)
        else:
            if self.main_window.clipboard_timer.IsRunning():
                self.main_window.clipboard_timer.Stop()

    def check_url(self, url: str):
        if not url:
            Window.message_dialog("解析失败\n\n链接不能为空", "警告", wx.ICON_WARNING)
            return True

    def check_update(self, from_menu: bool = False):
        def onError():
            self.show_error_message_dialog("检查更新失败\n\n当前无法检查更新，请稍候再试。", "检查更新", GlobalExceptionInfo.info.copy())

        def show_update_dialog():
            window = UpdateDialog(self.main_window, info)
            window.ShowModal()

        try:
            info = Update.get_update_json()

            version = info.get("version_code")

            if version > Config.APP.version_code and version != Config.Misc.ignore_version:
                wx.CallAfter(show_update_dialog)
            else:
                if from_menu:
                    Window.message_dialog("当前没有可用的更新。", "检查更新", wx.ICON_INFORMATION)

        except Exception as e:
            raise GlobalException(callback = onError) from e

    async def check_update_async(self):
        self.check_update()

    def check_download_items(self):
        if not self.main_window.episode_list.GetCheckedItemCount():
            Window.message_dialog("下载失败\n\n请选择要下载的项目。", "警告", wx.ICON_WARNING)
            return True

    def check_parse_status(self):
        if self.main_window.utils.copy_from_menu:
            return False
        
        if self.main_window.utils.dialog_show:
            return False

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
        def on_error():
            self.show_error_message_dialog("注销登录失败\n\n无法完成注销登录操作", "错误", GlobalExceptionInfo.info.copy())

        try:
            Login.logout()

            self.show_user_info()

        except Exception as e:
            raise GlobalException(callback = on_error) from e

    def user_refresh(self):
        def on_error():
            self.show_error_message_dialog("刷新登录信息失败\n\n无法刷新登录信息", "错误", GlobalExceptionInfo.info.copy())

        try:
            Login.refresh()

            self.show_user_info()

        except Exception as e:
            raise GlobalException(callback = on_error) from e

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

    async def show_user_info_async(self):
        self.show_user_info()

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
                self.main_window.utils.copy_from_menu = False

                self.main_window.url_box.SetValue(url)

                wx.CallAfter(self.main_window.onParseEVT, event)

    def validate_url(self, url: str):
        if url.startswith(("http", "https")) and "bilibili.com" in url:
            if url != self.main_window.url_box.GetValue():
                if Regex.find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival|popular|space|list", url):
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
        def worker():
            dlg = wx.MessageDialog(self.main_window, "未检测到 FFmpeg\n\n未检测到 FFmpeg，无法进行视频合并、截取和转换。\n\n请检查是否为 FFmpeg 创建环境变量或 FFmpeg 是否已在运行目录中。", "警告", wx.ICON_WARNING | wx.YES_NO)
            dlg.SetYesNoLabels("安装 FFmpeg", "忽略")

            if dlg.ShowModal() == wx.ID_YES:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/install/ffmpeg.html")
            
        result = FFmpeg.Env.check_availability()

        if result:
            wx.CallAfter(worker)

    async def check_ffmpeg_async(self):
        if Config.Merge.ffmpeg_check_available_when_launch:
            self.check_ffmpeg()

    async def async_worker(self):
        tasks = [
            asyncio.create_task(self.show_user_info_async()),
            asyncio.create_task(self.check_ffmpeg_async()),
            asyncio.create_task(self.check_update_async())
        ]

        await asyncio.gather(*tasks, return_exceptions = True)

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

    def show_error_message_dialog(self, message: str, caption: str, info: dict):
        def worker():
            dlg = wx.MessageDialog(self.main_window, message, caption, wx.ICON_ERROR | wx.YES_NO)
            dlg.SetYesNoLabels("详细信息", "确定")

            if dlg.ShowModal() == wx.ID_YES:
                err_dlg = ErrorInfoDialog(self.main_window, info)
                err_dlg.ShowModal()

        wx.CallAfter(worker)

    def show_processing_window(self, type: ProcessingType):
        wx.CallAfter(self.main_window.processing_window.ShowModal, type)

    def hide_processing_window(self):
        wx.CallAfter(self.main_window.processing_window.Close)

    def show_welcome_dialog(self):
        def worker():
            if Window.welcome_dialog(self.main_window) == wx.ID_YES:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/use/basic.html")
            
            Config.Basic.is_new_user = False

            Config.save_app_config()
        
        if Config.Basic.is_new_user:
            wx.CallAfter(worker)
