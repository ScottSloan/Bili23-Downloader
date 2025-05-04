import re
import wx
import webbrowser
import wx.dataview

from utils.config import Config
from utils.tool_v2 import UniversalTool, RequestTool
from utils.auth.login import QRLogin
from utils.module.ffmpeg import FFmpeg

from utils.common.thread import Thread
from utils.common.icon_v3 import Icon, IconID
from utils.common.update import Update
from utils.common.enums import ParseStatus, ParseType, StatusCode, EpisodeDisplayType, LiveStatus, DownloadStatus, VideoQualityID, Platform
from utils.common.data_type import ParseCallback, TreeListItemInfo
from utils.common.exception import GlobalException, GlobalExceptionInfo
from utils.common.map import video_quality_map, live_quality_map

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.live import LiveInfo, LiveParser
from utils.parse.b23 import B23Parser
from utils.parse.activity import ActivityParser
from utils.parse.episode import EpisodeManager, EpisodeInfo

from gui.window.download_v3 import DownloadManagerWindow
from gui.window.settings import SettingWindow
from gui.window.debug import DebugWindow
from gui.window.login import LoginWindow

from gui.dialog.about import AboutWindow
from gui.dialog.changelog import ChangeLogDialog
from gui.dialog.update import UpdateWindow
from gui.dialog.converter import ConverterWindow
from gui.dialog.cut_clip import CutClipDialog
from gui.dialog.error import ErrorInfoDialog
from gui.dialog.detail import DetailDialog
from gui.dialog.edit_title import EditTitleDialog
from gui.dialog.cover import CoverViewerDialog
from gui.dialog.processing import ProcessingWindow
from gui.dialog.live import LiveRecordingWindow
from gui.dialog.download_option_v2 import DownloadOptionDialog
from gui.dialog.duplicate import DuplicateDialog

from gui.component.frame import Frame
from gui.component.panel import Panel
from gui.component.search_ctrl import SearchCtrl
from gui.component.tree_list import TreeListCtrl
from gui.component.button import Button
from gui.component.bitmap_button import BitmapButton
from gui.component.info_bar import InfoBar

