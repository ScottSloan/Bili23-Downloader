import wx
import os
import time
import wx.py
import requests
from typing import Optional

from utils.config import Config, Download, Audio, conf
from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.festival import FestivalInfo, FestivalParser
from utils.parse.live import LiveInfo, LiveParser

from utils.login import QRLogin
from utils.thread import Thread
from utils.tool_v2 import RequestTool, UniversalTool
from utils.error import ErrorCallback, ErrorCode
from utils.mapping import video_quality_mapping, live_quality_mapping

from gui.templates import Frame, TreeListCtrl, InfoBar
from gui.dialog.about import AboutWindow
from gui.dialog.processing import ProcessingWindow
from gui.download_v2 import DownloadManagerWindow
from gui.dialog.update import UpdateWindow
from gui.login import LoginWindow
from gui.settings import SettingWindow
from gui.dialog.converter import ConverterWindow
from gui.dialog.live import LiveRecordingWindow

class MainWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, Config.APP.name)

        self.init_UI()

        self.init_utils()

        self.setMainWindowSize()

        self.Bind_EVT()

        self.CenterOnParent()

        self.onCheckFFmpeg()

        self.init_user_info()
    
    def init_UI(self):
        def _dark_mode():
            if Config.Sys.platform != "windows":
                Config.Sys.dark_mode = wx.SystemSettings.GetAppearance().IsDark()

        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize
                
        _dark_mode()

        # 避免出现 iCCP sRGB 警告
        wx.Image.SetDefaultLoadFlags(0)

        self.init_ids()

        self.infobar = InfoBar(self.panel)

        url_hbox = wx.BoxSizer(wx.HORIZONTAL)

        url_lab = wx.StaticText(self.panel, -1, "地址")
        self.url_box = wx.TextCtrl(self.panel, -1, style = wx.TE_PROCESS_ENTER)
        self.get_btn = wx.Button(self.panel, -1, "Get")

        url_hbox.Add(url_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        url_hbox.Add(self.url_box, 1, wx.EXPAND | wx.ALL & (~wx.LEFT), 10)
        url_hbox.Add(self.get_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        video_info_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.type_lab = wx.StaticText(self.panel, -1, "")
        video_quality_lab = wx.StaticText(self.panel, -1, "清晰度")
        self.video_quality_choice = wx.Choice(self.panel, -1)

        self.audio_btn = wx.Button(self.panel, -1, "...", size = (self.video_quality_choice.GetSize()[1], self.video_quality_choice.GetSize()[1]))

        video_info_hbox.Add(self.type_lab, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        video_info_hbox.AddStretchSpacer()
        video_info_hbox.Add(video_quality_lab, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        video_info_hbox.Add(self.video_quality_choice, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)
        video_info_hbox.Add(self.audio_btn, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)

        self.treelist = TreeListCtrl(self.panel)
        self.treelist.SetSize(self.FromDIP((800, 260)))

        self.download_mgr_btn = wx.Button(self.panel, -1, "下载管理", size = _get_scale_size((100, 30)))
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = _get_scale_size((100, 30)))
        self.download_btn.Enable(False)
        
        self.face = wx.StaticBitmap(self.panel, -1, size = self.FromDIP((32, 32)))
        self.face.Cursor = wx.Cursor(wx.CURSOR_HAND)
        self.uname_lab = wx.StaticText(self.panel, -1, "登录", style = wx.ST_ELLIPSIZE_END)
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
    
    def init_menubar(self):
        menu_bar = wx.MenuBar()
        self.help_menu = wx.Menu()
        self.tool_menu = wx.Menu()
        
        menu_bar.Append(self.tool_menu, "工具(&T)")
        menu_bar.Append(self.help_menu, "帮助(&H)")

        if not Config.User.login:
            self.tool_menu.Append(self.ID_LOGIN, "登录(&L)")

        if Config.Misc.debug:
            self.tool_menu.Append(self.ID_DEBUG, "调试(&D)")

        self.tool_menu.Append(self.ID_CONVERTER, "格式转换(&F)")
        self.tool_menu.AppendSeparator()
        self.tool_menu.Append(self.ID_SETTINGS, "设置(&S)")

        self.help_menu.Append(self.ID_CHECK_UPDATE, "检查更新(&U)")
        self.help_menu.AppendSeparator()
        self.help_menu.Append(self.ID_HELP, "使用帮助(&C)")
        self.help_menu.Append(self.ID_ABOUT, "关于(&A)")

        self.SetMenuBar(menu_bar)

    def init_user_info(self):
        # 如果用户已登录，则获取用户信息
        if Config.User.login:
            thread = Thread(target = self.showUserInfoThread)
            thread.daemon = True

            thread.start()
        else:
            self.face.Hide()

        # 调整用户信息 UI
        wx.CallAfter(self.userinfo_hbox.Layout)
        wx.CallAfter(self.frame_vbox.Layout)

    def get_user_context_menu(self):
        menu = wx.Menu()

        menu.Append(self.ID_REFRESH, "刷新")
        menu.Append(self.ID_LOGOUT, "注销")

        return menu
    
    def Bind_EVT(self):
        self.url_box.Bind(wx.EVT_TEXT_ENTER, self.onGet)
        self.get_btn.Bind(wx.EVT_BUTTON, self.onGet)
        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadMgr)
        self.download_btn.Bind(wx.EVT_BUTTON, self.onDownload)
        self.audio_btn.Bind(wx.EVT_BUTTON, self.onShowAudioMenu)

        self.face.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenu)
        self.uname_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenu)

        self.Bind(wx.EVT_MENU, self.onLogin, id = self.ID_LOGIN)
        self.Bind(wx.EVT_MENU, self.onLoadShell, id = self.ID_DEBUG)
        self.Bind(wx.EVT_MENU, self.onLoadSetting, id = self.ID_SETTINGS)
        self.Bind(wx.EVT_MENU, self.onLoadConverter, id = self.ID_CONVERTER)
        self.Bind(wx.EVT_MENU, self.onAbout, id = self.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.onCheckUpdate, id = self.ID_CHECK_UPDATE)
        self.Bind(wx.EVT_MENU, self.onLogout, id = self.ID_LOGOUT)
        self.Bind(wx.EVT_MENU, self.onRefresh, id = self.ID_REFRESH)
        self.Bind(wx.EVT_MENU, self.onHelp, id = self.ID_HELP)

        self.Bind(wx.EVT_MENU, self.onChangeAudioQuality, id = self.ID_AUDIO_HIRES)
        self.Bind(wx.EVT_MENU, self.onChangeAudioQuality, id = self.ID_AUDIO_DOLBY)
        self.Bind(wx.EVT_MENU, self.onChangeAudioQuality, id = self.ID_AUDIO_192K)
        self.Bind(wx.EVT_MENU, self.onChangeAudioQuality, id = self.ID_AUDIO_132K)
        self.Bind(wx.EVT_MENU, self.onChangeAudioQuality, id = self.ID_AUDIO_64K)
        self.Bind(wx.EVT_MENU, self.onChangeAudioQuality, id = self.ID_AUDIO_ONLY)

        self.Bind(wx.EVT_CLOSE, self.onClose)

    def init_utils(self):
        ErrorCallback.onError = self.onError
        ErrorCallback.onRedirect = self.onRedirect
        
        self.video_parser = VideoParser()
        self.bangumi_parser = BangumiParser()
        self.live_parser = LiveParser()
        self.activity_parser = FestivalParser(self.onError)

        self.download_window = DownloadManagerWindow(self)

        self.download_window_opened = False
        # 解析完成标识符
        self.parse_finish_flag = False

        utils_thread = Thread(target = self.utilsThread, daemon = True)

        utils_thread.start()

    def init_ids(self):
        self.ID_LOGIN = wx.NewIdRef()
        self.ID_DEBUG = wx.NewIdRef()
        self.ID_CONVERTER = wx.NewIdRef()
        self.ID_SETTINGS = wx.NewIdRef()
        self.ID_HELP = wx.NewIdRef()
        self.ID_CHECK_UPDATE = wx.NewIdRef()
        self.ID_CHANGE_LOG = wx.NewIdRef()
        self.ID_ABOUT = wx.NewIdRef()

        self.ID_LOGOUT = wx.NewIdRef()
        self.ID_REFRESH = wx.NewIdRef()

        self.ID_AUDIO_AUTO = wx.NewIdRef()
        self.ID_AUDIO_HIRES = wx.NewIdRef()
        self.ID_AUDIO_DOLBY = wx.NewIdRef()
        self.ID_AUDIO_192K = wx.NewIdRef()
        self.ID_AUDIO_132K = wx.NewIdRef()
        self.ID_AUDIO_64K = wx.NewIdRef()
        self.ID_AUDIO_ONLY = wx.NewIdRef()
        self.ID_AUDIO_NONE = wx.NewIdRef()

    def utilsThread(self):
        # 检查更新
        self.checkUpdateUtils()

        # 检查风控状态
        self.checkCookieUtils()

    def onClose(self, event):
        if self.download_window.get_download_task_count([Config.Type.DOWNLOAD_STATUS_WAITING, Config.Type.DOWNLOAD_STATUS_PAUSE, Config.Type.DOWNLOAD_STATUS_DOWNLOADING, Config.Type.DOWNLOAD_STATUS_MERGING]):
            dlg = wx.MessageDialog(self, "是否退出程序\n\n当前有下载任务正在进行中，是否退出程序？\n\n程序将在下次启动时恢复下载进度。", "警告", style = wx.ICON_WARNING | wx.YES_NO)

            if dlg.ShowModal() == wx.ID_NO:
                return

        event.Skip()

    def onAbout(self, event):
        about_window = AboutWindow(self)
        about_window.ShowModal()

    def onGet(self, event):
        url = self.url_box.GetValue()
        self.clearTreeList()

        # 显示加载窗口
        self.processing_window = ProcessingWindow(self)
        self.processing_window.Show()

        # 开启解析线程
        self.onRedirect(url)

        self.parse_finish_flag = False

    def parseThread(self, url: str):
        continue_to_parse = True

        match UniversalTool.re_find_string(r"av|BV|ep|ss|md|live|b23.tv|blackboard|festival", url):
            case "av" | "BV":
                # 用户投稿视频
                self.current_parse_type = Config.Type.VIDEO

                continue_to_parse = self.video_parser.parse_url(url)

                if continue_to_parse:
                    # 当存在跳转链接时，使用新的跳转链接重新开始解析，原先解析线程不继续执行
                    wx.CallAfter(self.setVideoList)

                    wx.CallAfter(self.setVideoQualityList)

            case "ep" | "ss" | "md":
                # 番组
                self.current_parse_type = Config.Type.BANGUMI

                self.bangumi_parser.parse_url(url)
                
                wx.CallAfter(self.setBangumiList)

                wx.CallAfter(self.setVideoQualityList)

            case "live":
                # 直播
                self.current_parse_type = Config.Type.LIVE

                self.live_parser.parse_url(url)

                wx.CallAfter(self.setLiveList)

                wx.CallAfter(self.setLiveQualityList)

            case "b23.tv":
                # 短链接
                new_url = RequestTool.get_real_url(url)

                self.parseThread(new_url)

                return

            case "blackboard" | "festival":
                # 活动页链接
                self.activity_parser.parse_url(url)

                self.parseThread(FestivalInfo.url)

                return

            case _:
                self.onError(ErrorCode.Invalid_URL)

        if continue_to_parse:
            wx.CallAfter(self.onGetFinished)

    def onRedirect(self, url: str):
        self.parse_thread = Thread(target = self.parseThread, args = (url, ))
        self.parse_thread.start()

    def onGetFinished(self):
        if self.current_parse_type != Config.Type.LIVE:
            self.parse_finish_flag = True

        self.processing_window.Hide()

        self.download_btn.Enable(True)

        self.treelist.SetFocus()

    def onDownload(self, event):
        def add_download_task_callback():
            if hasattr(self, "processing_window"):
                # 关闭加载窗口
                self.processing_window.Hide()

                # 显示下载窗口
                self.onOpenDownloadMgr(0)

        def worker():
            time.sleep(0.1)

            wx.CallAfter(self.download_window.add_download_task_panel, self.treelist.download_task_info_list, add_download_task_callback, True)

        # 直播类型视频跳转合成窗口
        if self.current_parse_type == Config.Type.LIVE:
            if LiveInfo.status == Config.Type.LIVE_STATUS_0:
                # 未开播，无法解析
                wx.MessageDialog(self, "直播间未开播\n\n当前直播间未开播，请开播后再进行解析", "警告", wx.ICON_WARNING).ShowModal()

                return

            # 获取选定清晰度的直播流
            self.get_live_stream()

            live_recording_window = LiveRecordingWindow(self)
            live_recording_window.ShowModal()

            return
        
        video_quality_id = video_quality_mapping[self.video_quality_choice.GetStringSelection()]

        # 获取要下载的视频列表
        self.treelist.get_all_selected_item(video_quality_id)

        if not len(self.treelist.download_task_info_list):
            self.infobar.ShowMessage("下载失败：请选择要下载的视频", flags = wx.ICON_ERROR)
            return
        
        # 显示加载窗口
        self.processing_window = ProcessingWindow(self)
        self.processing_window.Show()

        # 添加下载项目
        download_thread = Thread(target = worker)
        download_thread.start()
        
    def onOpenDownloadMgr(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()

            if self.download_window_opened:
                pass
            else:
                self.download_window.CenterOnParent()

                self.download_window_opened = True

        self.download_window.SetFocus()

    def clearTreeList(self):
        wx.CallAfter(self.treelist.init_list)

        self.video_quality_choice.Clear()

        self.type_lab.SetLabel("")

    def setVideoQualityList(self):
        if self.current_parse_type == Config.Type.VIDEO:
            video_quality_id_list = VideoInfo.video_quality_id_list
            video_quality_desc_list = VideoInfo.video_quality_desc_list
            Download.current_parse_type = Config.Type.VIDEO
        else:
            video_quality_id_list = BangumiInfo.video_quality_id_list
            video_quality_desc_list = BangumiInfo.video_quality_desc_list
            Download.current_parse_type = Config.Type.BANGUMI

        # 自动在最前添加自动选项
        video_quality_desc_list.insert(0, "自动")
        self.video_quality_choice.Set(video_quality_desc_list)

        if Config.Download.video_quality_id == 200:
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

    def setVideoList(self):
        self.treelist.set_video_list()

        count = len(self.treelist.all_list_items) - len(self.treelist.parent_items)
        
        self.type_lab.SetLabel("视频 (共 %d 个)" % count)
    
    def setBangumiList(self):
        self.treelist.set_bangumi_list()

        count = len(self.treelist.all_list_items) - len(self.treelist.parent_items)

        self.type_lab.SetLabel("{} (共 {} 个)".format(BangumiInfo.type_name, count))

    def setLiveList(self):
        self.treelist.set_live_list()

        self.type_lab.SetLabel("直播")

    def get_live_stream(self):
        # 获取选定清晰度的直播流
        live_qn_id = live_quality_mapping[self.video_quality_choice.GetStringSelection()]

        if live_qn_id == 40000:
            live_qn_id = max(LiveInfo.live_quality_id_list)

        self.live_parser.get_live_stream(live_qn_id)

    def onLoadDownloadProgress(self):
        self.showInfobarMessage("下载管理：已恢复中断的下载进度", flag = wx.ICON_INFORMATION)

    def onError(self, error_code: int, error_info: Optional[str] = None):
        # 匹配不同错误码
        match error_code:
            case ErrorCode.Invalid_URL:
                msg = "解析失败：不受支持的链接"
            
            case ErrorCode.Parse_Error:
                msg = f"解析失败：{error_info}"

            case ErrorCode.VIP_Required:
                msg = "解析失败：此视频为大会员专享，请确保已经登录大会员账号后再试"
            
                if self.current_parse_type == Config.Type.BANGUMI:
                    if BangumiInfo.payment and Config.User.login:
                        msg = "解析失败：此视频需要付费购买，请确保已经购买此视频后再试"
            
            case ErrorCode.Request_Error:
                msg = f"解析失败：{error_info}"
            
            case ErrorCode.Unknown_Error:
                msg = "解析失败：发生未知错误"
        
        self.infobar.ShowMessage(msg, flags = wx.ICON_ERROR)

        self.processing_window.Hide()
        self.download_btn.Enable(False)

        wx.CallAfter(self.SetFocus)

        self.parse_finish_flag = False

        raise Exception

    def onLogin(self, event):
        self.login_window = LoginWindow(self)
        self.login_window.ShowModal()

    def onLogout(self, event):
        dlg = wx.MessageDialog(self, f'确认注销登录\n\n是否要注销用户 "{Config.User.uname}"？', "注销", wx.ICON_WARNING | wx.YES_NO)
        
        if dlg.ShowModal() == wx.ID_YES:
            session = requests.sessions.Session()

            login = QRLogin(session)
            login.logout()

            self.face.Hide()
            self.uname_lab.SetLabel("登录")

            self.userinfo_hbox.Layout()

            self.infobar.ShowMessage("提示：您已注销登录", flags = wx.ICON_INFORMATION)

    def onRefresh(self, event):
        login = QRLogin()
        user_info = login.get_user_info(True)

        Config.User.face = user_info["face"]
        Config.User.uname = user_info["uname"]

        conf.save_all_user_config()

        os.remove(Config.User.face_path)

        # 刷新用户信息后重新显示
        thread = Thread(target = self.showUserInfoThread)
        thread.daemon = True

        thread.start()

    def onShowUserMenu(self, event):
        if Config.User.login:
            self.PopupMenu(self.get_user_context_menu())
        else:
            self.onLogin(0)

    def onLoadConverter(self, event):
        converter_window = ConverterWindow(self)
        converter_window.ShowModal()

    def onLoadSetting(self, event):
        setting_window = SettingWindow(self)
        setting_window.ShowModal()

    def onLoadShell(self, event):
        shell = wx.py.shell.ShellFrame(self, -1, "调试")
        
        shell.CenterOnParent()
        shell.Show()

    def onHelp(self, event):
        import webbrowser

        webbrowser.open("https://scott-sloan.cn/archives/12/")

    def onCheckUpdate(self, event):
        wx.CallAfter(self.checkUpdateManuallyThread)

    def onShowAudioMenu(self, event):
        # 只有解析成功才会显示音频菜单
        if self.parse_finish_flag:
            self.showAudioQualityMenu()

    def onChangeAudioQuality(self, event):
        match event.GetId():
            case self.ID_AUDIO_AUTO:
                Audio.audio_quality_id = 30300

            case self.ID_AUDIO_HIRES:
                Audio.audio_quality_id = 30251

            case self.ID_AUDIO_DOLBY:
                Audio.audio_quality_id = 30250

            case self.ID_AUDIO_192K:
                Audio.audio_quality_id = 30280

            case self.ID_AUDIO_132K:
                Audio.audio_quality_id = 30232

            case self.ID_AUDIO_64K:
                Audio.audio_quality_id = 30216

            case self.ID_AUDIO_ONLY:
                if Audio.audio_only:
                    Audio.audio_only = False
                else:
                    Audio.audio_only = True

    def showUserInfoThread(self):
        # 显示用户头像及昵称
        scale_size = self.FromDIP((32, 32))

        image = wx.Image(UniversalTool.get_user_face(), wx.BITMAP_TYPE_JPEG).Scale(scale_size[0], scale_size[1], wx.IMAGE_QUALITY_HIGH)
        
        self.face.SetBitmap(self.convertToCircle(image).ConvertToBitmap())
        self.face.SetSize(scale_size)
        self.face.Show()
        
        self.uname_lab.SetLabel(Config.User.uname)

        wx.CallAfter(self.userinfo_hbox.Layout)
        wx.CallAfter(self.frame_vbox.Layout)

    def checkUpdateUtils(self):
        # 检查更新
        if Config.Misc.check_update:
            try:
                UniversalTool.get_update_json()

                if Config.Temp.update_json["version_code"] > Config.APP.version_code:
                    self.showInfobarMessage("检查更新：有新的更新可用", wx.ICON_INFORMATION)

            except Exception:
                self.showInfobarMessage("检查更新：当前无法检查更新，请稍候再试", wx.ICON_ERROR)
                
    def checkUpdateManuallyThread(self):
        if not Config.Temp.update_json:
            try:
                UniversalTool.get_update_json()
                
            except Exception:
                wx.MessageDialog(self, "检查更新失败\n\n当前无法检查更新，请稍候再试", "检查更新", wx.ICON_ERROR).ShowModal()
                return
            
        if Config.Temp.update_json["version_code"] > Config.APP.version_code:
            wx.CallAfter(self.showUpdateWindow)
        else:
            wx.MessageDialog(self, "当前没有可用的更新", "检查更新", wx.ICON_INFORMATION).ShowModal()

    def checkCookieUtils(self):
        pass
        # if Config.User.login:
        #     # 判断用户是否登录，进行风控检查
        #     refresh = CookieUtils.checkCookieInfo()

        #     if refresh:
        #        self.showInfobarMessage("帐号安全：检测到当前帐号已被风控，请重新登录", flag = wx.ICON_WARNING)

    def showUpdateWindow(self):
        update_window = UpdateWindow(self)
        update_window.ShowWindowModal()

    def showAudioQualityMenu(self):
        # 显示音质菜单
        menu = wx.Menu()
        menu.Append(-1, "音质")
        menu.AppendSeparator()

        audio_none = False

        menuitem_auto = menu.Append(self.ID_AUDIO_AUTO, "自动", kind = wx.ITEM_RADIO)
        menuitem_auto.Check(True if Audio.audio_quality_id == 30300 else False)

        if Audio.q_hires:
            menuitem_hires = menu.Append(self.ID_AUDIO_HIRES, "Hi-Res 无损", kind = wx.ITEM_RADIO)
            menuitem_hires.Check(True if Audio.audio_quality_id == 30251 else False)

        if Audio.q_dolby:
            menuitem_dolby = menu.Append(self.ID_AUDIO_DOLBY, "杜比全景声", kind = wx.ITEM_RADIO)
            menuitem_dolby.Check(True if Audio.audio_quality_id == 30250 else False)

        if Audio.q_192k:
            menuitem_192k = menu.Append(self.ID_AUDIO_192K, "192K", kind = wx.ITEM_RADIO)
            menuitem_192k.Check(True if Audio.audio_quality_id == 30280 else False)

        if Audio.q_132k:
            menuitem_132k = menu.Append(self.ID_AUDIO_132K, "132K", kind = wx.ITEM_RADIO)
            menuitem_132k.Check(True if Audio.audio_quality_id == 30232 else False)

        if Audio.q_64k:
            menuitem_64k = menu.Append(self.ID_AUDIO_64K, "64K", kind = wx.ITEM_RADIO)
            menuitem_64k.Check(True if Audio.audio_quality_id == 30216 else False)

        if not Audio.q_64k and not Audio.q_132k and not Audio.q_192k:
            menuitem_none = menu.Append(self.ID_AUDIO_NONE, "无音轨")
            menuitem_none.Enable(False)

            audio_none = True

        menu.AppendSeparator()

        menuitem_audio_only = menu.Append(self.ID_AUDIO_ONLY, "仅下载音频", kind = wx.ITEM_CHECK)
        menuitem_audio_only.Check(True if Audio.audio_only else False)

        if audio_none:
            menuitem_auto.Hide(True)
            menuitem_audio_only.Enable(False)

        self.PopupMenu(menu)

    def showInfobarMessage(self, message: str, flag: int):
        wx.CallAfter(self.infobar.ShowMessage, message, flag)

    def onCheckFFmpeg(self):
        if not Config.FFmpeg.available:
            dlg = wx.MessageDialog(self, "未检测到 FFmpeg\n\n未检测到 FFmpeg，视频合成不可用。\n\n若您已确认安装 FFmpeg，请检查（二者其一即可）：\n1.为 FFmpeg 设置环境变量\n2.将 FFmpeg 放置到程序运行目录下\n\n点击下方安装 FFmpeg 按钮，将打开 FFmpeg 安装教程，请按照教程安装。", "警告", wx.ICON_WARNING | wx.YES_NO)
            dlg.SetYesNoLabels("安装 FFmpeg", "忽略")

            if dlg.ShowModal() == wx.ID_YES:
                import webbrowser

                webbrowser.open("https://scott-sloan.cn/archives/120/")
    
    def convertToCircle(self, image: wx.Image):
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
    
    def startNewParseThread(self, *args):
        self.parse_thread = Thread(target = self.parseThread, args = args, daemon = True)
        self.parse_thread.start()

    def onLoginSuccess(self):
        self.init_user_info()
        
        self.infobar.ShowMessage("提示：登录成功", flags = wx.ICON_INFORMATION)

        self.init_menubar()

        # 安全关闭扫码登录窗口
        self.login_window.Close()
        self.login_window.Destroy()

    def setMainWindowSize(self):
        # 解决 Linux 上 UI 太小的问题
        match Config.Sys.platform:
            case "windows" | "darwin":
                self.SetSize(self.FromDIP((800, 450)))
            case "linux":
                self.SetClientSize(self.FromDIP((880, 450)))
