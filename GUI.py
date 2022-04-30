import wx
import sys

from concurrent.futures import ThreadPoolExecutor

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
from gui.main import MainWindow
from gui.templates import *

class Main(MainWindow):
    def __init__(self, parent):
        MainWindow.__init__(self, parent)
        
        self.Bind_EVT()

        Main_ThreadPool.submit(self.onShow)

        self.show_download_window = False
        CheckUtils.CheckFFmpeg(self)
        
    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.On_Close)

        self.about_menu.Bind(wx.EVT_MENU, self.menu_EVT)
        self.tool_menu.Bind(wx.EVT_MENU, self.menu_EVT)

        self.address_tc.Bind(wx.EVT_TEXT_ENTER, self.get_url_EVT)
        self.get_button.Bind(wx.EVT_BUTTON, self.get_url_EVT)

        self.quality_cb.Bind(wx.EVT_CHOICE, self.select_quality)
        self.info_btn.Bind(wx.EVT_BUTTON, self.Load_info_window_EVT)
        self.download_manager_btn.Bind(wx.EVT_BUTTON, self.Load_download_window_EVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.download_EVT)

    def On_Close(self, event):
        sys.exit(0)

    def menu_EVT(self, event):
        menuid = event.GetId()

        if menuid == 110:
            info = CheckUtils.CheckUpdate()

            if info == None:
                Message.ShowMessage(self, 200)
            elif info[0]:
                CheckUtils.ShowMessageUpdate(self, info)
            else:
                Message.ShowMessage(self, 201)

        elif menuid == 120:
            import webbrowser
            webbrowser.open("https://scott.hanloth.cn/index.php/archives/12/")

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
        wx.CallAfter(self.list_lc.InitList)

        if "b23.tv" in url:
            url = process_shortlink(url)
        
        if "live" in url:
            self.theme = LiveInfo
            live_parser.parse_url(url)

            self.set_live_list()

        elif "audio" in url:
            self.theme = AudioInfo
            audio_parser.parse_url(url)

            self.set_audio_list()

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
            self.info_btn.Enable(False)
            self.download_btn.SetLabel("播放")
        elif self.theme == AudioInfo:
            self.quality_cb.Enable(False)
            self.info_btn.Enable(False)
            self.download_btn.SetLabel("下载音频")
        else:
            self.quality_cb.Enable(True)
            self.info_btn.Enable(True)
            self.download_btn.SetLabel("下载视频")

        self.download_btn.Enable(True)

        self.processing_window.Hide()

        self.list_lc.SetFocus()

        if Config.cookie_sessdata == "" and self.theme == BangumiInfo:
            self.infobar.ShowMessageInfo(200)

    def set_video_list(self):
        videos = len(VideoInfo.episodes) if VideoInfo.collection else len(VideoInfo.pages)

        wx.CallAfter(self.list_lc.SetVideoList)
        self.list_lb.SetLabel("视频 (共 %d 个)" % videos)

    def set_bangumi_list(self):
        bangumis = len(BangumiInfo.episodes)

        wx.CallAfter(self.list_lc.SetBangumiList)
        self.list_lb.SetLabel("{} (正片共 {} 集)".format(BangumiInfo.theme, bangumis))

    def set_live_list(self):
        wx.CallAfter(self.list_lc.SetLiveList)
        self.list_lb.SetLabel("直播")

    def set_audio_list(self):
        wx.CallAfter(self.list_lc.SetAudioList)
        self.list_lb.SetLabel("音乐")

    def set_quality(self, type):
        self.quality_cb.Set(type.quality_desc)
        type.quality = Config.default_quality if Config.default_quality in type.quality_id else type.quality_id[0]
        self.quality_cb.Select(type.quality_id.index(type.quality))

    def select_quality(self, event):
        if self.theme.quality_id[event.GetSelection()] in [127, 125, 120, 116, 112] and Config.cookie_sessdata == "":
            self.quality_cb.Select(self.theme.quality_id.index(80))
            wx.CallAfter(self.on_error, 404)

        self.theme.quality = self.theme.quality_id[event.GetSelection()]

    def download_EVT(self, event):
        if self.theme == LiveInfo:
            live_parser.open_player()
        else:
            if self.list_lc.GetAllCheckedItem(self.theme, self.on_error): return

            self.Load_download_window_EVT(0)

            quality_desc = self.quality_cb.GetStringSelection()

            if self.theme != AudioInfo:
                self.download_window.add_download_task(self.theme, quality_desc, quality_wrap[quality_desc])
            else:
                self.download_window.add_download_task(self.theme, None, None)

    def Load_info_window_EVT(self, event):
        self.info_window = InfoWindow(self, VideoInfo.title if self.theme == VideoInfo else BangumiInfo.title, self.theme)
        self.info_window.Show()
    
    def Load_download_window_EVT(self, event):
        if self.show_download_window:
            self.download_window.Show()
        else:
            self.download_window = DownloadWindow(self)
            self.download_window.Show()
            self.show_download_window = True

    def on_error(self, code: int):
        wx.CallAfter(self.processing_window.Hide)

        self.infobar.ShowMessageInfo(code)

    def on_redirect(self, url: str):
        Main_ThreadPool = ThreadPoolExecutor()
        Main_ThreadPool.submit(self.get_url_thread, url)

    def onShow(self):
        if not Config.auto_check_update: return
            
        self.update_info = CheckUtils.CheckUpdate()

        if self.update_info == None:
            self.infobar.ShowMessageInfo(405)

        elif self.update_info[0]:
            self.infobar.ShowMessageInfo(100)

if __name__ == "__main__":
    app = wx.App()

    Main_ThreadPool = ThreadPoolExecutor()
    
    video_parser = VideoParser()
    bangumi_parser = BangumiParser()
    live_parser = LiveParser()
    audio_parser = AudioParser()

    main_window = Main(None)
    main_window.Show()

    app.MainLoop()