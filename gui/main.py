import wx
import wx.py
from io import BytesIO

from utils.config import Config, Download
from utils.video import VideoInfo, VideoParser
from utils.bangumi import BangumiInfo, BangumiParser
from utils.tools import *
from utils.thread import Thread
from utils.login import QRLogin

from .templates import Frame, TreeListCtrl, InfoBar
from .about import AboutWindow
from .processing import ProcessingWindow
from .download import DownloadWindow
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

        resolution_hbox.Add(self.type_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        resolution_hbox.AddStretchSpacer()
        resolution_hbox.Add(resolution_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        resolution_hbox.Add(self.resolution_choice, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)

        self.treelist = TreeListCtrl(self.panel)
        self.treelist.SetSize(self.FromDIP((800, 260)))

        self.download_mgr_btn = wx.Button(self.panel, -1, "下载管理", size = self.FromDIP((100, 30)))
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = self.FromDIP((100, 30)))
        self.download_btn.Enable(False)
        
        self.face = wx.StaticBitmap(self.panel, -1)
        self.face.Cursor = wx.Cursor(wx.CURSOR_HAND)
        self.uname_lab = wx.StaticText(self.panel, -1, "登录")
        self.uname_lab.Cursor = wx.Cursor(wx.CURSOR_HAND)

        self.userinfo_hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.userinfo_hbox.Add(self.face, 0, wx.ALL & ~(wx.RIGHT), 10)
        self.userinfo_hbox.Add(self.uname_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)

        bottom_hbox.Add(self.userinfo_hbox, 0, wx.EXPAND)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.download_btn, 0, wx.ALL & ~(wx.LEFT), 10)

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
        self.help_menu.Append(self.ID_CHANGE_LOG, "更新日志(&P)")
        self.help_menu.AppendSeparator()
        self.help_menu.Append(self.ID_HELP, "使用帮助(&C)")
        self.help_menu.Append(self.ID_ABOUT, "关于(&A)")

        self.SetMenuBar(menu_bar)

    def init_user_info(self):
        if Config.User.login:
            Thread(target = self.ShowUserInfoThread).start()

    def get_user_context_menu(self):
        menu = wx.Menu()

        menu.Append(self.ID_REFRESH, "刷新")
        menu.Append(self.ID_LOGOUT, "注销")

        return menu
    
    def Bind_EVT(self):
        self.url_box.Bind(wx.EVT_TEXT_ENTER, self.OnGet)
        self.get_btn.Bind(wx.EVT_BUTTON, self.OnGet)
        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.onOpenDownloadMgr)
        self.download_btn.Bind(wx.EVT_BUTTON, self.OnDownload)

        self.face.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenu)
        self.uname_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenu)

        self.Bind(wx.EVT_MENU, self.onLogin, id = self.ID_LOGIN)
        self.Bind(wx.EVT_MENU, self.onLoadShell, id = self.ID_DEBUG)
        self.Bind(wx.EVT_MENU, self.onLoadSetting, id = self.ID_SETTINGS)
        self.Bind(wx.EVT_MENU, self.OnAbout, id = self.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnShowChangeLog, id = self.ID_CHANGE_LOG)
        self.Bind(wx.EVT_MENU, self.onCheckUpdate, id = self.ID_CHECK_UPDATE)
        self.Bind(wx.EVT_MENU, self.onLogout, id = self.ID_LOGOUT)
        self.Bind(wx.EVT_MENU, self.onHelp, id = self.ID_HELP)

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

        self.video_parser = VideoParser(self.OnError)
        self.bangumi_parser = BangumiParser(self.OnError)

        self.download_window = DownloadWindow(self)

        self.download_window_opened = False

    def OnAbout(self, event):
        about_window = AboutWindow(self)
        about_window.ShowModal()

    def OnGet(self, event):
        url = self.url_box.GetValue()
        self.clear_treelist()

        self.parse_thraed = Thread(target = self.ParseThread, args = (url,))
        self.parse_thraed.start()

        self.processing_window = ProcessingWindow(self)
        self.processing_window.Show()

    def ParseThread(self, url: str):
        Download.download_list.clear()

        match find_str("av|BV|ep|ss", url):
            case "av" | "BV":
                self.video_parser.parse_url(url)
                self.set_video_list()

                self.set_resolution_list(VideoInfo)
            case "ep" | "ss":
                self.bangumi_parser.parse_url(url)
                self.set_bangumi_list()

                self.set_resolution_list(BangumiInfo)
            case _:
                self.OnError(100)

        wx.CallAfter(self.OnGetFinished)
    
    def OnGetFinished(self):
        self.processing_window.Hide()

        self.download_btn.Enable(True)

        self.treelist.SetFocus()

    def OnDownload(self, event):
        resolution = resolution_map[self.resolution_choice.GetStringSelection()]

        self.treelist.get_all_selected_item(resolution)

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

    def clear_treelist(self):
        wx.CallAfter(self.treelist.init_list)

        self.resolution_choice.Clear()

        self.type_lab.SetLabel("")

    def set_resolution_list(self, info: VideoInfo | BangumiInfo):
        self.resolution_choice.Set(info.resolution_desc)
        
        info.resolution = Config.Download.resolution if Config.Download.resolution in info.resolution_id else info.resolution_id[0]
        self.resolution_choice.Select(info.resolution_id.index(info.resolution))

        Download.current_type = info

    def set_video_list(self):
        match VideoInfo.type:
            case 1 | 2:
                count = len(VideoInfo.pages)
            case 3:
                count = len(VideoInfo.episodes)
        
        self.treelist.set_video_list()
        
        self.type_lab.SetLabel("视频 (共 %d 个)" % count)
    
    def set_bangumi_list(self):
        count = len(BangumiInfo.episodes)

        wx.CallAfter(self.treelist.set_bangumi_list)
        self.type_lab.SetLabel("{} (正片共 {} 集)".format(BangumiInfo.type, count))

    def OnError(self, err_code):
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

        webbrowser.open("http://116.63.172.112:6888/archives/12/")

    def onCheckUpdate(self, event):
        thread = Thread(target = self.UpdateJsonThread)
        thread.setDaemon(True)

        thread.start()
    
    def OnShowChangeLog(self, event):
        thread = Thread(target = self.ChangeLogThread)
        thread.setDaemon(True)

        thread.start()

    def ShowUserInfoThread(self):
        self.face.SetBitmap(wx.Image(BytesIO(get_user_face(Config.User.face))).Scale(48, 48))
        self.face.Show()

        self.uname_lab.SetLabel(Config.User.uname)

        wx.CallAfter(self.userinfo_hbox.Layout)
        wx.CallAfter(self.frame_vbox.Layout)

    def UpdateJsonThread(self):
        update_json = get_update_json()
        
        wx.CallAfter(self.ShowCheckUpdateResult, update_json)

    def ChangeLogThread(self):
        changelog = get_changelog(Config.APP.version_code)
        
        wx.CallAfter(self.ShowChangeLogResult, {"changelog": changelog})

    def ShowCheckUpdateResult(self, update_json):
        if update_json["error"]:
            wx.MessageDialog(self, "检查更新失败\n\n目前无法检查更新，请稍候再试", "检查更新", wx.ICON_ERROR).ShowModal()
    
        else:
            if update_json["version_code"] > Config.APP.version_code:
                update_window = UpdateWindow(self, update_json)
                update_window.ui_update()
                update_window.ShowWindowModal()
            
            else:
                wx.MessageDialog(self, "当前没有可用的更新", "检查更新", wx.ICON_INFORMATION).ShowModal()

    def ShowChangeLogResult(self, update_json):
        update_window = UpdateWindow(self, update_json)
        update_window.ui_changelog()
        update_window.ShowWindowModal()

    def onCheckFFmpeg(self):
        if not Config.Download.ffmpeg_available:
            dlg = wx.MessageDialog(self, "未安装 ffmpeg\n\n尚未安装 ffmpeg，无法合成视频。\n\n若您已确认安装 ffmpeg，请检查（二者其一即可）：\n1.为 ffmpeg 设置环境变量\n2.将 ffmpeg 放置到程序运行目录", "警告", wx.ICON_WARNING | wx.YES_NO)
            dlg.SetYesNoLabels("安装 ffmpeg", "忽略")

            if dlg.ShowModal() == wx.ID_YES:
                import webbrowser

                webbrowser.open("http://116.63.172.112:6888/archives/120/")