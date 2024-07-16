import wx
import wx.py
from io import BytesIO

from utils.config import Config, Download, conf, Audio
from utils.video import VideoInfo, VideoParser
from utils.bangumi import BangumiInfo, BangumiParser
from utils.activity import ActivityInfo, ActivityParser
from utils.tools import *
from utils.thread import Thread
from utils.login import QRLogin
from utils.download import DownloaderInfo

from .templates import Frame, TreeListCtrl, InfoBar
from .about import AboutWindow
from .processing import ProcessingWindow
from .download import DownloadWindow, DownloadInfo
from .update import UpdateWindow
from .login import LoginWindow
from .settings import SettingWindow

class MainWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, Config.APP.name)

        self.init_utils()

        self.init_UI()

        self.SetSize(self.FromDIP((800, 450)))

        self.Bind_EVT()

        self.CenterOnScreen()

        self.onCheckFFmpeg()

        self.init_user_info()
    
    def init_UI(self):
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

        self.audio_btn = wx.Button(self.panel, -1, "...", size = self.FromDIP((24, 24)))

        resolution_hbox.Add(self.type_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        resolution_hbox.AddStretchSpacer()
        resolution_hbox.Add(resolution_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        resolution_hbox.Add(self.resolution_choice, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)
        resolution_hbox.Add(self.audio_btn, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)

        self.treelist = TreeListCtrl(self.panel)
        self.treelist.SetSize(self.FromDIP((800, 260)))

        self.download_mgr_btn = wx.Button(self.panel, -1, "下载管理", size = self.FromDIP((100, 30)))
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = self.FromDIP((100, 30)))
        self.download_btn.Enable(False)
        
        self.face = wx.StaticBitmap(self.panel, -1, size = self.FromDIP((32, 32)))
        self.face.Cursor = wx.Cursor(wx.CURSOR_HAND)
        self.uname_lab = wx.StaticText(self.panel, -1, "登录")
        self.uname_lab.Cursor = wx.Cursor(wx.CURSOR_HAND)

        self.userinfo_hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.userinfo_hbox.Add(self.face, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, 10)
        self.userinfo_hbox.Add(self.uname_lab, 0, wx.LEFT | wx.ALIGN_CENTER, 10)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)

        bottom_hbox.Add(self.userinfo_hbox, 0, wx.EXPAND | wx.CENTER)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        bottom_hbox.Add(self.download_btn, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(10)
        vbox.Add(url_hbox, 0, wx.EXPAND)
        vbox.Add(resolution_hbox, 0, wx.EXPAND)
        vbox.Add(self.treelist, 1, wx.ALL | wx.EXPAND, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)
        vbox.AddSpacer(10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(10)
        hbox.Add(vbox, 1, wx.EXPAND)
        hbox.AddSpacer(10)

        self.frame_vbox = wx.BoxSizer(wx.VERTICAL)
        self.frame_vbox.Add(self.infobar, 1, wx.EXPAND)
        self.frame_vbox.Add(hbox, 1, wx.EXPAND)

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

            if not Config.Misc.debug:
                self.tool_menu.AppendSeparator()

        if Config.Misc.debug:
            self.tool_menu.Append(self.ID_DEBUG, "调试(&D)")
            self.tool_menu.AppendSeparator()

        self.tool_menu.Append(self.ID_SETTINGS, "设置(&S)")

        self.help_menu.Append(self.ID_CHECK_UPDATE, "检查更新(&U)")
        self.help_menu.AppendSeparator()
        self.help_menu.Append(self.ID_HELP, "使用帮助(&C)")
        self.help_menu.Append(self.ID_ABOUT, "关于(&A)")

        self.SetMenuBar(menu_bar)

    def init_user_info(self):
        if Config.User.login:
            Thread(target = self.showUserInfoThread).start()
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

        self.Bind(wx.EVT_CLOSE, self.onClose)

    def init_utils(self):
        self.ID_LOGIN = wx.NewIdRef()
        self.ID_DEBUG = wx.NewIdRef()
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

        self.video_parser = VideoParser(self.onError)
        self.bangumi_parser = BangumiParser(self.onError)
        self.activity_parser = ActivityParser(self.onError)

        self.download_window = DownloadWindow(self)

        self.download_window_opened = False
        self.parse_ready = False

        utils_thread = Thread(target = self.utilsThread)
        utils_thread.daemon = True

        utils_thread.start()

    def utilsThread(self):
        info = DownloaderInfo()
        tasks = info.read_info()

        if len(tasks):
            self.onLoadDownloadProgress()

        self.checkUpdateUtils()

    def onClose(self, event):
        if not DownloadInfo.no_task:
            dlg = wx.MessageDialog(self, "是否退出程序\n\n当前有下载任务正在进行中，是否继续退出？\n\n程序将自动保存下载进度，可随时恢复下载。", "警告", style = wx.ICON_WARNING | wx.YES_NO)

            if dlg.ShowModal() == wx.ID_NO:
                return

        event.Skip()

    def onAbout(self, event):
        about_window = AboutWindow(self)
        about_window.ShowModal()

    def onGet(self, event):
        url = self.url_box.GetValue()
        self.clearTreeList()

        self.parse_thraed = Thread(target = self.parseThread, args = (url,))
        self.parse_thraed.setDaemon(True)
        self.parse_thraed.start()

        self.processing_window = ProcessingWindow(self)
        self.processing_window.Show()

        self.parse_ready = True

    def parseThread(self, url: str):
        Download.download_list.clear()

        match find_str("av|BV|ep|ss|md|b23.tv|blackboard|festival", url):
            case "av" | "BV":
                self.video_parser.parse_url(url)
                self.setVideoList()

                self.setResolutionList(VideoInfo)
            case "ep" | "ss" | "md":
                self.bangumi_parser.parse_url(url)
                self.setBangumiList()

                self.setResolutionList(BangumiInfo)
            case "b23.tv":
                new_url = process_shorklink(url)

                Thread(target = self.parseThread, args = (new_url,)).start()
                
                self.parse_thraed.stop()

            case "blackboard" | "festival":
                self.activity_parser.parse_url(url)
                
                Thread(target = self.parseThread, args = (ActivityInfo.new_url,)).start()
                
                self.parse_thraed.stop()

            case _:
                self.onError(100)

        self.onGetFinished()

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
        self.resolution_choice.Set(info.resolution_desc)
        
        info.resolution = Config.Download.resolution if Config.Download.resolution in info.resolution_id else info.resolution_id[0]
        self.resolution_choice.Select(info.resolution_id.index(info.resolution))

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
        self.infobar.ShowMessage("下载管理：已恢复中断的下载进度", flags = wx.ICON_INFORMATION)

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
        self.parse_thraed.stop()

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

        conf.config.set("user", "face", str(Config.User.face))
        conf.config.set("user", "uname", str(Config.User.uname))

        conf.config_save()

    def onShowUserMenu(self, event):
        if Config.User.login:
            self.PopupMenu(self.get_user_context_menu())
        else:
            self.onLogin(0)

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
        thread = Thread(target = self.checkUpdateManuallyThread)
        thread.setDaemon(True)

        thread.start()

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

    def showUserInfoThread(self):
        # 显示用户头像及昵称
        scale_size = (48, 48)

        image = wx.Image(get_user_face(Config.User.face), wx.BITMAP_TYPE_JPEG).Scale(scale_size[0], scale_size[1], wx.IMAGE_QUALITY_HIGH)
        
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

    def showUpdateWindow(self):
        update_window = UpdateWindow(self)
        update_window.ShowWindowModal()

    def showAudioQualityMenu(self):
        menu = wx.Menu()
        menu.Append(-1, "音质")
        menu.AppendSeparator()

        if Audio.q_hires:
            menuitem_hires = menu.Append(self.ID_AUDIO_HIRES, "Hi-Res 无损", kind = wx.ITEM_RADIO)
            menuitem_hires.Check(True if Audio.audio_quality == 30251 else False)

        if Audio.q_dolby:
            menuitem_dolby = menu.Append(self.ID_AUDIO_DOLBY, "杜比全景声", kind = wx.ITEM_RADIO)
            menuitem_dolby.Check(True if Audio.audio_quality == 30250 else False)

        menuitem_192k = menu.Append(self.ID_AUDIO_192K, "192K", kind = wx.ITEM_RADIO)
        menuitem_132k = menu.Append(self.ID_AUDIO_132K, "132K", kind = wx.ITEM_RADIO)
        menuitem_64k = menu.Append(self.ID_AUDIO_64K, "64K", kind = wx.ITEM_RADIO)

        menuitem_192k.Check(True if Audio.audio_quality == 30280 else False)
        menuitem_132k.Check(True if Audio.audio_quality == 30232 else False)
        menuitem_64k.Check(True if Audio.audio_quality == 30216 else False)

        self.PopupMenu(menu)

    def showInfobarMessage(self, message, flag):
        wx.CallAfter(self.infobar.ShowMessage, message, flag)

    def onCheckFFmpeg(self):
        if not Config.FFmpeg.available:
            dlg = wx.MessageDialog(self, "未安装 ffmpeg\n\n尚未安装 ffmpeg，无法合成视频。\n\n若您已确认安装 ffmpeg，请检查（二者其一即可）：\n1.为 ffmpeg 设置环境变量\n2.将 ffmpeg 放置到程序运行目录", "警告", wx.ICON_WARNING | wx.YES_NO)
            dlg.SetYesNoLabels("安装 ffmpeg", "忽略")

            if dlg.ShowModal() == wx.ID_YES:
                import webbrowser

                webbrowser.open("https://scott-sloan.cn/archives/120/")
    
    def convertToCircle(self, image):
        size = image.GetSize()
        width, height = size
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