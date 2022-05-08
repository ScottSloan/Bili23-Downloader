import wx
from threading import Thread

from utils.video import VideoInfo, VideoParser
from utils.bangumi import BangumiInfo, BangumiParser
from utils.live import LiveInfo, LiveParser
from utils.audio import AudioInfo, AudioParser
from utils.config import Config
from utils.tools import *
from utils.check import CheckUtils

from gui.info import InfoWindow
from gui.download import DownloadWindow
from gui.settings import SettingWindow
from gui.about import AboutWindow
from gui.processing import ProcessingWindow
from gui.taskbar import TaskBarIcon
from gui.user import UserWindow
from gui.login import LoginWindow
from gui.notification import Notification
from gui.templates import *

class MainWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Bili23 Downloader")

        self.SetIcon(wx.Icon(Config.res_logo))
        self.SetSize(self.FromDIP((800, 480)))
        self.Center()

        self.panel = wx.Panel(self, -1)

        self.InitUI()
        
        self.Bind_EVT()

        onshow_thread = Thread(target = self.onShow)
        onshow_thread.start()

        self.show_download_window = False

    def InitUI(self):
        self.infobar = InfoBar(self.panel)

        self.address_lb = wx.StaticText(self.panel, -1, "地址")
        self.address_tc = wx.TextCtrl(self.panel, -1, style = wx.TE_PROCESS_ENTER)
        self.get_button = wx.Button(self.panel, -1, "Get")
        self.help_button = wx.BitmapButton(self.panel, -1, wx.ArtProvider().GetBitmap(wx.ART_INFORMATION, size = (16, 16)), style = wx.BORDER_NONE)
        self.help_button.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.address_lb, 0, wx.ALL | wx.CENTER, 10)
        hbox1.Add(self.address_tc, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)
        hbox1.Add(self.get_button, 0, wx.ALL, 10)
        hbox1.Add(self.help_button, 0, wx.ALL & (~wx.LEFT), 10)

        self.list_lb = wx.StaticText(self.panel, -1, "视频")
        self.quality_lb = wx.StaticText(self.panel, -1, "清晰度")
        self.quality_cb = wx.Choice(self.panel, -1)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(self.list_lb, 0, wx.LEFT | wx.CENTER, 10)
        hbox2.AddStretchSpacer(1)
        hbox2.Add(self.quality_lb, 0, wx.CENTER | wx.RIGHT, 10)
        hbox2.Add(self.quality_cb, 0, wx.RIGHT, 10)

        self.list_lc = TreeListCtrl(self.panel)

        self.info_btn = wx.Button(self.panel, -1, "视频信息", size = self.FromDIP((90, 30)))
        self.info_btn.Enable(False)
        self.download_manager_btn = wx.Button(self.panel, -1, "下载管理", size = self.FromDIP((90, 30)))
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = self.FromDIP((90, 30)))
        self.download_btn.Enable(False)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(self.info_btn, 0, wx.BOTTOM | wx.LEFT, 10)
        hbox3.AddStretchSpacer(1)
        hbox3.Add(self.download_manager_btn)
        hbox3.Add(self.download_btn, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.infobar, 0, wx.EXPAND)
        vbox.Add(hbox1, 0, wx.EXPAND)
        vbox.Add(hbox2, 0, wx.EXPAND)
        vbox.Add(self.list_lc, 1, wx.EXPAND | wx.ALL, 10)
        vbox.Add(hbox3, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)

        self.InitMenuBar()
        self.InitTaskBar()

    def InitMenuBar(self):
        menu_bar = wx.MenuBar()
        self.about_menu = wx.Menu()
        self.tool_menu = wx.Menu()

        check_menuitem = wx.MenuItem(self.about_menu, 110, "检查更新(&U)")
        help_menuitem = wx.MenuItem(self.about_menu, 120, "使用帮助(&C)")
        about_menuitem = wx.MenuItem(self.about_menu, 130, "关于(&A)")

        user_menuitem = wx.MenuItem(self.tool_menu, 150, "用户中心(&E)")
        option_menuitem = wx.MenuItem(self.tool_menu, 140, "设置(&S)")

        menu_bar.Append(self.tool_menu, "工具(&T)")
        menu_bar.Append(self.about_menu, "帮助(&H)")

        self.tool_menu.Append(user_menuitem)
        self.tool_menu.AppendSeparator()
        self.tool_menu.Append(option_menuitem)

        self.about_menu.Append(check_menuitem)
        self.about_menu.AppendSeparator()
        self.about_menu.Append(help_menuitem)
        self.about_menu.Append(about_menuitem)

        self.SetMenuBar(menu_bar)
    
    def InitTaskBar(self):
        if not Config.show_icon: return

        TaskBarIcon()
    
    def Bind_EVT(self):
        self.about_menu.Bind(wx.EVT_MENU, self.menu_EVT)
        self.tool_menu.Bind(wx.EVT_MENU, self.menu_EVT)

        self.address_tc.Bind(wx.EVT_TEXT_ENTER, self.get_url_EVT)
        self.address_tc.Bind(wx.EVT_SET_FOCUS, self.On_GetFocus)
        self.address_tc.Bind(wx.EVT_KILL_FOCUS, self.On_KillFocus)

        self.get_button.Bind(wx.EVT_BUTTON, self.get_url_EVT)
        self.help_button.Bind(wx.EVT_BUTTON, self.show_help_info_EVT)

        self.quality_cb.Bind(wx.EVT_CHOICE, self.select_quality)
        self.info_btn.Bind(wx.EVT_BUTTON, self.Load_info_window_EVT)
        self.download_manager_btn.Bind(wx.EVT_BUTTON, self.Load_download_window_EVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.download_EVT)

    def On_GetFocus(self, event):
        if self.address_tc.GetValue() == "请输入 URL 链接":
            self.address_tc.Clear()
            self.address_tc.SetForegroundColour("black")

        event.Skip()

    def On_KillFocus(self, event):
        if self.address_tc.GetValue() == "":
            self.address_tc.SetValue("请输入 URL 链接")
            self.address_tc.SetForegroundColour(wx.Colour(117, 117, 117))

        event.Skip()

    def menu_EVT(self, event):
        menuid = event.GetId()

        if menuid == 110:
            info = CheckUtils.CheckUpdate()

            if info == None:
                Notification.show_dialog(self, 200)
            elif info[0]:
                CheckUtils.ShowMessageUpdate(self, info)
            else:
                Notification.show_dialog(self, 201)

        elif menuid == 120:
            import webbrowser
            webbrowser.open("https://scott.hanloth.cn/index.php/archives/12/")

        elif menuid == 130:
            AboutWindow(self)
            
        elif menuid == 140:
            setting_window = SettingWindow(self)
            setting_window.ShowModal()
        
        elif menuid == 150:
            if Config.user_uname == "":
                login_window = LoginWindow(self)
                login_window.ShowWindowModal()
            
            if Config.user_uname != "":
                user_window = UserWindow(self)
                user_window.ShowWindowModal()
            
    def get_url_EVT(self, event):
        url = str(self.address_tc.GetValue())

        if url == "": return

        self.quality_cb.Clear()
        self.list_lb.SetLabel("视频")
        self.info_btn.Enable(False)
        self.download_btn.Enable(False)

        VideoInfo.down_pages = BangumiInfo.down_episodes = []

        self.processing_window = ProcessingWindow(self)

        work_thread = Thread(target = self.get_url_thread, args = (url,))
        work_thread.start()

        self.processing_window.ShowWindowModal()
        
    def get_url_thread(self, url: str):
        wx.CallAfter(self.list_lc.init_list)

        if "b23.tv" in url:
            url = process_shortlink(url)
        
        if "live" in url:
            self.type = LiveInfo
            live_parser.parse_url(url, self.on_error)

            self.set_live_list()

        elif "au" in url:
            self.type = AudioInfo
            audio_parser.parse_url(url, self.on_error)

            self.set_audio_list()

        elif "BV" in url or "av" in url:
            self.type = VideoInfo
            video_parser.parse_url(url, self.on_redirect, self.on_error)

            self.set_video_list()
            self.set_quality(VideoInfo)

        elif "ep" in url or "ss" in url or "md" in url:
            self.type = BangumiInfo
            bangumi_parser.parse_url(url, self.on_error)

            self.set_bangumi_list()
            self.set_quality(BangumiInfo)
        else:
            self.on_error(400)

        wx.CallAfter(self.get_url_finish)
        
    def get_url_finish(self):
        if self.type == LiveInfo:
            self.quality_cb.Enable(False)
            self.info_btn.Enable(False)
            self.download_btn.SetLabel("播放")

        elif self.type == AudioInfo:
            self.quality_cb.Enable(False)
            self.info_btn.Enable(True)

            if AudioInfo.isplaylist:
                self.info_btn.SetLabel("歌单信息")
                self.download_btn.SetLabel("下载歌单")
            else:
                self.info_btn.SetLabel("音乐信息")
                self.download_btn.SetLabel("下载音乐")

        else:
            self.quality_cb.Enable(True)
            self.info_btn.Enable(True)

            self.info_btn.SetLabel("视频信息")
            self.download_btn.SetLabel("下载视频")

        self.download_btn.Enable(True)

        self.processing_window.Hide()

        self.list_lc.SetFocus()

        if Config.user_sessdata == "" and self.type == BangumiInfo:
            self.infobar.show_message_info(200)

    def set_video_list(self):
        count = len(VideoInfo.episodes) if VideoInfo.collection else len(VideoInfo.pages)

        wx.CallAfter(self.list_lc.set_video_list)
        self.list_lb.SetLabel("视频 (共 {} 个)".format(count))

    def set_bangumi_list(self):
        count = len(BangumiInfo.episodes)

        wx.CallAfter(self.list_lc.set_bangumi_list)
        self.list_lb.SetLabel("{} (正片共 {} 集)".format(BangumiInfo.type, count))

    def set_live_list(self):
        wx.CallAfter(self.list_lc.set_live_list)
        self.list_lb.SetLabel("直播")

    def set_audio_list(self):
        wx.CallAfter(self.list_lc.set_audio_list)

        if AudioInfo.isplaylist:
            self.list_lb.SetLabel("歌单 (共 {} 首)".format(AudioInfo.count))
        else:
            self.list_lb.SetLabel("音乐 (共 1 首)")

    def set_quality(self, type):
        self.quality_cb.Set(type.quality_desc)
        type.quality = Config.default_quality if Config.default_quality in type.quality_id else type.quality_id[0]
        self.quality_cb.Select(type.quality_id.index(type.quality))

    def select_quality(self, event):
        if self.type.quality_id[event.GetSelection()] in [127, 125, 120, 116, 112] and Config.user_sessdata == "":
            self.quality_cb.Select(self.type.quality_id.index(80))
            wx.CallAfter(self.on_error, 404)

        self.type.quality = self.type.quality_id[event.GetSelection()]

    def download_EVT(self, event):
        if self.type == LiveInfo:
            live_parser.open_player()
        else:
            if self.list_lc.get_allcheckeditem(self.type, self.on_error): return

            self.Load_download_window_EVT(0)

            quality_desc = self.quality_cb.GetStringSelection()

            if self.type != AudioInfo:
                self.download_window.add_download_task(self.type, quality_desc, quality_wrap[quality_desc])
            else:
                self.download_window.add_download_task(self.type, None, None)

    def Load_info_window_EVT(self, event):
        self.info_window = InfoWindow(self, VideoInfo.title if self.type == VideoInfo else BangumiInfo.title, self.type)
        self.info_window.Show()
    
    def Load_download_window_EVT(self, event):
        if self.show_download_window:
            self.download_window.Show()
        else:
            self.download_window = DownloadWindow.Window(self)
            self.download_window.Show()
            self.show_download_window = True

    def show_help_info_EVT(self, event):
        wx.MessageDialog(self, "支持输入的 URL 链接\n\n用户投稿类型视频链接\n剧集（番剧，电影，纪录片等）链接\n活动页链接\n直播链接\n音乐、歌单链接\nb23.tv 短链接", Config.APPNAME, wx.ICON_INFORMATION).ShowModal()

    def on_error(self, code: int):
        wx.CallAfter(self.processing_window.Hide)

        self.infobar.show_message_info(code)

    def on_redirect(self, url: str):
        work_thread = Thread(target = self.get_url_thread, args = (url,))
        work_thread.start()

    def onShow(self):
        if not Config.auto_check_update: return
            
        self.update_info = CheckUtils.CheckUpdate()

        if self.update_info == None:
            self.infobar.show_message_info(405)

        elif self.update_info[0]:
            self.infobar.show_message_info(100)
    
video_parser = VideoParser()
bangumi_parser = BangumiParser()
live_parser = LiveParser()
audio_parser = AudioParser()