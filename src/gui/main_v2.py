import wx
import webbrowser

from utils.config import Config

from utils.module.ffmpeg_v2 import FFmpeg

from utils.common.thread import Thread

from utils.common.enums import ParseStatus, ParseType, StatusCode, EpisodeDisplayType, LiveStatus, Platform, ProcessingType, ExitOption
from utils.common.data_type import ParseCallback, TreeListCallback, Callback
from utils.common.regex import Regex

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.live import LiveInfo, LiveParser

from gui.window.download_v3 import DownloadManagerWindow

from gui.dialog.processing import ProcessingWindow
from gui.dialog.live import LiveRecordingWindow
from gui.dialog.confirm.duplicate import DuplicateDialog

from gui.component.window.frame import Frame


class MainWindow(Frame):
    def __init__(self, parent):
        def set_window_property():
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

        Frame.__init__(self, parent, Config.APP.name)

        set_window_property()

        self.get_sys_settings()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

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

    def init_utils(self):
        def start_thread():
            FFmpeg.Env.detect()

            if Config.Merge.ffmpeg_check_available_when_lauch:
                Thread(target = self.check_ffmpeg_available).start()

            if Config.Misc.check_update_when_lauch:
                Thread(target = self.check_update).start()

            Thread(target = self.show_user_info).start()

        def init_timer():
            if Config.Basic.listen_clipboard:
                self.clipboard_timer.Start(1000)

        self.download_window = DownloadManagerWindow(self)
        self.processing_window = ProcessingWindow(self)
        
        self.current_parse_url = ""
        self.error_url_list = []
        self.status = ParseStatus.Finish.value

        self.video_quality_id = 0
        self.video_quality_id_list = []
        self.video_quality_desc_list = []

        init_timer()

        start_thread()

    def onDownloadEVT(self, event):
        match self.current_parse_type:
            case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                def callback():
                    self.onOpenDownloadMgrEVT(event)

                if not self.episode_list.GetCheckedItemCount():
                    wx.MessageDialog(self, "下载失败\n\n请选择要下载的项目。", "警告", wx.ICON_WARNING).ShowModal()
                    return
                
                if Config.Basic.auto_popup_option_dialog:
                    if self.onShowDownloadOptionDlgEVT(event) != wx.ID_OK:
                        return
                
                self.episode_list.GetAllCheckedItem(self.current_parse_type, self.video_quality_id)

                duplicate_episode_list = self.download_window.find_duplicate_tasks(self.episode_list.download_task_info_list)

                if duplicate_episode_list:
                    if DuplicateDialog(self, duplicate_episode_list).ShowModal() != wx.ID_OK:
                        return

                Thread(target = self.download_window.add_to_download_list, args = (self.episode_list.download_task_info_list, callback, )).start()

                self.processing_window.ShowModal(ProcessingType.Process)

            case ParseType.Live:
                if LiveInfo.status == LiveStatus.Not_Started.value:
                    wx.MessageDialog(self, "直播间未开播\n\n当前直播间未开播，请开播后再进行解析", "警告", wx.ICON_WARNING).ShowModal()
                    return
                
                self.live_parser.get_live_stream(self.live_quality_id)
                
                LiveRecordingWindow(self).ShowModal()

    def check_ffmpeg_available(self):
        class callback(Callback):
            @staticmethod
            def onSuccess(*process):
                pass
            
            @staticmethod
            def onError(*process):
                def worker():
                    dlg = wx.MessageDialog(self, "未检测到 FFmpeg\n\n未检测到 FFmpeg，无法进行视频合并、截取和转换。\n\n请检查是否为 FFmpeg 创建环境变量或 FFmpeg 是否已在运行目录中。", "警告", wx.ICON_WARNING | wx.YES_NO)
                    dlg.SetYesNoLabels("安装 FFmpeg", "忽略")

                    if dlg.ShowModal() == wx.ID_YES:
                        webbrowser.open("https://bili23.scott-sloan.cn/doc/install/ffmpeg.html")

                        return super().onError(*process)
                    
                wx.CallAfter(worker)
            
        FFmpeg.Env.check_availability(callback)

    def set_parse_status(self, status: ParseStatus):
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

        self.status = status

        match status:
            case ParseStatus.Parsing:
                self.processing_icon.Show(True)

                self.type_lab.SetLabel("正在解析中")

                self.detail_btn.Hide()

                set_enable_status(False)

                self.processing_window.ShowModal(ProcessingType.Parse)
            
            case ParseStatus.Finish:
                self.processing_icon.Hide()

                self.type_lab.SetLabel("")

                self.detail_btn.Show()

                self.graph_btn.Show(VideoInfo.is_interactive)

                set_enable_status(True)
                set_download_btn_label()

                self.processing_window.Close()

            case ParseStatus.Error:
                self.processing_icon.Hide()

                self.type_lab.SetLabel("")

                self.detail_btn.Hide()

                self.url_box.Enable(True)
                self.get_btn.Enable(True)
                self.episode_list.Enable(True)

                self.processing_window.Close()

        self.panel.Layout()
    
    def show_info_bar_message(self, message: str, flag: int):
        wx.CallAfter(self.infobar.ShowMessage, message, flag)

    @property
    def stream_type(self):
        match self.current_parse_type:
            case ParseType.Video:
                return VideoInfo.stream_type
            
            case ParseType.Bangumi:
                return BangumiInfo.stream_type
            
            case ParseType.Cheese:
                return CheeseInfo.stream_type