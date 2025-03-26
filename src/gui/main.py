import wx
import os
import wx.py
import requests
import webbrowser
import wx.dataview

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.activity import ActivityParser
from utils.parse.live import LiveInfo, LiveParser
from utils.parse.b23 import B23Parser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.episode import EpisodeInfo

from utils.config import Config
from utils.auth.login import QRLogin
from utils.tool_v2 import UniversalTool, RequestTool
from utils.module.ffmpeg import FFmpeg
from utils.common.thread import Thread
from utils.common.exception import GlobalExceptionInfo, GlobalException
from utils.common.map import video_quality_map, live_quality_map
from utils.common.icon_v2 import IconManager, IconType
from utils.common.enums import ParseType, EpisodeDisplayType, LiveStatus, StatusCode, VideoQualityID, VideoType
from utils.common.data_type import ParseCallback, TreeListItemInfo

from gui.component.frame import Frame
from gui.component.info_bar import InfoBar
from gui.component.tree_list import TreeListCtrl
from gui.component.panel import Panel
from gui.component.bitmap_button import BitmapButton
from gui.window.download_v3 import DownloadManagerWindow
from gui.window.settings import SettingWindow
from gui.window.login import LoginWindow

from gui.dialog.about import AboutWindow
from gui.dialog.processing import ProcessingWindow
from gui.dialog.update import UpdateWindow
from gui.dialog.converter import ConverterWindow
from gui.dialog.live import LiveRecordingWindow
from gui.dialog.option import OptionDialog
from gui.dialog.error import ErrorInfoDialog
from gui.dialog.detail import DetailDialog
from gui.dialog.edit_title import EditTitleDialog
from gui.dialog.cover import CoverViewerDialog
from gui.dialog.changelog import ChangeLogDialog
from gui.dialog.cut_clip import CutClipDialog

