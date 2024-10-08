import wx
import wx.py

from utils.config import Config, Download, conf, Audio
from utils.video import VideoInfo, VideoParser
from utils.bangumi import BangumiInfo, BangumiParser
from utils.activity import ActivityInfo, ActivityParser
from utils.tools import *
from utils.login import QRLogin
from utils.download import DownloaderInfo
from utils.thread import Thread
from utils.cookie import CookieUtils

from gui.templates import Frame, TreeListCtrl, InfoBar
from gui.about import AboutWindow
from gui.processing import ProcessingWindow
from gui.download import DownloadWindow, DownloadInfo
from gui.update import UpdateWindow
from gui.login import LoginWindow
from gui.settings import SettingWindow
from gui.converter import ConverterWindow

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
        # （macOS）获取系统是否处于深色模式
        if Config.Sys.platform == "darwin":
            Config.Sys.dark_mode = wx.SystemSettings.GetAppearance().IsDark()

        self.init_ids()

        self.infobar = InfoBar(self.panel)

        url_hbox = wx.BoxSizer(wx.HORIZONTAL)

        url_lab = wx.StaticText(self.panel, -1, "地址")
        self.url_box = wx.TextCtrl(self.panel, -1, style = wx.TE_PROCESS_ENTER)
        self.get_btn = wx.Button(self.panel, -1, "Get")

        url_hbox.Add(url_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        url_hbox.Add(self.url_box, 1, wx.EXPAND | wx.ALL & (~wx.LEFT), 10)
        url_hbox.Add(self.get_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        resolution_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.type_lab = wx.StaticText(self.panel, -1, "")
        resolution_lab = wx.StaticText(self.panel, -1, "清晰度")
        self.resolution_choice = wx.Choice(self.panel, -1)

        self.audio_btn = wx.Button(self.panel, -1, "...", size = (self.resolution_choice.GetSize()[1], self.resolution_choice.GetSize()[1]))

        resolution_hbox.Add(self.type_lab, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        resolution_hbox.AddStretchSpacer()
        resolution_hbox.Add(resolution_lab, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        resolution_hbox.Add(self.resolution_choice, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)
        resolution_hbox.Add(self.audio_btn, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)

        self.treelist = TreeListCtrl(self.panel)
        self.treelist.SetSize(self.FromDIP((800, 260)))

        self.download_mgr_btn = wx.Button(self.panel, -1, "下载管理", size = self.getButtonSize())
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = self.getButtonSize())
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
        vbox.Add(resolution_hbox, 0, wx.EXPAND)
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
        if Config.User.login:
            thread = Thread(target = self.showUserInfoThread)
            thread.daemon = True

            thread.start()
        else:
            self.face.Hide()

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
        self.audio_btn.Bind(wx.EVT_BUTTON, self.onAudioDetail)

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
        self.video_parser = VideoParser(self.onError)
        self.bangumi_parser = BangumiParser(self.onError)
        self.activity_parser = ActivityParser(self.onError)

        self.download_window = DownloadWindow(self)

        self.download_window_opened = False
        self.parse_ready = False

        utils_thread = Thread(target = self.utilsThread)
        utils_thread.daemon = True

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

        self.ID_AUDIO_HIRES = wx.NewIdRef()
        self.ID_AUDIO_DOLBY = wx.NewIdRef()
        self.ID_AUDIO_192K = wx.NewIdRef()
        self.ID_AUDIO_132K = wx.NewIdRef()
        self.ID_AUDIO_64K = wx.NewIdRef()
        self.ID_AUDIO_ONLY = wx.NewIdRef()

    def utilsThread(self):
        info = DownloaderInfo()
        tasks = info.read_info()

        if len(tasks):
            self.onLoadDownloadProgress()

        # 检查更新
        self.checkUpdateUtils()

        # 检查风控状态
        self.checkCookieUtils()

    def onClose(self, event):
        if not DownloadInfo.no_task:
            dlg = wx.MessageDialog(self, "是否退出程序\n\n当前有下载任务正在进行中，是否继续退出？", "警告", style = wx.ICON_WARNING | wx.YES_NO)

            if dlg.ShowModal() == wx.ID_NO:
                return

        event.Skip()

    def onAbout(self, event):
        about_window = AboutWindow(self)
        about_window.ShowModal()

    def onGet(self, event):
        url = self.url_box.GetValue()
        self.clearTreeList()

        self.processing_window = ProcessingWindow(self)
        self.processing_window.Show()

        self.parse_thread = Thread(target = self.parseThread, args = (url, ))
        self.parse_thread.setDaemon(True)

        self.parse_thread.start()

        self.parse_ready = True

    def parseThread(self, url: str):
        Download.download_list.clear()

        match find_str("av|BV|ep|ss|md|b23.tv|blackboard|festival", url):
            case "av" | "BV":
                self.video_parser.parse_url(url)
                wx.CallAfter(self.setVideoList)

                wx.CallAfter(self.setResolutionList, VideoInfo)

            case "ep" | "ss" | "md":
                self.bangumi_parser.parse_url(url)
                wx.CallAfter(self.setBangumiList)

                wx.CallAfter(self.setResolutionList, BangumiInfo)

            case "b23.tv":
                new_url = process_shorklink(url)

                self.startNewParseThread((new_url,))

                # 抛出异常，终止线程运行
                # 此处不使用 stop 方法

                raise Exception

            case "blackboard" | "festival":
                self.activity_parser.parse_url(url)

                self.startNewParseThread((ActivityInfo.new_url,))

                raise Exception

            case _:
                self.onError(100)

        wx.CallAfter(self.onGetFinished)

    def onGetFinished(self):
        self.processing_window.Hide()

        self.download_btn.Enable(True)

        self.treelist.SetFocus()

    def onDownload(self, event):
        resolution = resolution_map[self.resolution_choice.GetStringSelection()]

        self.treelist.get_all_selected_item(resolution)

        if not len(Download.download_list):
            self.infobar.ShowMessage("下载失败：请选择要下载的视频", flags = wx.ICON_ERROR)
            return
        
        self.onOpenDownloadMgr(0)
        self.download_window.add_download_item()

    def onOpenDownloadMgr(self, event):
        if not self.download_window.IsShown():
            self.download_window.Show()

            if self.download_window_opened:
                self.download_window.SetPosition(Config.Temp.download_window_pos)
            else:
                self.download_window.CenterOnParent()

                self.download_window_opened = True

        self.download_window.SetFocus()

    def clearTreeList(self):
        wx.CallAfter(self.treelist.init_list)

        self.resolution_choice.Clear()

        self.type_lab.SetLabel("")

    def setResolutionList(self, info: VideoInfo | BangumiInfo):
        # 显示可用清晰度
        resolution_desc = info.resolution_desc

        # 自动在最前添加自动选项
        resolution_desc.insert(0, "自动")

        self.resolution_choice.Set(resolution_desc)
        
        info.resolution = Config.Download.resolution if Config.Download.resolution in info.resolution_id else info.resolution_id[1]

        if info.resolution == 200:
            index = 0
        else:
            index = info.resolution_id.index(info.resolution) + 1

        self.resolution_choice.Select(index)

        Download.current_type = info

    def setVideoList(self):
        self.treelist.set_video_list()

        count = len(self.treelist.all_list_items) - len(self.treelist.parent_items)
        
        self.type_lab.SetLabel("视频 (共 %d 个)" % count)
    
    def setBangumiList(self):
        self.treelist.set_bangumi_list()

        count = len(self.treelist.all_list_items) - len(self.treelist.parent_items)

        self.type_lab.SetLabel("{} (共 {} 个)".format(BangumiInfo.type, count))

    def onLoadDownloadProgress(self):
        self.showInfobarMessage("下载管理：已恢复中断的下载进度", flag = wx.ICON_INFORMATION)

    def onError(self, err_code):
        match err_code:
            case 100:
                self.infobar.ShowMessage("解析失败：不受支持的链接", flags = wx.ICON_ERROR)
            
            case 101:
                self.infobar.ShowMessage("解析失败：视频不存在", flags = wx.ICON_ERROR)

            case 102:
                self.infobar.ShowMessage("解析失败：无法获取视频信息，请登录后再试", flags = wx.ICON_ERROR)

        self.processing_window.Hide()
        self.download_btn.Enable(False)

        wx.CallAfter(self.SetFocus)
        self.parse_thread.stop()

        self.parse_ready = False

    def onLogin(self, event):
        login_window = LoginWindow(self)
        login_window.ShowModal()

    def onLogout(self, event):
        dlg = wx.MessageDialog(self, f'确认注销登录\n\n是否要注销用户 "{Config.User.uname}"？', "注销", wx.ICON_WARNING | wx.YES_NO)
        
        if dlg.ShowModal() == wx.ID_YES:
            login = QRLogin()
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
        converter_window.Show()

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

    def onAudioDetail(self, event):
        if not self.parse_ready:
            return
        
        self.showAudioQualityMenu()

    def onChangeAudioQuality(self, event):
        match event.GetId():
            case self.ID_AUDIO_HIRES:
                Audio.audio_quality = 30251

            case self.ID_AUDIO_DOLBY:
                Audio.audio_quality = 30250

            case self.ID_AUDIO_192K:
                Audio.audio_quality = 30280

            case self.ID_AUDIO_132K:
                Audio.audio_quality = 30232

            case self.ID_AUDIO_64K:
                Audio.audio_quality = 30216

            case self.ID_AUDIO_ONLY:
                if Audio.audio_only:
                    Audio.audio_only = False
                else:
                    Audio.audio_only = True

    def showUserInfoThread(self):
        # 显示用户头像及昵称
        scale_size = self.FromDIP((32, 32))

        image = wx.Image(get_user_face(), wx.BITMAP_TYPE_JPEG).Scale(scale_size[0], scale_size[1], wx.IMAGE_QUALITY_HIGH)
        
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
                check_update()

                if Config.Temp.update_json["version_code"] > Config.APP.version_code:
                    self.showInfobarMessage("检查更新：有新的更新可用", wx.ICON_INFORMATION)
            except:
                self.showInfobarMessage("检查更新：当前无法检查更新，请稍候再试", wx.ICON_ERROR)
                
    def checkUpdateManuallyThread(self):
        if not Config.Temp.update_json:
            try:
                check_update()
            except:
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
        menu = wx.Menu()
        menu.Append(-1, "音质")
        menu.AppendSeparator()

        if Audio.q_hires:
            menuitem_hires = menu.Append(self.ID_AUDIO_HIRES, "Hi-Res 无损", kind = wx.ITEM_RADIO)
            menuitem_hires.Check(True if Audio.audio_quality == 30250 else False)

        if Audio.q_dolby:
            menuitem_dolby = menu.Append(self.ID_AUDIO_DOLBY, "杜比全景声", kind = wx.ITEM_RADIO)
            menuitem_dolby.Check(True if Audio.audio_quality == 30250 else False)

        menuitem_192k = menu.Append(self.ID_AUDIO_192K, "192K", kind = wx.ITEM_RADIO)
        menuitem_132k = menu.Append(self.ID_AUDIO_132K, "132K", kind = wx.ITEM_RADIO)
        menuitem_64k = menu.Append(self.ID_AUDIO_64K, "64K", kind = wx.ITEM_RADIO)

        menuitem_192k.Check(True if Audio.audio_quality == 30280 else False)
        menuitem_132k.Check(True if Audio.audio_quality == 30232 else False)
        menuitem_64k.Check(True if Audio.audio_quality == 30216 else False)

        menu.AppendSeparator()

        menuitem_audio_only = menu.Append(self.ID_AUDIO_ONLY, "仅下载音频", kind = wx.ITEM_CHECK)
        menuitem_audio_only.Check(True if Audio.audio_only else False)

        self.PopupMenu(menu)

    def showInfobarMessage(self, message, flag):
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
        self.parse_thread = Thread(target = self.parseThread, args = args)
        self.parse_thread.setDaemon(True)

        self.parse_thread.start()

    def setMainWindowSize(self):
        # 解决 Linux 上 UI 太小的问题
        match Config.Sys.platform:
            case "windows" | "darwin":
                self.SetSize(self.FromDIP((800, 450)))
            case "linux":
                self.SetClientSize(self.FromDIP((880, 450)))

    def getButtonSize(self):
        # 解决 Linux macOS 按钮太小对的问题
        match Config.Sys.platform:
            case "windows":
                size = self.FromDIP((100, 30))
            case "linux" | "darwin":
                size = self.FromDIP((120, 40))

        return size