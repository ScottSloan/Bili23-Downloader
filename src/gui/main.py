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

    def init_menubar(self):
        menu_bar = wx.MenuBar()

        self.help_menu = wx.Menu()
        self.tool_menu = wx.Menu()
        
        menu_bar.Append(self.tool_menu, "工具(&T)")
        menu_bar.Append(self.help_menu, "帮助(&H)")

        if Config.User.login:
            self.tool_menu.Append(self.ID_LOGOUT, "退出登录(&L)")
        else:
            self.tool_menu.Append(self.ID_LOGIN, "登录(&L)")
        
        self.tool_menu.AppendSeparator()

        if Config.Misc.enable_debug:
            self.tool_menu.Append(self.ID_DEBUG, "调试(&D)")

        self.tool_menu.Append(self.ID_CONVERTER, "格式转换(&F)")
        self.tool_menu.Append(self.ID_CUT_CLIP, "截取片段(&I)")
        self.tool_menu.AppendSeparator()
        self.tool_menu.Append(self.ID_SETTINGS, "设置(&S)")

        self.help_menu.Append(self.ID_CHECK_UPDATE, "检查更新(&U)")
        self.help_menu.Append(self.ID_CHANGELOG, "更新日志(&P)")
        self.help_menu.AppendSeparator()
        self.help_menu.Append(self.ID_HELP, "使用帮助(&C)")
        self.help_menu.Append(self.ID_FEEDBACK, "意见反馈(&B)")
        self.help_menu.Append(self.ID_ABOUT, "关于(&A)")

        self.SetMenuBar(menu_bar)

    def init_user_info(self):
        if Config.Misc.show_user_info:
            # 如果用户已登录，则获取用户信息
            if Config.User.login:
                thread = Thread(target = self.showUserInfoThread)
                thread.daemon = True

                thread.start()
            else:
                self.face.Hide()
        else:
            self.uname_lab.Hide()
            self.face.Hide()

        # 调整用户信息 UI
        wx.CallAfter(self.userinfo_hbox.Layout)
        wx.CallAfter(self.frame_vbox.Layout)   
    
    def Bind_EVT(self):
        self.url_box.Bind(wx.EVT_SEARCH, self.onGetEVT)
        self.get_btn.Bind(wx.EVT_BUTTON, self.onGetEVT)
        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadMgrEVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.onDownloadEVT)
        self.download_option_btn.Bind(wx.EVT_BUTTON, self.onDownloadOptionEVT)
        self.episode_option_btn.Bind(wx.EVT_BUTTON, self.onEpisodeOptionEVT)

        self.face.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)
        self.uname_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)

        self.detail_icon.Bind(wx.EVT_LEFT_DOWN, self.onVideoDetailEVT)

        self.Bind(wx.EVT_MENU, self.onLoginEVT, id = self.ID_LOGIN)
        self.Bind(wx.EVT_MENU, self.onDebugEVT, id = self.ID_DEBUG)
        self.Bind(wx.EVT_MENU, self.onSettingEVT, id = self.ID_SETTINGS)
        self.Bind(wx.EVT_MENU, self.onLoadConverter, id = self.ID_CONVERTER)
        self.Bind(wx.EVT_MENU, self.onCutClipEVT, id = self.ID_CUT_CLIP)
        self.Bind(wx.EVT_MENU, self.onAboutEVT, id = self.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.onCheckUpdateEVT, id = self.ID_CHECK_UPDATE)
        self.Bind(wx.EVT_MENU, self.onLogoutEVT, id = self.ID_LOGOUT)
        self.Bind(wx.EVT_MENU, self.onRefreshEVT, id = self.ID_REFRESH)
        self.Bind(wx.EVT_MENU, self.onHelpEVT, id = self.ID_HELP)
        self.Bind(wx.EVT_MENU, self.onChangeLogEVT, id = self.ID_CHANGELOG)
        self.Bind(wx.EVT_MENU, self.onFeedBackEVT, id = self.ID_FEEDBACK)
        self.Bind(wx.EVT_MENU, self.onEpisodeOptionMenuEVT, id = self.ID_EPISODE_SINGLE)
        self.Bind(wx.EVT_MENU, self.onEpisodeOptionMenuEVT, id = self.ID_EPISODE_IN_SECTION)
        self.Bind(wx.EVT_MENU, self.onEpisodeOptionMenuEVT, id = self.ID_EPISODE_ALL_SECTIONS)
        self.Bind(wx.EVT_MENU, self.onEpisodeOptionMenuEVT, id = self.ID_EPISODE_FULL_NAME)

        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.treelist.Bind(wx.dataview.EVT_TREELIST_ITEM_CONTEXT_MENU, self.onEpisodeRightClickEVT)

        self.treelist.Bind(wx.EVT_MENU, self.onEpisodeContextMenuEVT, id = self.ID_EPISODE_LIST_VIEW_COVER)
        self.treelist.Bind(wx.EVT_MENU, self.onEpisodeContextMenuEVT, id = self.ID_EPISODE_LIST_COPY_TITLE)
        self.treelist.Bind(wx.EVT_MENU, self.onEpisodeContextMenuEVT, id = self.ID_EPISODE_LIST_COPY_URL)
        self.treelist.Bind(wx.EVT_MENU, self.onEpisodeContextMenuEVT, id = self.ID_EPISODE_LIST_EDIT_TITLE)
        self.treelist.Bind(wx.EVT_MENU, self.onEpisodeContextMenuEVT, id = self.ID_EPISODE_LIST_CHECK)
        self.treelist.Bind(wx.EVT_MENU, self.onEpisodeContextMenuEVT, id = self.ID_EPISODE_LIST_COLLAPSE)

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
            
        def redirect_callback(url: str):
            Thread(target = self.parse_url_thread, args = (url, )).start()

        callback = ParseCallback()
        callback.error_callback = self.onParseErrorCallback
        callback.redirect_callback = redirect_callback
        
        self.video_parser = VideoParser(callback)
        self.bangumi_parser = BangumiParser(callback)
        self.live_parser = LiveParser(callback)
        self.activity_parser = ActivityParser(callback)
        self.b23_parser = B23Parser(callback)
        self.cheese_parser = CheeseParser(callback)

        self.download_window = DownloadManagerWindow(self)

        self.download_window_opened = False

        self.init_user_info()

        Thread(target = worker).start()

    def init_ids(self):
        self.ID_LOGIN = wx.NewIdRef()
        self.ID_DEBUG = wx.NewIdRef()
        self.ID_CONVERTER = wx.NewIdRef()
        self.ID_CUT_CLIP = wx.NewIdRef()
        self.ID_SETTINGS = wx.NewIdRef()
        self.ID_HELP = wx.NewIdRef()
        self.ID_CHECK_UPDATE = wx.NewIdRef()
        self.ID_CHANGELOG = wx.NewIdRef()
        self.ID_FEEDBACK = wx.NewIdRef()
        self.ID_ABOUT = wx.NewIdRef()

        self.ID_LOGOUT = wx.NewIdRef()
        self.ID_REFRESH = wx.NewIdRef()

        self.ID_EPISODE_SINGLE = wx.NewIdRef()
        self.ID_EPISODE_IN_SECTION = wx.NewIdRef()
        self.ID_EPISODE_ALL_SECTIONS = wx.NewIdRef()
        self.ID_EPISODE_FULL_NAME = wx.NewIdRef()

        self.ID_EPISODE_LIST_VIEW_COVER = wx.NewIdRef()
        self.ID_EPISODE_LIST_COPY_TITLE = wx.NewIdRef()
        self.ID_EPISODE_LIST_COPY_URL = wx.NewIdRef()
        self.ID_EPISODE_LIST_EDIT_TITLE = wx.NewIdRef()
        self.ID_EPISODE_LIST_CHECK = wx.NewIdRef()
        self.ID_EPISODE_LIST_COLLAPSE = wx.NewIdRef()

    def onCloseEVT(self, event):
        # if self.download_window.get_download_task_count([DownloadStatus.Downloading.value, DownloadStatus.Merging.value]):
        #     dlg = wx.MessageDialog(self, "是否退出程序\n\n当前有下载任务正在进行中，是否退出程序？\n\n程序将在下次启动时恢复下载进度。", "警告", style = wx.ICON_WARNING | wx.YES_NO)

        #     if dlg.ShowModal() == wx.ID_NO:
        #         return

        event.Skip()

    def onHelpEVT(self, event):
        import webbrowser

        webbrowser.open("https://bili23.scott-sloan.cn/doc/use/basic.html")

    def onAboutEVT(self, event):
        about_window = AboutWindow(self)
        about_window.ShowModal()

    def onGetEVT(self, event):
        def _clear():
            self.treelist.init_list()

            self.video_quality_choice.Clear()

            self.type_lab.SetLabel("")

        if not self.url_box.GetValue():
            wx.MessageDialog(self, "解析失败\n\n链接不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        _clear()

        url = self.url_box.GetValue()

        # 显示加载窗口
        self._onLoading(True)

        self.download_btn.Enable(False)
        self.episode_option_btn.Enable(False)
        self.download_option_btn.Enable(False)

        self.detail_icon.Hide()

        # 开启解析线程
        Thread(target = self.parse_url_thread, args = (url, )).start()

    def parse_url_thread(self, url: str):
        def callback():
            match self.current_parse_type:
                case ParseType.Video |  ParseType.Bangumi | ParseType.Cheese:
                    self.episode_option_btn.Enable(True)
                    self.download_option_btn.Enable(True)
                    self.download_btn.SetLabel("开始下载")

                case ParseType.Live:
                    self.episode_option_btn.Enable(False)
                    self.download_option_btn.Enable(False)
                    self.download_btn.SetLabel("直播录制")

            self._onLoading(False)

            self.download_btn.Enable(True)
            
            self.showEpisodeList()

        def worker():
            match UniversalTool.re_find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival", url):
                case "cheese":
                    # 课程，都使用 ep, season_id，与番组相同，需要匹配 cheese 特征字
                    self.current_parse_type = ParseType.Cheese

                    return_code = self.cheese_parser.parse_url(url)

                    wx.CallAfter(self.setVideoQualityList)

                case "av" | "BV":
                    # 用户投稿视频
                    self.current_parse_type = ParseType.Video

                    return_code = self.video_parser.parse_url(url)

                    wx.CallAfter(self.setVideoQualityList)

                case "ep" | "ss" | "md":
                    # 番组
                    self.current_parse_type = ParseType.Bangumi

                    return_code = self.bangumi_parser.parse_url(url)

                    wx.CallAfter(self.setVideoQualityList)

                case "live":
                    # 直播
                    self.current_parse_type = ParseType.Live

                    return_code = self.live_parser.parse_url(url)

                    wx.CallAfter(self.setLiveQualityList)

                case "b23.tv" | "bili2233.cn":
                    # 短链接
                    return_code = self.b23_parser.parse_url(url)

                case "blackboard" | "festival":
                    # 活动页链接
                    return_code = self.activity_parser.parse_url(url)

                case _:
                    raise GlobalException(code = StatusCode.URL.value, callback = self.onParseErrorCallback)
                
            return return_code
                
        self.current_parse_type = None

        if worker() == StatusCode.Success.value:
            wx.CallAfter(callback)

    def onDownloadEVT(self, event):
        def worker():
            def callback():
                self.processing_window.Hide()
                self.onOpenDownloadMgrEVT(0)

            self.download_window.add_to_download_list(self.treelist.download_task_info_list, callback)

        def _get_live_stram():
            # 获取选定清晰度的直播流
            live_qn_id = live_quality_map[self.video_quality_choice.GetStringSelection()]

            if live_qn_id == 40000:
                live_qn_id = max(LiveInfo.live_quality_id_list)

            self.live_parser.get_live_stream(live_qn_id)

        # 直播类型视频跳转合成窗口
        if self.current_parse_type == ParseType.Live:
            if LiveInfo.status == LiveStatus.Not_Started.value:
                # 未开播，无法解析
                wx.MessageDialog(self, "直播间未开播\n\n当前直播间未开播，请开播后再进行解析", "警告", wx.ICON_WARNING).ShowModal()

                return

            # 获取选定清晰度的直播流
            _get_live_stram()

            live_recording_window = LiveRecordingWindow(self)
            live_recording_window.ShowModal()

            return
        
        video_quality_id = video_quality_map[self.video_quality_choice.GetStringSelection()]

        # 获取要下载的视频列表
        self.treelist.get_all_checked_item(video_quality_id)

        if not len(self.treelist.download_task_info_list):
            wx.MessageDialog(self, "下载失败\n\n请选择要下载的视频", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        if Config.Download.auto_popup_option_dialog:
            if self.onDownloadOptionEVT(0) == wx.ID_CANCEL:
                return
        
        # 显示加载窗口
        self.processing_window = ProcessingWindow(self)
        self.processing_window.Show()

        # 添加下载项目
        download_thread = Thread(target = worker)
        download_thread.start()
        
    def onOpenDownloadMgrEVT(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()

            if self.download_window_opened:
                pass
            else:
                self.download_window.CenterOnParent()

                self.download_window_opened = True

        self.download_window.SetFocus()
        self.download_window.onDownloadingPageBtnEVT()

    def setVideoQualityList(self):
        match self.current_parse_type:
            case ParseType.Video:
                video_quality_id_list = VideoInfo.video_quality_id_list
                video_quality_desc_list = VideoInfo.video_quality_desc_list

            case ParseType.Bangumi:
                video_quality_id_list = BangumiInfo.video_quality_id_list
                video_quality_desc_list = BangumiInfo.video_quality_desc_list

            case ParseType.Cheese:
                video_quality_id_list = CheeseInfo.video_quality_id_list
                video_quality_desc_list = CheeseInfo.video_quality_desc_list

        # 自动在最前添加自动选项
        video_quality_desc_list.insert(0, "自动")
        self.video_quality_choice.Set(video_quality_desc_list)

        if Config.Download.video_quality_id == VideoQualityID._Auto.value:
            index = 0

        else:
            if Config.Download.video_quality_id in video_quality_id_list:
                video_quality_id = Config.Download.video_quality_id
            else:
                video_quality_id = video_quality_id_list[0]

            index = video_quality_id_list.index(video_quality_id) + 1

        self.video_quality_choice.Select(index)

    def setLiveQualityList(self):
        live_quality_desc_list = LiveInfo.live_quality_desc_list

        live_quality_desc_list.insert(0, "自动")
        self.video_quality_choice.Set(live_quality_desc_list)

        self.video_quality_choice.Select(0)

    def onLoginEVT(self, event):
        def callback():
            self.init_user_info()

            self.init_menubar()

            # 安全关闭扫码登录窗口
            self.login_window.Close()
            self.login_window.Destroy()

        self.login_window = LoginWindow(self, callback)
        self.login_window.ShowModal()

    def onLogoutEVT(self, event):
        dlg = wx.MessageDialog(self, '退出登录\n\n是否要退出登录？', "警告", wx.ICON_WARNING | wx.YES_NO)
        
        if dlg.ShowModal() == wx.ID_YES:
            session = requests.sessions.Session()

            login = QRLogin(session)
            login.logout()

            self.face.Hide()
            self.uname_lab.SetLabel("未登录")

            self.userinfo_hbox.Layout()

    def onRefreshEVT(self, event):
        login = QRLogin(requests.Session())
        user_info = login.get_user_info(refresh = True)

        Config.User.face_url = user_info["face_url"]
        Config.User.username = user_info["username"]

        os.remove(Config.User.face_path)

        # 刷新用户信息后重新显示
        Thread(target = self.showUserInfoThread).start()

    def onShowUserMenuEVT(self, event):
        def _get_menu():
            context_menu = wx.Menu()

            context_menu.Append(self.ID_REFRESH, "刷新(&R)")
            context_menu.Append(self.ID_LOGOUT, "退出登录(&L)")

            return context_menu

        if Config.User.login:
            self.PopupMenu(_get_menu())
        else:
            self.onLoginEVT(0)

    def onLoadConverter(self, event):
        converter_window = ConverterWindow(self)
        converter_window.ShowModal()

    def onCutClipEVT(self, event):
        dlg = CutClipDialog(self)
        dlg.ShowModal()

    def onSettingEVT(self, event):
        setting_window = SettingWindow(self)
        setting_window.ShowModal()

    def onDebugEVT(self, event):
        shell = wx.py.shell.ShellFrame(self, -1, "调试")
        
        shell.CenterOnParent()
        shell.Show()

    def onChangeLogEVT(self, event):
        def worker():
            def show():
                dialog = ChangeLogDialog(self)
                dialog.ShowModal()

            if not Config.Temp.change_log:
                try:
                    UniversalTool.get_changelog()

                    wx.CallAfter(show)
                
                except Exception:
                    wx.MessageDialog(self, "获取更新日志失败\n\n当前无法获取更新日志，请稍候再试", "获取更新日志", wx.ICON_ERROR).ShowModal()

        Thread(target = worker).start()

    def onFeedBackEVT(self, event):
        webbrowser.open("https://github.com/ScottSloan/Bili23-Downloader/issues")

    def onCheckUpdateEVT(self, event):
        def worker():
            def show():
                update_window = UpdateWindow(self)
                update_window.ShowWindowModal()

            if not Config.Temp.update_json:
                try:
                    UniversalTool.get_update_json()
                    
                except Exception:
                    wx.MessageDialog(self, "检查更新失败\n\n当前无法检查更新，请稍候再试", "检查更新", wx.ICON_ERROR).ShowModal()
                    return
                
            if Config.Temp.update_json["version_code"] > Config.APP.version_code:
                wx.CallAfter(show)
            else:
                wx.MessageDialog(self, "当前没有可用的更新", "检查更新", wx.ICON_INFORMATION).ShowModal()

        Thread(target = worker).start()
    
    def onEpisodeOptionEVT(self, event):
        def _get_menu():
            context_menu = wx.Menu()

            single_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_SINGLE, "显示单个视频", kind = wx.ITEM_RADIO)
            in_section_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_IN_SECTION, "显示视频所在的列表", kind = wx.ITEM_RADIO)
            all_section_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_ALL_SECTIONS, "显示全部相关视频", kind = wx.ITEM_RADIO)

            show_episode_full_name = wx.MenuItem(context_menu, self.ID_EPISODE_FULL_NAME, "显示完整剧集名称", kind = wx.ITEM_CHECK)

            context_menu.Append(wx.NewIdRef(), "剧集列表显示设置")
            context_menu.AppendSeparator()
            context_menu.Append(single_menuitem)
            context_menu.Append(in_section_menuitem)
            context_menu.Append(all_section_menuitem)
            context_menu.AppendSeparator()
            context_menu.Append(show_episode_full_name)

            match EpisodeDisplayType(Config.Misc.episode_display_mode):
                case EpisodeDisplayType.Single:
                    single_menuitem.Check(True)

                case EpisodeDisplayType.In_Section:
                    in_section_menuitem.Check(True)

                case EpisodeDisplayType.All:
                    all_section_menuitem.Check(True)

            show_episode_full_name.Check(Config.Misc.show_episode_full_name)

            return context_menu
        
        self.PopupMenu(_get_menu())

    def onDownloadOptionEVT(self, event):
        def callback(index: int, enable: bool):
            self.video_quality_choice.SetSelection(index)
            self.video_quality_choice.Enable(enable)
            self.video_quality_lab.Enable(enable)
        
        match self.current_parse_type:
            case ParseType.Video:
                stream_type = VideoInfo.stream_type

            case ParseType.Bangumi:
                stream_type = BangumiInfo.stream_type

            case ParseType.Cheese:
                stream_type = CheeseInfo.stream_type

        dlg = OptionDialog(self, stream_type, callback)
        return dlg.ShowModal()

    def onEpisodeOptionMenuEVT(self, event):
        def _clear():
            self.treelist.init_list()
            self.type_lab.SetLabel("")

        match event.GetId():
            case self.ID_EPISODE_SINGLE:
                Config.Misc.episode_display_mode = EpisodeDisplayType.Single.value

            case self.ID_EPISODE_IN_SECTION:
                Config.Misc.episode_display_mode = EpisodeDisplayType.In_Section.value

            case self.ID_EPISODE_ALL_SECTIONS:
                Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

            case self.ID_EPISODE_FULL_NAME:
                Config.Misc.show_episode_full_name = not Config.Misc.show_episode_full_name

        _clear()

        match self.current_parse_type:
            case ParseType.Video:
                self.video_parser.parse_episodes()

            case ParseType.Bangumi:
                self.bangumi_parser.parse_episodes()

            case ParseType.Cheese:
                self.cheese_parser.parse_episodes()

        self.treelist.set_list()
        self.updateVideoCountLabel()
    
    def onParseErrorCallback(self):
        def worker():
            self._onLoading(False)

            dlg = wx.MessageDialog(self, f"解析失败\n\n错误码：{GlobalExceptionInfo.info.get('code')}\n描述：{GlobalExceptionInfo.info.get('message')}", "错误", wx.ICON_ERROR | wx.YES_NO)
            dlg.SetYesNoLabels("详细信息", "确定")

            if dlg.ShowModal() == wx.ID_YES:
                dlg = ErrorInfoDialog(self, GlobalExceptionInfo.info)
                dlg.ShowModal()

        wx.CallAfter(worker)

    def onEpisodeRightClickEVT(self, event):
        def _get_menu():
            context_menu = wx.Menu()

            view_cover_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_LIST_VIEW_COVER, "查看封面(&V)")
            copy_title_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_LIST_COPY_TITLE, "复制标题(&C)")
            copy_url_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_LIST_COPY_URL, "复制链接(&U)")
            edit_title_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_LIST_EDIT_TITLE, "修改标题(&E)")
            check_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_LIST_CHECK, "取消选择(&N)" if self.treelist.is_current_item_checked() else "选择(&S)")
            collapse_menuitem = wx.MenuItem(context_menu, self.ID_EPISODE_LIST_COLLAPSE, "展开(&X)" if self.treelist.is_current_item_collapsed() else "折叠(&O)")
            
            if self.treelist.is_current_item_node():
                view_cover_menuitem.Enable(False)
                copy_title_menuitem.Enable(False)
                copy_url_menuitem.Enable(False)
                edit_title_menuitem.Enable(False)
            else:
                collapse_menuitem.Enable(False)

            context_menu.Append(view_cover_menuitem)
            context_menu.AppendSeparator()
            context_menu.Append(copy_title_menuitem)
            context_menu.Append(copy_url_menuitem)
            context_menu.AppendSeparator()
            context_menu.Append(edit_title_menuitem)
            context_menu.AppendSeparator()
            context_menu.Append(check_menuitem)
            context_menu.Append(collapse_menuitem)

            return context_menu
        
        if self.treelist.GetSelection().IsOk():
            self.treelist.PopupMenu(_get_menu())

    def onEpisodeContextMenuEVT(self, event):
        def _view_cover():
            def _video():
                if "arc" in episode_info:
                    return episode_info["arc"]["pic"]
                else:
                    return VideoInfo.cover

            def _bangumi():
                return episode_info["cover"]

            def _cheese():
                return episode_info["cover"]

            def worker():
                def callback():
                    dlg = CoverViewerDialog(self, contents)
                    dlg.Show()

                contents = RequestTool.request_get(url).content

                wx.CallAfter(callback)

            cid = self.treelist.GetItemData(self.treelist.GetSelection()).cid
            episode_info = EpisodeInfo.cid_dict.get(cid)

            match self.current_parse_type:
                case ParseType.Video:
                    url = _video()

                case ParseType.Bangumi:
                    url = _bangumi()

                case ParseType.Cheese:
                    url = _cheese()

            Thread(target = worker).start()

        def _copy_title():
            text = self.treelist.GetItemText(self.treelist.GetSelection(), 1)

            wx.TheClipboard.SetData(wx.TextDataObject(text))

        def _copy_url():
            def _type_video():
                match VideoInfo.type:
                    case VideoType.Single:
                        return VideoInfo.url

                    case VideoType.Part:
                        return f"{VideoInfo.url}?p={episode_info['page']}"

                    case VideoType.Collection:
                        return f"https://www.bilibili.com/video/{episode_info['bvid']}"

            def _type_bangumi():
                return f"https://www.bilibili.com/bangumi/play/ep{episode_info['ep_id']}"

            def _type_live():
                return f"https://live.bilibili.com/{LiveInfo.room_id}"

            def _type_cheese():
                return f"https://www.bilibili.com/cheese/play/ep{episode_info['id']}"

            cid = self.treelist.GetItemData(self.treelist.GetSelection()).cid
            episode_info = EpisodeInfo.cid_dict.get(cid)

            match self.current_parse_type:
                case ParseType.Video:
                    url = _type_video()

                case ParseType.Bangumi:
                    url = _type_bangumi()

                case ParseType.Live:
                    url = _type_live()

                case ParseType.Cheese:
                    url = _type_cheese()
            
            wx.TheClipboard.SetData(wx.TextDataObject(url))

        def _edit_title():
            item = self.treelist.GetSelection()
            text = self.treelist.GetItemText(item, 1)

            dialog = EditTitleDialog(self, text)

            if dialog.ShowModal() == wx.ID_OK:
                title = dialog.title_box.GetValue()
                item_info: TreeListItemInfo = self.treelist.GetItemData(item)

                item_info.title = title

                self.treelist.SetItemText(item, 1, title)
                self.treelist.SetItemData(item, item_info)

                if self.current_parse_type == ParseType.Live:
                    LiveInfo.title = title

        match event.GetId():
            case self.ID_EPISODE_LIST_VIEW_COVER:
                _view_cover()

            case self.ID_EPISODE_LIST_COPY_TITLE:
                _copy_title()

            case self.ID_EPISODE_LIST_COPY_URL:
                _copy_url()

            case self.ID_EPISODE_LIST_EDIT_TITLE:
                _edit_title()

            case self.ID_EPISODE_LIST_CHECK:
                self.treelist.check_current_item()

            case self.ID_EPISODE_LIST_COLLAPSE:
                self.treelist.collapse_current_item()

    def onVideoDetailEVT(self, event):
        if self.current_parse_type != ParseType.Live:
            dialog = DetailDialog(self)

            dialog.set_page(self.current_parse_type)

            dialog.ShowModal()
        else:
            wx.MessageDialog(self, "暂不支持查看\n\n目前暂不支持查看直播的详细信息", "警告", wx.ICON_WARNING).ShowModal()

    def updateVideoCountLabel(self, checked: int = 0):
        if checked:
            _total = f"(共 {self.treelist._index} 个，已选择 {checked} 个)"
        else:
            _total = f"(共 {self.treelist._index} 个)"

        match self.current_parse_type:
            case ParseType.Video:
                _type = "投稿视频"

            case ParseType.Bangumi:
                _type = BangumiInfo.type_name

            case ParseType.Live:
                _type = "直播"
            
            case ParseType.Cheese:
                _type = "课程"
        
        self.type_lab.SetLabel(f"{_type} {_total}")
        self.detail_icon.Show(True)

        self.panel.Layout()

    def showEpisodeList(self):
        self.treelist.set_list()

        self.updateVideoCountLabel()

    def showUserInfoThread(self):
        def _process(image: wx.Image):
            width, height = image.GetSize()
            diameter = min(width, height)
            
            image = image.Scale(diameter, diameter, wx.IMAGE_QUALITY_HIGH)
            
            circle_image = wx.Image(diameter, diameter)
            circle_image.InitAlpha()
            
            for x in range(diameter):
                for y in range(diameter):
                    dist = ((x - diameter / 2) ** 2 + (y - diameter / 2) ** 2) ** 0.5
                    if dist <= diameter / 2:
                        circle_image.SetRGB(x, y, image.GetRed(x, y), image.GetGreen(x, y), image.GetBlue(x, y))
                        circle_image.SetAlpha(x, y, 255)
                    else:
                        circle_image.SetAlpha(x, y, 0)
            
            return circle_image

        # 显示用户头像及昵称
        scale_size = self.FromDIP((32, 32))

        image = wx.Image(UniversalTool.get_user_face(), wx.BITMAP_TYPE_JPEG).Scale(scale_size[0], scale_size[1], wx.IMAGE_QUALITY_HIGH)
        
        self.face.SetBitmap(_process(image).ConvertToBitmap())
        self.face.SetSize(scale_size)
        self.face.Show()
        
        self.uname_lab.SetLabel(Config.User.username)

        wx.CallAfter(self.userinfo_hbox.Layout)
        wx.CallAfter(self.frame_vbox.Layout)

    def showInfobarMessage(self, message: str, flag: int):
        wx.CallAfter(self.infobar.ShowMessage, message, flag)
    
    def _onLoading(self, state: bool):
        self.processing_icon.Show(state)

        self.url_box.Enable(not state)
        self.get_btn.Enable(not state)
        self.treelist.Enable(not state)

        if state:
            tip = "正在解析中..."
        else:
            tip = ""
            
        self.type_lab.SetLabel(tip)

        self.panel.Layout()
