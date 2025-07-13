import wx
import webbrowser

from utils.config import Config, app_config_group
from utils.auth.login import QRLogin

from utils.module.ffmpeg_v2 import FFmpeg
from utils.module.clipboard import ClipBoard
from utils.module.cover import CoverUtils
from utils.module.face import FaceUtils

from utils.common.thread import Thread
from utils.common.icon_v4 import Icon, IconID
from utils.common.update import Update
from utils.common.enums import ParseStatus, ParseType, StatusCode, EpisodeDisplayType, LiveStatus, VideoQualityID, Platform, ProcessingType, ExitOption
from utils.common.data_type import ParseCallback, TreeListCallback, Callback
from utils.common.exception import GlobalException, GlobalExceptionInfo
from utils.common.map import video_quality_map, live_quality_map
from utils.common.re_utils import REUtils

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.live import LiveInfo, LiveParser
from utils.parse.b23 import B23Parser
from utils.parse.activity import ActivityParser
from utils.parse.episode_v2 import Episode

from gui.window.download_v3 import DownloadManagerWindow
from gui.window.settings import SettingWindow
from gui.window.debug import DebugWindow
from gui.window.login import LoginWindow
from gui.window.format_factory import FormatFactoryWindow

from gui.dialog.about import AboutWindow
from gui.dialog.misc.changelog import ChangeLogDialog
from gui.dialog.misc.update import UpdateWindow
from gui.dialog.error import ErrorInfoDialog
from gui.dialog.detail import DetailDialog
from gui.dialog.setting.edit_title import EditTitleDialog
from gui.dialog.processing import ProcessingWindow
from gui.dialog.live import LiveRecordingWindow
from gui.dialog.download_option_v3 import DownloadOptionDialog
from gui.dialog.confirm.duplicate import DuplicateDialog
from gui.dialog.graph import GraphWindow

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel
from gui.component.text_ctrl.search_ctrl import SearchCtrl
from gui.component.tree_list_v2 import TreeListCtrl
from gui.component.button.button import Button
from gui.component.button.bitmap_button import BitmapButton
from gui.component.info_bar import InfoBar
from gui.component.taskbar_icon import TaskBarIcon
from gui.component.button.flat_button import FlatButton

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

    def init_UI(self):
        class callback(TreeListCallback):
            @staticmethod
            def onUpdateCheckedItemCount(count: int):
                self.onUpdateCheckedItemCount(count)
            
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
        self.video_quality_lab = wx.StaticText(self.panel, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self.panel, -1)
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
        info_hbox.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.episode_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.download_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.episode_list = TreeListCtrl(self.panel, callback)

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
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.url_box.Bind(wx.EVT_SEARCH, self.onGetEVT)
        self.get_btn.Bind(wx.EVT_BUTTON, self.onGetEVT)

        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadMgrEVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.onDownloadEVT)

        self.episode_option_btn.Bind(wx.EVT_BUTTON, self.onShowEpisodeOptionMenuEVT)
        self.download_option_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadOptionDlgEVT)

        self.face_icon.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)
        self.uname_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)

        self.detail_btn.onClickCustomEVT = self.onShowDetailInfoDlgEVT
        self.graph_btn.onClickCustomEVT = self.onShowGraphEVT

        self.episode_list.Bind(wx.EVT_MENU, self.onEpisodeListContextMenuEVT)

        self.Bind(wx.EVT_TIMER, self.read_clipboard, self.clipboard_timer)

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
        
        self.current_parse_url = ""
        self.error_url_list = []
        self.status = ParseStatus.Finish.value

        init_timer()

        start_thread()

    def onCloseEVT(self, event):
        def save_config():
            if Config.Basic.remember_window_status:
                Config.Basic.window_pos = list(self.GetPosition())
                Config.Basic.window_size = list(self.GetSize())
                Config.Basic.window_maximized = self.IsMaximized()

                Config.save_config_group(Config, app_config_group, Config.APP.app_config_path)

        def show_dialog():
            dlg = wx.MessageDialog(self, "退出程序\n\n确定要退出程序吗？\n下次将不再显示此对话框。", "提示", style = wx.ICON_INFORMATION | wx.YES_NO | wx.CANCEL)
            dlg.SetYesNoCancelLabels("最小化到托盘", "退出程序", "取消")

            flag = dlg.ShowModal()

            match flag:
                case wx.ID_YES:
                    Config.Basic.exit_option = ExitOption.TaskIcon.value

                case wx.ID_NO:
                    Config.Basic.exit_option = ExitOption.Exit.value

            Config.Basic.show_exit_dialog = False

            Config.save_config_group(Config, app_config_group, Config.APP.app_config_path)

            return flag
                
        if Config.Basic.show_exit_dialog:
            if show_dialog() == wx.ID_CANCEL:
                return
            
        if Config.Basic.exit_option == ExitOption.TaskIcon.value:
            self.Hide()
            return
            
        self.clipboard_timer.Stop()

        self.taskbar_icon.Destroy()

        save_config()
        
        event.Skip()

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
                self.show_login_window()

            case self.ID_LOGOUT_MENU:
                dlg = wx.MessageDialog(self, '退出登录\n\n是否要退出登录？', "警告", wx.ICON_WARNING | wx.YES_NO)

                if dlg.ShowModal() == wx.ID_YES:
                    QRLogin().logout()

                    self.show_user_info()

            case self.ID_REFRESH_MENU:
                def worker():
                    QRLogin().refresh()

                    self.show_user_info()

                Thread(target = worker).start()

            case self.ID_DEBUG_MENU:
                DebugWindow(self).Show()

            case self.ID_FORMAT_FACTORY_MENU:
                FormatFactoryWindow(self).Show()

            case self.ID_SETTINGS_MENU:
                SettingWindow(self).ShowModal()

            case self.ID_CHECK_UPDATE_MENU:
                def check_update_thread():
                    def callback():
                        UpdateWindow(self).ShowModal()

                    Update.get_update_json()

                    if Config.Temp.update_json:
                        if Config.Temp.update_json["version_code"] > Config.APP.version_code:
                            wx.CallAfter(callback)
                        else:
                            wx.CallAfter(wx.MessageDialog(self, "当前没有可用的更新。", "检查更新", wx.ICON_INFORMATION).ShowModal)
                    else:
                        wx.CallAfter(wx.MessageDialog(self, "检查更新失败\n\n当前无法检查更新，请稍候再试。", "检查更新", wx.ICON_ERROR).ShowModal)

                Thread(target = check_update_thread).start()

            case self.ID_CHANGELOG_MENU:
                def changelog_thread():
                    def callback():
                        ChangeLogDialog(self).ShowModal()

                    Update.get_changelog()

                    if Config.Temp.changelog:
                        wx.CallAfter(callback)
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
        self.current_parse_url = self.url_box.GetValue()

        if not url:
            self.status = ParseStatus.Error
            wx.MessageDialog(self, "解析失败\n\n链接不能为空", "警告", wx.ICON_WARNING).ShowModal()

            return
                
        self.set_parse_status(ParseStatus.Parsing)

        self.episode_list.init_episode_list()
        
        Thread(target = self.parse_url_thread, args = (url, )).start()

        self.processing_window.ShowModal()

    def onOpenDownloadMgrEVT(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()
            self.download_window.CenterOnParent()
        
        elif self.download_window.IsIconized():
            if Config.Basic.auto_show_download_window:
                self.download_window.Iconize(False)
        
        if Config.Basic.auto_show_download_window:
            self.download_window.downloading_page_btn.onClickEVT(event)
            self.download_window.Raise()

    def onDownloadEVT(self, event):
        match self.current_parse_type:
            case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                def callback():
                    self.processing_window.Close()
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

                self.processing_window = ProcessingWindow(self, ProcessingType.Normal)
                self.processing_window.ShowModal()

            case ParseType.Live:
                if LiveInfo.status == LiveStatus.Not_Started.value:
                    wx.MessageDialog(self, "直播间未开播\n\n当前直播间未开播，请开播后再进行解析", "警告", wx.ICON_WARNING).ShowModal()
                    return
                
                self.live_parser.get_live_stream(self.live_quality_id)
                
                LiveRecordingWindow(self).ShowModal()

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
        def callback(index: int, enable: bool):
            self.video_quality_choice.SetSelection(index)
            self.video_quality_choice.Enable(enable)
            self.video_quality_lab.Enable(enable)

        return DownloadOptionDialog(self, callback).ShowModal()

    def onShowUserMenuEVT(self, event):
        if Config.User.login:
            menu = wx.Menu()

            menu.Append(self.ID_REFRESH_MENU, "刷新(&R)")
            menu.Append(self.ID_LOGOUT_MENU, "注销(&L)")

            self.PopupMenu(menu)
        else:
            self.show_login_window()

    def onShowDetailInfoDlgEVT(self):
        match self.current_parse_type:
            case ParseType.Live:
                wx.MessageDialog(self, "暂不支持查看\n\n目前暂不支持查看直播的详细信息", "警告", wx.ICON_WARNING).ShowModal()

            case _:
                DetailDialog(self, self.current_parse_type).ShowModal()
    
    def onShowGraphEVT(self):
        GraphWindow(self).Show()

    def onEpisodeListContextMenuEVT(self, event):
        match event.GetId():
            case self.episode_list.ID_EPISODE_LIST_VIEW_COVER_MENU:
                item_data = self.episode_list.GetItemData(self.episode_list.GetSelection())

                if item_data.cover_url:
                    CoverUtils.view_cover(self, item_data.cover_url)
                
            case self.episode_list.ID_EPISODE_LIST_COPY_TITLE_MENU:
                text = self.episode_list.GetItemText(self.episode_list.GetSelection(), 1)

                ClipBoard.Write(text)

            case self.episode_list.ID_EPISODE_LIST_COPY_URL_MENU:
                item_data = self.episode_list.GetItemData(self.episode_list.GetSelection())

                url = Episode.Utils.get_share_url(item_data)

                ClipBoard.Write(url)

            case self.episode_list.ID_EPISODE_LIST_EDIT_TITLE_MENU:
                def edit_title():
                    item = self.episode_list.GetSelection()

                    dialog = EditTitleDialog(self, self.episode_list.GetItemText(item, 1))

                    if dialog.ShowModal() == wx.ID_OK:
                        title = dialog.title_box.GetValue()

                        self.episode_list.SetItemTitle(item, title)

                        if self.current_parse_type == ParseType.Live:
                            LiveInfo.title = title

                edit_title()

            case self.episode_list.ID_EPISODE_LIST_CHECK_MENU:
                self.episode_list.CheckCurrentItem()

            case self.episode_list.ID_EPISODE_LIST_COLLAPSE_MENU:
                self.episode_list.CollapseCurrentItem()

    def onUpdateCheckedItemCount(self, count: int):        
        if count:
            label = f"(共 {self.episode_list.count} 个，已选择 {count} 个)"
        else:
            label = f"(共 {self.episode_list.count} 个)"

        match self.current_parse_type:
            case ParseType.Video:
                if VideoInfo.is_interactive:
                    type = "互动视频"
                else:
                    type = "投稿视频"

            case ParseType.Bangumi:
                type = BangumiInfo.type_name

            case ParseType.Live:
                type = "直播"

            case ParseType.Cheese:
                type = "课程"
        
        self.type_lab.SetLabel(f"{type} {label}")

        self.panel.Layout()

    def set_video_quality_list(self):
        def get_video_quality_list():
            match self.current_parse_type:
                case ParseType.Video:
                    video_quality_id_list = VideoInfo.video_quality_id_list.copy()
                    video_quality_desc_list = VideoInfo.video_quality_desc_list.copy()
                
                case ParseType.Bangumi:
                    video_quality_id_list = BangumiInfo.video_quality_id_list.copy()
                    video_quality_desc_list = BangumiInfo.video_quality_desc_list.copy()
                
                case ParseType.Cheese:
                    video_quality_id_list = CheeseInfo.video_quality_id_list.copy()
                    video_quality_desc_list = CheeseInfo.video_quality_desc_list.copy()

            video_quality_id_list.insert(0, VideoQualityID._Auto.value)
            video_quality_desc_list.insert(0, "自动")

            return video_quality_id_list, video_quality_desc_list
            
        (video_quality_id_list, video_quality_desc_list) = get_video_quality_list()

        self.video_quality_choice.Set(video_quality_desc_list)

        if Config.Download.video_quality_id in video_quality_id_list:
            self.video_quality_choice.Select(video_quality_id_list.index(Config.Download.video_quality_id))
        else:
            self.video_quality_choice.Select(1)
    
    def set_live_quality_list(self):
        live_quality_desc_list = LiveInfo.live_quality_desc_list

        live_quality_desc_list.insert(0, "自动")

        self.video_quality_choice.Set(live_quality_desc_list)
        self.video_quality_choice.Select(0)

    def show_user_info(self):
        def show_face():
            self.face_icon.Show()
            self.face_icon.SetBitmap(FaceUtils.crop_round_face_bmp(image))
            self.uname_lab.SetLabel(Config.User.username)

            self.panel.Layout()

        def hide_face():
            self.uname_lab.SetLabel("未登录")
            self.face_icon.Hide()

            self.panel.Layout()

        wx.CallAfter(hide_face)

        if Config.Misc.show_user_info:
            if Config.User.login:
                image = FaceUtils.get_scaled_face(self.FromDIP((32, 32)))

                wx.CallAfter(show_face)

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

    def check_update(self):
        Update.get_update_json()

        if Config.Temp.update_json:
            if Config.Temp.update_json["version_code"] > Config.APP.version_code:
                self.show_info_bar_message("检查更新：有新的更新可用。", wx.ICON_INFORMATION)
        else:
            self.show_info_bar_message("检查更新：当前无法检查更新，请稍候再试。", wx.ICON_ERROR)

    def show_login_window(self):
        def callback():
            self.init_menubar()

            self.show_user_info()

        login_window = LoginWindow(self, callback)
        login_window.ShowModal()

    def parse_url_thread(self, url: str):
        def worker():
            self.set_parse_status(ParseStatus.Finish)

            match self.current_parse_type:
                case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                    self.set_video_quality_list()                        

                case ParseType.Live:
                    self.set_live_quality_list()

            self.show_episode_list()
        
        class Callback(ParseCallback):
            @staticmethod
            def onError():
                self.onErrorCallback()
            
            @staticmethod
            def onBangumi(url: str):
                self.onBangumiCallback(url)

            @staticmethod
            def onInteractVideo():
                self.onInteractVideoCallback()

            @staticmethod
            def onUpdateInteractVideo(title: str):
                self.processing_window.onUpdateNode(title)

        match REUtils.find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival", url):
            case "cheese":
                self.current_parse_type = ParseType.Cheese
                self.cheese_parser = CheeseParser(Callback)

                return_code = self.cheese_parser.parse_url(url)

            case "av" | "BV":
                self.current_parse_type = ParseType.Video
                self.video_parser = VideoParser(Callback)

                return_code = self.video_parser.parse_url(url)

            case "ep" | "ss" | "md":
                self.current_parse_type = ParseType.Bangumi
                self.bangumi_parser = BangumiParser(Callback)

                return_code = self.bangumi_parser.parse_url(url)

            case "live":
                self.current_parse_type = ParseType.Live
                self.live_parser = LiveParser(Callback)

                return_code = self.live_parser.parse_url(url)

            case "b23.tv" | "bili2233.cn":
                self.b23_parser = B23Parser(Callback)

                return_code = self.b23_parser.parse_url(url)

            case "blackboard" | "festival":
                self.activity_parser = ActivityParser(Callback)

                return_code = self.activity_parser.parse_url(url)
            
            case _:
                self.current_parse_type = None
                raise GlobalException(code = StatusCode.URL.value, callback = self.onErrorCallback)
        
        if return_code == StatusCode.Success.value:
            self.CallAfter(worker)
    
    def show_episode_list(self):
        self.episode_list.show_episode_list()

        if Config.Misc.auto_check_episode_item or self.episode_list.count == 1:
            self.episode_list.CheckAllItems()

        self.onUpdateCheckedItemCount(self.episode_list.GetCheckedItemCount())

    def onErrorCallback(self):
        def worker():
            self.set_parse_status(ParseStatus.Error)

            dlg = wx.MessageDialog(self, f"解析失败\n\n错误码：{GlobalExceptionInfo.info.get('code')}\n描述：{GlobalExceptionInfo.info.get('message')}", "错误", wx.ICON_ERROR | wx.YES_NO)
            dlg.SetYesNoLabels("详细信息", "确定")

            if dlg.ShowModal() == wx.ID_YES:
                ErrorInfoDialog(self, GlobalExceptionInfo.info).ShowModal()

        self.error_url_list.append(self.current_parse_url)

        self.CallAfter(worker)

    def onBangumiCallback(self, url: str):
        Thread(target = self.parse_url_thread, args = (url, )).start()

    def set_parse_status(self, status: ParseStatus):
        def set_enable_status(enable: bool):
            self.url_box.Enable(enable)
            self.get_btn.Enable(enable)
            self.episode_list.Enable(enable)
            self.download_btn.Enable(enable)
            self.episode_option_btn.Enable(enable)
            self.download_option_btn.Enable(enable)
            self.video_quality_choice.Enable(enable)
        
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
                self.video_quality_choice.Clear()

                self.processing_window = ProcessingWindow(self, ProcessingType.Parse)
            
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
    
    def get_sys_settings(self):
        Config.Sys.dark_mode = False if Config.Sys.platform == Platform.Windows.value else wx.SystemSettings.GetAppearance().IsDark()
        Config.Sys.dpi_scale_factor = self.GetDPIScaleFactor()

        for key in ["danmaku", "subtitle"]:
            if Config.Basic.ass_style.get(key).get("font_name") == "default":
                Config.Basic.ass_style[key]["font_name"] = self.GetFont().GetFaceName()

    def read_clipboard(self, event):
        def is_valid_url(url: str):
            if url:
                if url.startswith(("http", "https")):
                    if REUtils.find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival", url):
                        return url != self.current_parse_url and url not in self.error_url_list

        if self.status == ParseStatus.Parsing or not self.IsShown():
            return
        
        url: str = ClipBoard.Read()

        if is_valid_url(url):
            self.url_box.SetValue(url)

            wx.CallAfter(self.onGetEVT, event)

    def onInteractVideoCallback(self):
        def worker():
            self.processing_window.change_type(ProcessingType.Interact)

        wx.CallAfter(worker)

    def CallAfter(self, func):
        def worker():
            self.processing_window.Close()

            func()

        wx.CallAfter(worker)

    @property
    def video_quality_id(self):
        return video_quality_map.get(self.video_quality_choice.GetStringSelection())
    
    @property
    def live_quality_id(self):
        return live_quality_map.get(self.video_quality_choice.GetStringSelection())
    
    @property
    def stream_type(self):
        match self.current_parse_type:
            case ParseType.Video:
                return VideoInfo.stream_type
            
            case ParseType.Bangumi:
                return BangumiInfo.stream_type
            
            case ParseType.Cheese:
                return CheeseInfo.stream_type