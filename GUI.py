import wx
import os
import wx.adv
import wx.html2
import wx.dataview
from concurrent.futures import ThreadPoolExecutor

from utils.video import VideoInfo, VideoParser
from utils.bangumi import BangumiInfo, BangumiParser
from utils.live import LiveInfo, LiveParser
from utils.config import Config
from utils.tools import *

from gui.info import InfoWindow
from gui.download import DownloadWindow
from gui.settings import SettingWindow
from gui.about import AboutWindow
from gui.processing import ProcessingWindow
from gui.template import InfoBar, TreeListCtrl

class MainWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Bili23 Downloader")

        self.SetIcon(wx.Icon(Config._logo))
        self.SetSize(self.FromDIP((800, 480)))
        self.Center()
        self.panel = wx.Panel(self, -1)

        self.init_controls()
        self.Bind_EVT()

        Main_ThreadPool.submit(self.check_app_update)

    def init_controls(self):
        self.infobar = InfoBar(self.panel)

        self.address_lb = wx.StaticText(self.panel, -1, "地址")
        self.address_tc = wx.TextCtrl(self.panel, -1, style = wx.TE_PROCESS_ENTER)
        self.get_button = wx.Button(self.panel, -1, "Get")

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.address_lb, 0, wx.ALL | wx.CENTER, 10)
        hbox1.Add(self.address_tc, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)
        hbox1.Add(self.get_button, 0, wx.ALL, 10)

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
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = self.FromDIP((90, 30)))
        self.download_btn.Enable(False)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(self.info_btn, 0, wx.BOTTOM | wx.LEFT, 10)
        hbox3.AddStretchSpacer(1)
        hbox3.Add(self.download_btn, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.infobar, 0, wx.EXPAND)
        vbox.Add(hbox1, 0, wx.EXPAND, 10)
        vbox.Add(hbox2, 0, wx.EXPAND)
        vbox.Add(self.list_lc, 1, wx.EXPAND | wx.ALL, 10)
        vbox.Add(hbox3, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)

        self.init_menu_bar()

    def init_menu_bar(self):
        menu_bar = wx.MenuBar()
        self.about_menu = wx.Menu()
        self.tool_menu = wx.Menu()

        check_menuitem = wx.MenuItem(self.about_menu, 110, "检查更新(&U)")
        help_menuitem = wx.MenuItem(self.about_menu, 120, "使用帮助(&C)")
        about_menuitem = wx.MenuItem(self.about_menu, 130, "关于(&A)")

        option_menuitem = wx.MenuItem(self.tool_menu, 140, "设置(&S)")

        menu_bar.Append(self.tool_menu, "工具(&T)")
        menu_bar.Append(self.about_menu, "帮助(&H)")

        self.tool_menu.Append(option_menuitem)
        self.about_menu.Append(check_menuitem)
        self.about_menu.AppendSeparator()
        self.about_menu.Append(help_menuitem)
        self.about_menu.Append(about_menuitem)

        self.SetMenuBar(menu_bar)

    def Bind_EVT(self):
        self.about_menu.Bind(wx.EVT_MENU, self.menu_EVT)
        self.tool_menu.Bind(wx.EVT_MENU, self.menu_EVT)

        self.address_tc.Bind(wx.EVT_TEXT_ENTER, self.get_url_EVT)
        self.get_button.Bind(wx.EVT_BUTTON, self.get_url_EVT)

        self.quality_cb.Bind(wx.EVT_CHOICE, self.select_quality)
        self.info_btn.Bind(wx.EVT_BUTTON, self.Load_info_window_EVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.download_EVT)

    def menu_EVT(self, event):
        menuid = event.GetId()

        if menuid == 110:
            info = check_update()

            if info == None:
                wx.MessageDialog(self, "检查更新失败\n\n当前无法检查更新，请稍候再试", "警告", wx.ICON_WARNING).ShowModal()
                
            elif info[0]:
                dialog = wx.MessageDialog(self, "有新的更新可用\n\n{}\n\n更新说明：{}\n\n版本：{}".format(info[1], info[2], info[4]), "提示", wx.ICON_INFORMATION | wx.YES_NO)
                dialog.SetYesNoLabels("马上更新", "稍后更新")
                if dialog.ShowModal() == wx.ID_YES:
                    import webbrowser
                    webbrowser.open(Config._website)
            
            else:
                wx.MessageDialog(self, "当前没有可用更新", "提示", wx.ICON_INFORMATION).ShowModal()

        elif menuid == 120:
            wx.MessageDialog(self, "使用帮助\n\nhelp", "使用帮助", wx.ICON_INFORMATION).ShowModal()

        elif menuid == 130:
            AboutWindow(self)

        elif menuid == 140:
            setting_window = SettingWindow(self)
            setting_window.ShowModal()

    def get_url_EVT(self, event):
        url = str(self.address_tc.GetValue())

        self.quality_cb.Clear()
        self.list_lb.SetLabel("视频")
        self.info_btn.Enable(False)
        self.download_btn.Enable(False)

        VideoInfo.down_pages = BangumiInfo.down_episodes = []

        self.processing_window = ProcessingWindow(self)

        Main_ThreadPool.submit(self.get_url_thread, url)

        self.processing_window.ShowWindowModal()
        
    def get_url_thread(self, url: str):
        wx.CallAfter(self.list_lc.init_list_lc)

        if "b23.tv" in url:
            url = process_shortlink(url)
        
        if "live" in url:
            self.theme = LiveInfo
            live_parser.parse_url(url)

            self.set_live_list()

        elif "BV" in url or "av" in url:
            self.theme = VideoInfo
            video_parser.parse_url(url, self.on_redirect, self.on_error)

            self.set_video_list()
            self.set_quality(VideoInfo)

        elif "ep" in url or "ss" in url or "md" in url:
            self.theme = BangumiInfo
            bangumi_parser.parse_url(url, self.on_error)

            self.set_bangumi_list()
            self.set_quality(BangumiInfo)
        else:
            self.on_error(400)

        wx.CallAfter(self.get_url_finish)
        
    def get_url_finish(self):
        if self.theme == LiveInfo:
            self.quality_cb.Enable(False)
            self.download_btn.SetLabel("播放")
        else:
            self.quality_cb.Enable(True)
            self.download_btn.SetLabel("下载视频")

        self.download_btn.Enable(True)
        self.info_btn.Enable(True)

        self.processing_window.Hide()

        self.list_lc.SetFocus()

        if Config.cookie_sessdata == "" and self.theme == BangumiInfo:
            self.infobar.ShowMessage("注意：尚未添加大会员 Cookie，部分视频可能无法下载", flags = wx.ICON_WARNING)

    def set_video_list(self):
        videos = len(VideoInfo.episodes) if VideoInfo.collection else len(VideoInfo.pages)

        wx.CallAfter(self.list_lc.set_video_list)
        self.list_lb.SetLabel("视频 (共 %d 个)" % videos)

    def set_bangumi_list(self):
        bangumis = len(BangumiInfo.episodes)

        wx.CallAfter(self.list_lc.set_bangumi_list)
        self.list_lb.SetLabel("{} (正片共 {} 集)".format(BangumiInfo.theme, bangumis))

    def set_live_list(self):
        wx.CallAfter(self.list_lc.set_live_list)
        self.list_lb.SetLabel("直播")

    def set_quality(self, type):
        self.quality_cb.Set(type.quality_desc)
        type.quality = Config.default_quality if Config.default_quality in type.quality_id else type.quality_id[0]
        self.quality_cb.Select(type.quality_id.index(type.quality))

    def select_quality(self, event):
        if self.theme.quality_id[event.GetSelection()] in [120, 116, 112] and Config.cookie_sessdata == "":
            self.quality_cb.Select(self.theme.quality_id.index(80))
            wx.CallAfter(self.on_error, 403)

        self.theme.quality = self.theme.quality_id[event.GetSelection()]

    def download_EVT(self, event):
        if self.theme == LiveInfo:
            if Config.player_path == "":
                wx.MessageDialog(self, "未指定播放器路径\n\n尚未指定播放器路径，请添加路径后再试", "警告", wx.ICON_WARNING).ShowModal()
                return

            elif LiveInfo.live_status == 0:
                wx.MessageDialog(self, "当前直播未开播\n\n当前直播尚未开播，请稍候再试", "警告", wx.ICON_WARNING).ShowModal()
                return

            else:
                os.system("{} {}".format(Config.player_path, LiveInfo.playurl))
        else:
            if self.list_lc.get_all_checked_item(self.theme, self.on_error):
                return

            self.download_window = DownloadWindow(self)

            Main_ThreadPool.submit(self.download_thread)

            self.download_window.ShowWindowModal()

    def download_thread(self):
        kwargs = {"on_start":self.download_window.on_download_start, "on_download":self.download_window.on_downloading, "on_complete":self.on_download_complete, "on_merge":self.download_window.on_merge}

        video_parser.get_video_durl(kwargs) if self.theme == VideoInfo else bangumi_parser.get_bangumi_durl(kwargs)

    def Load_info_window_EVT(self, event):
        self.info_window = InfoWindow(self, VideoInfo.title if self.theme == VideoInfo else BangumiInfo.title)
        self.info_window.Show()

    def on_error(self, code: int):
        wx.CallAfter(self.processing_window.Hide)

        self.infobar.show_error_info(code)

    def on_download_complete(self):
        wx.CallAfter(self.download_window.Hide)

        if Config.show_notification:
            msg = wx.adv.NotificationMessage("下载完成", "所选视频已全部下载完成", self, wx.ICON_INFORMATION)
            msg.Show(timeout = 5)
            return

        dlg = wx.MessageDialog(self, "下载完成\n\n所选视频已全部下载完成", "提示", wx.ICON_INFORMATION | wx.YES_NO)
        dlg.SetYesNoLabels("打开所在位置", "确定")

        if dlg.ShowModal() == wx.ID_YES:
            if Config._platform.startswith("Windows"):
                os.startfile(Config.download_path)
            else:
                os.system('xdg-open "{}"'.format(Config.download_path))

    def on_redirect(self, url: str):
        Main_ThreadPool = ThreadPoolExecutor(max_workers = 2)
        Main_ThreadPool.submit(self.get_url_thread, url)

    def check_app_update(self):
        if not Config.auto_check_update:
            return
            
        self.update_info = check_update()

        if self.update_info == None:
            self.infobar.ShowMessage("检查更新失败", wx.ICON_WARNING)

        elif self.update_info[0]:
            self.infobar.ShowMessage("有新版本更新可用", wx.ICON_INFORMATION)

if __name__ == "__main__":
    app = wx.App()

    Main_ThreadPool = ThreadPoolExecutor(max_workers = 2)
    
    video_parser = VideoParser()
    bangumi_parser = BangumiParser()
    live_parser = LiveParser()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()