class MainWindow(Frame):
    def __init__(self, parent):
        def set_window_size():
            match Config.Sys.platform:
                case "windows" | "darwin":
                    self.SetSize(self.FromDIP((800, 450)))

                case "linux":
                    self.SetClientSize(self.FromDIP((880, 450)))

        Frame.__init__(self, parent, Config.APP.name)

        set_window_size()

        self.init_UI()

        self.init_utils()

        self.Bind_EVT()

        self.CenterOnParent()
    
    def init_UI(self):
        def set_dark_mode():
            if Config.Sys.platform != "windows":
                Config.Sys.dark_mode = wx.SystemSettings.GetAppearance().IsDark()

        def _set_button_variant():
            if Config.Sys.platform == "darwin":
                self.download_mgr_btn.SetWindowVariant(wx.WINDOW_VARIANT_LARGE)
                self.download_btn.SetWindowVariant(wx.WINDOW_VARIANT_LARGE)

        set_dark_mode()

        icon_manager = IconManager(self)

        # 避免出现 iCCP sRGB 警告
        wx.Image.SetDefaultLoadFlags(0)

        self.init_ids()

        self.panel = Panel(self)

        self.infobar = InfoBar(self.panel)

        url_hbox = wx.BoxSizer(wx.HORIZONTAL)

        url_lab = wx.StaticText(self.panel, -1, "链接")
        self.url_box = wx.SearchCtrl(self.panel, -1)
        self.url_box.ShowSearchButton(False)
        self.url_box.ShowCancelButton(True)
        self.url_box.SetDescriptiveText("在此处粘贴链接进行解析")
        self.get_btn = wx.Button(self.panel, -1, "Get")

        url_hbox.Add(url_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        url_hbox.Add(self.url_box, 1, wx.EXPAND | wx.ALL & (~wx.LEFT), 10)
        url_hbox.Add(self.get_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        video_info_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.processing_icon = wx.StaticBitmap(self.panel, -1, icon_manager.get_icon_bitmap(IconType.LOADING_ICON), size = self.FromDIP((24, 24)))
        self.processing_icon.Hide()
        self.type_lab = wx.StaticText(self.panel, -1, "")
        self.detail_icon = wx.StaticBitmap(self.panel, -1, icon_manager.get_icon_bitmap(IconType.INFO_ICON), size = self.FromDIP((24, 24)))
        self.detail_icon.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.detail_icon.SetToolTip("查看详细信息")
        self.detail_icon.Hide()
        self.video_quality_lab = wx.StaticText(self.panel, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self.panel, -1)

        self.episode_option_btn = BitmapButton(self.panel, icon_manager.get_icon_bitmap(IconType.LIST_ICON))
        self.episode_option_btn.Enable(False)
        self.episode_option_btn.SetToolTip("剧集列表显示设置")
        self.download_option_btn = BitmapButton(self.panel, icon_manager.get_icon_bitmap(IconType.SETTING_ICON))
        self.download_option_btn.Enable(False)
        self.download_option_btn.SetToolTip("下载选项")

        video_info_hbox.Add(self.processing_icon, 0, wx.LEFT, 10)
        video_info_hbox.Add(self.type_lab, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        video_info_hbox.Add(self.detail_icon, 0, wx.ALIGN_CENTER)
        video_info_hbox.AddStretchSpacer()
        video_info_hbox.Add(self.video_quality_lab, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        video_info_hbox.Add(self.video_quality_choice, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)
        video_info_hbox.Add(self.episode_option_btn, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)
        video_info_hbox.Add(self.download_option_btn, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)

        self.treelist = TreeListCtrl(self.panel)
        self.treelist.SetSize(self.FromDIP((800, 260)))

        self.download_mgr_btn = wx.Button(self.panel, -1, "下载管理", size = self.get_scaled_size((100, 30)))
        self.download_btn = wx.Button(self.panel, -1, "开始下载", size = self.get_scaled_size((100, 30)))
        self.download_btn.Enable(False)
        
        self.face = wx.StaticBitmap(self.panel, -1, size = self.FromDIP((32, 32)))
        self.face.Cursor = wx.Cursor(wx.CURSOR_HAND)
        self.uname_lab = wx.StaticText(self.panel, -1, "未登录", style = wx.ST_ELLIPSIZE_END)
        self.uname_lab.Cursor = wx.Cursor(wx.CURSOR_HAND)
        self.uname_lab_ex = wx.StaticText(self.panel, -1, "", size = self.FromDIP((1, 32)))

        self.userinfo_hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.userinfo_hbox.Add(self.face, 0, wx.ALL & (~wx.RIGHT), 15)
        self.userinfo_hbox.Add(self.uname_lab, 0, wx.LEFT | wx.ALIGN_CENTER, 10)
        self.userinfo_hbox.Add(self.uname_lab_ex, 0, wx.ALIGN_CENTER, 10)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)

        bottom_hbox.Add(self.userinfo_hbox, 0, wx.EXPAND | wx.CENTER)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        bottom_hbox.Add(self.download_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(url_hbox, 0, wx.EXPAND)
        vbox.Add(video_info_hbox, 0, wx.EXPAND)
        vbox.Add(self.treelist, 1, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.frame_vbox = wx.BoxSizer(wx.VERTICAL)
        self.frame_vbox.Add(self.infobar, 1, wx.EXPAND)
        self.frame_vbox.Add(vbox, 1, wx.EXPAND)

        self.panel.SetSizerAndFit(self.frame_vbox)

        self.init_menubar()

        _set_button_variant()

    def init_utils(self):
        def worker():
            def check_update():
                if Config.Misc.auto_check_update:
                    try:
                        UniversalTool.get_update_json()

                        if Config.Temp.update_json["version_code"] > Config.APP.version_code:
                            self.showInfobarMessage("检查更新：有新的更新可用", wx.ICON_INFORMATION)

                    except Exception:
                        self.showInfobarMessage("检查更新：当前无法检查更新，请稍候再试", wx.ICON_ERROR)

            def check_ffmpeg():
                ffmpeg = FFmpeg()
                ffmpeg.check_available()

                if not Config.FFmpeg.available:
                    dlg = wx.MessageDialog(self, "未检测到 FFmpeg\n\n未检测到 FFmpeg，视频合成不可用。\n\n若您已确认安装 FFmpeg，请检查（二者其一即可）：\n1.为 FFmpeg 设置环境变量\n2.将 FFmpeg 放置到程序运行目录下\n\n点击下方安装 FFmpeg 按钮，将打开 FFmpeg 安装教程，请按照教程安装。", "警告", wx.ICON_WARNING | wx.YES_NO)
                    dlg.SetYesNoLabels("安装 FFmpeg", "忽略")

                    if dlg.ShowModal() == wx.ID_YES:
                        import webbrowser

                        webbrowser.open("https://bili23.scott-sloan.cn/doc/install/ffmpeg.html")

            def check_login():
                if Config.Temp.need_login:
                    wx.MessageDialog(self, "登录状态失效\n\n账号登录状态已失效，请重新登录", "警告", wx.ICON_WARNING).ShowModal()

            wx.CallAfter(check_login)
            
            check_ffmpeg()

            check_update()

        Thread(target = worker).start()

    def onCloseEVT(self, event):
        # if self.download_window.get_download_task_count([DownloadStatus.Downloading.value, DownloadStatus.Merging.value]):
        #     dlg = wx.MessageDialog(self, "是否退出程序\n\n当前有下载任务正在进行中，是否退出程序？\n\n程序将在下次启动时恢复下载进度。", "警告", style = wx.ICON_WARNING | wx.YES_NO)

        #     if dlg.ShowModal() == wx.ID_NO:
        #         return

        event.Skip()

    def onRefreshEVT(self, event):
        login = QRLogin(requests.Session())
        user_info = login.get_user_info(refresh = True)

        Config.User.face_url = user_info["face_url"]
        Config.User.username = user_info["username"]

        os.remove(Config.User.face_path)

        # 刷新用户信息后重新显示
        Thread(target = self.showUserInfoThread).start()