class MainWindow(Frame):
    def __init__(self, parent):
        def set_window_size():
            match Platform(Config.Sys.platform):
                case Platform.Windows | Platform.macOS:
                    self.SetSize(self.FromDIP((800, 450)))

                case Platform.Linux:
                    self.SetSize(self.FromDIP((900, 550)))

        Frame.__init__(self, parent, Config.APP.name)

        set_window_size()

        self.get_sys_settings()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

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

        self.processing_icon = wx.StaticBitmap(self.panel, -1, Icon.get_icon_bitmap(IconID.LOADING_ICON), size = self.FromDIP((24, 24)))
        self.processing_icon.Hide()
        self.type_lab = wx.StaticText(self.panel, -1, "")
        self.detail_icon = wx.StaticBitmap(self.panel, -1, Icon.get_icon_bitmap(IconID.INFO_ICON), size = self.FromDIP((24, 24)))
        self.detail_icon.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.detail_icon.Hide()
        self.video_quality_lab = wx.StaticText(self.panel, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self.panel, -1)
        self.episode_option_btn = BitmapButton(self.panel, Icon.get_icon_bitmap(IconID.LIST_ICON))
        self.episode_option_btn.Enable(False)
        self.download_option_btn = BitmapButton(self.panel, Icon.get_icon_bitmap(IconID.SETTING_ICON))
        self.download_option_btn.Enable(False)

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.Add(self.processing_icon, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.detail_icon, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.AddStretchSpacer()
        info_hbox.Add(self.video_quality_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.video_quality_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.episode_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.download_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.episode_list = TreeListCtrl(self.panel, self.update_checked_count)

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

    def init_id(self):
        self.ID_REFRESH_MENU = wx.NewIdRef()
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

        self.ID_EPISODE_LIST_VIEW_COVER_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_COPY_TITLE_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_COPY_URL_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_EDIT_TITLE_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_CHECK_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_COLLAPSE_MENU = wx.NewIdRef()

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
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.url_box.Bind(wx.EVT_SEARCH, self.onGetEVT)
        self.get_btn.Bind(wx.EVT_BUTTON, self.onGetEVT)

        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadMgrEVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.onDownloadEVT)

        self.episode_option_btn.Bind(wx.EVT_BUTTON, self.onShowEpisodeOptionMenuEVT)
        self.download_option_btn.Bind(wx.EVT_BUTTON, self.onShowDownloadOptionDlgEVT)

        self.face_icon.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)
        self.uname_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)

        self.detail_icon.Bind(wx.EVT_LEFT_DOWN, self.onShowDetailInfoDlgEVT)

        self.episode_list.Bind(wx.dataview.EVT_TREELIST_ITEM_CONTEXT_MENU, self.onShowEpisodeListMenuEVT)
        self.episode_list.Bind(wx.EVT_MENU, self.onEpisodeListMenuEVT)

        self.Bind(wx.EVT_TIMER, self.read_clip_board, self.clipboard_timer)

    def init_utils(self):
        def start_thread():
            wx.CallAfter(self.check_ffmpeg_available)

            Thread(target = self.check_update).start()

        def init_timer():
            if Config.Basic.listen_clipboard:
                self.clipboard_timer.Start(1000)

        self.download_window = DownloadManagerWindow(self)

        self.current_parse_url = ""

        self.show_user_info()

        init_timer()

        start_thread()

    def onCloseEVT(self, event):
        if self.download_window.downloading_page.get_scroller_task_count([DownloadStatus.Downloading.value, DownloadStatus.Merging.value]):
            dlg = wx.MessageDialog(self, "是否退出程序\n\n当前有下载任务正在进行中，是否退出程序？\n\n程序将在下次启动时恢复下载进度。", "警告", style = wx.ICON_WARNING | wx.YES_NO)

            if dlg.ShowModal() == wx.ID_NO:
                return
            
        self.clipboard_timer.Stop()
        
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

            case self.ID_CONVERTER_MENU:
                ConverterWindow(self).ShowModal()

            case self.ID_CUT_CLIP_MENU:
                CutClipDialog(self).ShowModal()

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

        if not url:
            wx.MessageDialog(self, "解析失败\n\n链接不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        self.current_parse_url = url
        
        self.episode_list.init_list()
        
        self.set_parse_status(ParseStatus.Parsing.value)
        
        Thread(target = self.parse_url_thread, args = (url, )).start()

    def onOpenDownloadMgrEVT(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()
            self.download_window.CenterOnParent()
        
        elif self.download_window.IsIconized():
            if Config.Basic.auto_show_download_window:
                self.download_window.Iconize(False)
        
        if Config.Basic.auto_show_download_window:
            self.download_window.SetFocus()
            self.download_window.downloading_page_btn.onClickEVT(event)

    def onDownloadEVT(self, event):
        match self.current_parse_type:
            case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                def callback():
                    self.processing_window.Hide()
                    self.onOpenDownloadMgrEVT(event)

                if not self.episode_list.get_checked_item_count():
                    wx.MessageDialog(self, "下载失败\n\n请选择要下载的项目。", "警告", wx.ICON_WARNING).ShowModal()
                    return
                
                if Config.Basic.auto_popup_option_dialog:
                    if self.onShowDownloadOptionDlgEVT(event) != wx.ID_OK:
                        return
                
                self.episode_list.get_all_checked_item()

                duplicate_episode_list = self.download_window.find_duplicate_tasks(self.episode_list.download_task_info_list)

                if duplicate_episode_list:
                    if DuplicateDialog(self, duplicate_episode_list).ShowModal() != wx.ID_OK:
                        return

                self.processing_window = ProcessingWindow(self)
                self.processing_window.Show()
                
                Thread(target = self.download_window.add_to_download_list, args = (self.episode_list.download_task_info_list, callback, )).start()

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

    def onShowDetailInfoDlgEVT(self, event):
        match self.current_parse_type:
            case ParseType.Live:
                wx.MessageDialog(self, "暂不支持查看\n\n目前暂不支持查看直播的详细信息", "警告", wx.ICON_WARNING).ShowModal()

            case _:
                DetailDialog(self, self.current_parse_type).ShowModal()
    
    def onShowEpisodeListMenuEVT(self, event):
        menu = wx.Menu()

        view_cover_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_VIEW_COVER_MENU, "查看封面(&V)")
        copy_title_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_COPY_TITLE_MENU, "复制标题(&C)")
        copy_url_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_COPY_URL_MENU, "复制链接(&U)")
        edit_title_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_EDIT_TITLE_MENU, "修改标题(&E)")
        check_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_CHECK_MENU, "取消选择(&N)" if self.episode_list.is_current_item_checked() else "选择(&S)")
        collapse_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_COLLAPSE_MENU, "展开(&X)" if self.episode_list.is_current_item_collapsed() else "折叠(&O)")

        if self.episode_list.is_current_item_node():
            view_cover_menuitem.Enable(False)
            copy_title_menuitem.Enable(False)
            copy_url_menuitem.Enable(False)
            edit_title_menuitem.Enable(False)
        else:
            collapse_menuitem.Enable(False)

        menu.Append(view_cover_menuitem)
        menu.AppendSeparator()
        menu.Append(copy_title_menuitem)
        menu.Append(copy_url_menuitem)
        menu.AppendSeparator()
        menu.Append(edit_title_menuitem)
        menu.AppendSeparator()
        menu.Append(check_menuitem)
        menu.Append(collapse_menuitem)

        if self.episode_list.GetSelection().IsOk():
            self.episode_list.PopupMenu(menu)

    def onEpisodeListMenuEVT(self, event):
        match event.GetId():
            case self.ID_EPISODE_LIST_VIEW_COVER_MENU:
                def view_cover():
                    def worker():
                        def callback():
                            CoverViewerDialog(self, contents).Show()

                        contents = RequestTool.request_get(url).content
                        wx.CallAfter(callback)

                    cid = self.episode_list.GetItemData(self.episode_list.GetSelection()).cid
                    episode_info = EpisodeInfo.cid_dict.get(cid)

                    match self.current_parse_type:
                        case ParseType.Video:
                            if "arc" in episode_info:
                                url = episode_info["arc"]["pic"]
                            else:
                                url = VideoInfo.cover

                        case ParseType.Bangumi:
                            url = episode_info["cover"]

                        case ParseType.Cheese:
                            url = episode_info["cover"]

                    Thread(target = worker).start()

                view_cover()

            case self.ID_EPISODE_LIST_COPY_TITLE_MENU:
                def copy_title():
                    text = self.episode_list.GetItemText(self.episode_list.GetSelection(), 1)

                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                
                copy_title()

            case self.ID_EPISODE_LIST_COPY_URL_MENU:
                cid = self.episode_list.GetItemData(self.episode_list.GetSelection()).cid

                url = EpisodeManager.get_episode_url(cid, self.current_parse_type)

                wx.TheClipboard.SetData(wx.TextDataObject(url))

            case self.ID_EPISODE_LIST_EDIT_TITLE_MENU:
                def edit_title():
                    item = self.episode_list.GetSelection()
                    text = self.episode_list.GetItemText(item, 1)

                    dialog = EditTitleDialog(self, text)

                    if dialog.ShowModal() == wx.ID_OK:
                        title = dialog.title_box.GetValue()
                        item_info: TreeListItemInfo = self.episode_list.GetItemData(item)

                        item_info.title = title

                        self.episode_list.SetItemText(item, 1, title)
                        self.episode_list.SetItemData(item, item_info)

                        if self.current_parse_type == ParseType.Live:
                            LiveInfo.title = title

                edit_title()

            case self.ID_EPISODE_LIST_CHECK_MENU:
                self.episode_list.check_current_item()

            case self.ID_EPISODE_LIST_COLLAPSE_MENU:
                self.episode_list.collapse_current_item()

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
        def worker():
            def show():
                self.face_icon.Show()
                self.face_icon.SetBitmap(UniversalTool.get_user_round_face(image).ConvertToBitmap())
                self.uname_lab.SetLabel(Config.User.username)

                self.panel.Layout()

            scaled_size = self.FromDIP((32, 32))
            user_face = UniversalTool.get_user_face()

            image = wx.Image(user_face, wx.BITMAP_TYPE_JPEG).Scale(scaled_size[0], scaled_size[1], wx.IMAGE_QUALITY_HIGH)

            wx.CallAfter(show)

        if Config.Misc.show_user_info:
            if Config.User.login:
                Thread(target = worker).start()
        else:
            self.uname_lab.Hide()
            self.face_icon.Hide()
        
        self.panel.Layout()

    def check_ffmpeg_available(self):
        ffmpeg = FFmpeg()
        ffmpeg.check_available()

        if Config.FFmpeg.check_available and not Config.FFmpeg.available:
            dlg = wx.MessageDialog(self, "未检测到 FFmpeg\n\n未检测到 FFmpeg，无法进行视频合成、裁切和转换。\n\n请检查是否为 FFmpeg 创建环境变量或 FFmpeg 是否已在运行目录中。", "警告", wx.ICON_WARNING | wx.YES_NO)
            dlg.SetYesNoLabels("安装 FFmpeg", "忽略")

            if dlg.ShowModal() == wx.ID_YES:
                webbrowser.open("https://bili23.scott-sloan.cn/doc/install/ffmpeg.html")

    def check_update(self):
        if Config.Misc.auto_check_update:
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
            self.set_parse_status(ParseStatus.Finish.value)

            self.show_episode_list()

        self.current_parse_type = None
        
        match UniversalTool.re_find_string(r"cheese|av|BV|ep|ss|md|live|b23.tv|bili2233.cn|blackboard|festival", url):
            case "cheese":
                self.current_parse_type = ParseType.Cheese
                self.cheese_parser = CheeseParser(self.parse_callback)

                return_code = self.cheese_parser.parse_url(url)

                wx.CallAfter(self.set_video_quality_list)

            case "av" | "BV":
                self.current_parse_type = ParseType.Video
                self.video_parser = VideoParser(self.parse_callback)

                return_code = self.video_parser.parse_url(url)

                wx.CallAfter(self.set_video_quality_list)

            case "ep" | "ss" | "md":
                self.current_parse_type = ParseType.Bangumi
                self.bangumi_parser = BangumiParser(self.parse_callback)

                return_code = self.bangumi_parser.parse_url(url)

                wx.CallAfter(self.set_video_quality_list)

            case "live":
                self.current_parse_type = ParseType.Live
                self.live_parser = LiveParser(self.parse_callback)

                return_code = self.live_parser.parse_url(url)

                wx.CallAfter(self.set_live_quality_list)

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
        def worker():
            dlg = wx.MessageDialog(self, f"解析失败\n\n错误码：{GlobalExceptionInfo.info.get('code')}\n描述：{GlobalExceptionInfo.info.get('message')}", "错误", wx.ICON_ERROR | wx.YES_NO)
            dlg.SetYesNoLabels("详细信息", "确定")

            if dlg.ShowModal() == wx.ID_YES:
                ErrorInfoDialog(self, GlobalExceptionInfo.info).ShowModal()

        self.set_parse_status(ParseStatus.Error)

        wx.CallAfter(worker)

    def onRedirectCallback(self, url: str):
        Thread(target = self.parse_url_thread, args = (url, )).start()

    def set_parse_status(self, status: int):
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

        match ParseStatus(status):
            
            case ParseStatus.Parsing:
                self.processing_icon.Show(True)

                self.type_lab.SetLabel("正在解析中")

                self.detail_icon.Hide()

                set_enable_status(False)
                self.video_quality_choice.Clear()
            
            case ParseStatus.Finish:
                self.processing_icon.Hide()

                self.type_lab.SetLabel("")

                self.detail_icon.Show()

                set_enable_status(True)
                set_download_btn_label()

            case ParseStatus.Error:
                self.processing_icon.Hide()

                self.type_lab.SetLabel("")

                self.detail_icon.Hide()

                self.url_box.Enable(True)
                self.get_btn.Enable(True)
                self.episode_list.Enable(True)

        self.panel.Layout()
    
    def show_info_bar_message(self, message: str, flag: int):
        wx.CallAfter(self.infobar.ShowMessage, message, flag)
    
    def get_sys_settings(self):
        Config.Sys.dark_mode = False if Config.Sys.platform == Platform.Windows.value else wx.SystemSettings.GetAppearance().IsDark()
        Config.Sys.dpi_scale_factor = self.GetDPIScaleFactor()

    def read_clip_board(self, event):
        def is_valid_url(url: str):
            return re.findall(r"https:\/\/[a-zA-Z0-9-]+\.bilibili\.com", url)

        text = wx.TextDataObject()

        if wx.TheClipboard.Open():
            if wx.TheClipboard.GetData(text):
                url: str = text.GetText()
                if is_valid_url(url):
                    if url != self.current_parse_url:
                        self.url_box.SetValue(url)

                        wx.CallAfter(self.onGetEVT, event)

            wx.TheClipboard.Close()

    @property
    def parse_callback(self):
        callback = ParseCallback()
        callback.onError = self.onErrorCallback
        callback.onRedirect = self.onRedirectCallback

        return callback
    
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