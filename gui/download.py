import wx
import os
import time
import subprocess
import wx.lib.scrolledpanel
from concurrent.futures import ThreadPoolExecutor

from utils.video import VideoInfo
from utils.bangumi import BangumiInfo
from utils.audio import AudioInfo
from utils.download import Downloader
from utils.config import Config
from utils.tools import *

from gui.taskbar import TaskBarProgress
from gui.templates import Frame
from gui.notification import Notification

class DownloadWindow:
    download_list = {}

    download_count = 0
    downloading = False

    class Window(Frame):
        def __init__(self, parent):
            Frame.__init__(self, parent, "下载管理", (680, 420), False)

            self.SetBackgroundColour("white")
        
            self.list_panel = DownloadWindow.ListPanel(self)

            self.Bind_EVT()

            taskbar.Bind(self.GetHandle())

        def Bind_EVT(self):
            self.Bind(wx.EVT_CLOSE, self.onClose)

        def onClose(self, event):
            self.Hide()

        def add_download_task(self, type, quality_desc: str, quality_id: int):
            if type == VideoInfo:
                if VideoInfo.multiple:
                    for i in VideoInfo.down_pages:
                        self.list_panel.download_list_panel.add_panel(pid = DownloadWindow.download_count, title = i["part"], bvid = VideoInfo.bvid, cid = i["cid"], sid = None, lyric = None, quality_desc = quality_desc, quality_id = quality_id, type = type, onComplete = self.onComplete, onMerge = self.onMerge)

                elif VideoInfo.collection:
                    for i in VideoInfo.down_pages:
                        self.list_panel.download_list_panel.add_panel(pid = DownloadWindow.download_count, title = i["title"], bvid = i["bvid"], cid = i["cid"], sid = None, lyric = None, quality_desc = quality_desc, quality_id = quality_id, type = type, onComplete = self.onComplete, onMerge = self.onMerge)

                else:
                    self.list_panel.download_list_panel.add_panel(pid = DownloadWindow.download_count, title = VideoInfo.title, bvid = VideoInfo.bvid, cid = VideoInfo.cid, sid = None, lyric = None, quality_desc = quality_desc, quality_id = quality_id, type = type, onComplete = self.onComplete, onMerge = self.onMerge)

            elif type == BangumiInfo:
                for i in BangumiInfo.down_episodes:
                    self.list_panel.download_list_panel.add_panel(pid = DownloadWindow.download_count, title = i["share_copy"], bvid = i["bvid"], cid = i["cid"], sid = None, lyric = None, quality_desc = quality_desc, quality_id = quality_id, type = type, onComplete = self.onComplete, onMerge = self.onMerge)

            elif type == AudioInfo and AudioInfo.isplaylist:
                for i in AudioInfo.down_list:
                    self.list_panel.download_list_panel.add_panel(pid = DownloadWindow.download_count, title = i["title"], bvid = None, cid = None, sid = i["id"], lyric = i["lyric"], quality_desc = None, quality_id = None, type = type, onComplete = self.onComplete, onMerge = self.onMerge)

            else:
                self.list_panel.download_list_panel.add_panel(pid = DownloadWindow.download_count, title = AudioInfo.title, bvid = None, cid = None, sid = AudioInfo.sid, lyric = AudioInfo.lyric, quality_desc = None, quality_id = None, type = type, onComplete = self.onComplete, onMerge = self.onMerge)

            self.list_panel.task_lb.SetLabel("{} 个任务正在下载".format(len(DownloadWindow.download_list)))

            ThreadPool.submit(self.start_download)

        def start_download(self):
            for key, value in DownloadWindow.download_list.items():

                if value.status == "waiting" and not DownloadWindow.downloading:
                    value.start_download()
                    DownloadWindow.downloading = True

                    break

        def onMerge(self):
            if len(DownloadWindow.download_list) != 0:
                ThreadPool.submit(self.start_download)

        def onComplete(self, iserror = False, update_title_only = False):
            count = len(DownloadWindow.download_list)
    
            if count != 0:
                self.list_panel.task_lb.SetLabel("{} 个任务正在下载".format(count))
            else:
                self.list_panel.task_lb.SetLabel("下载管理")

                if Config.show_notification and not update_title_only:
                    if not iserror:
                        Notification.show_notification_download_finish()
                        self.RequestUserAttention(flags = wx.USER_ATTENTION_INFO)
                    else:
                        Notification.show_notification_download_error()
                        self.RequestUserAttention(flags = wx.USER_ATTENTION_ERROR)

    class ListPanel(wx.Panel):
        def __init__(self, parent):
            wx.Panel.__init__(self, parent, -1)
            
            self.init_UI()
            self.Bind_EVT()

        def init_UI(self):
            self.task_lb = wx.StaticText(self, -1, "下载管理")
            self.task_lb.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑"))

            top_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

            self.download_list_panel = DownloadWindow.DownloadListPanel(self)

            bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

            self.open_btn = wx.Button(self, -1, "打开下载目录", size = self.FromDIP((100, 30)))
            self.clear_btn = wx.Button(self, -1, "清除下载记录", size = self.FromDIP((100, 30)))

            hbox2 = wx.BoxSizer(wx.HORIZONTAL)
            hbox2.Add(self.open_btn, 0, wx.ALL, 10)
            hbox2.AddStretchSpacer(1)
            hbox2.Add(self.clear_btn, 0, wx.ALL, 10)

            main_sizer = wx.BoxSizer(wx.VERTICAL)
            main_sizer.Add(self.task_lb, 0, wx.ALL, 10)
            main_sizer.Add(top_border, 0, wx.EXPAND)
            main_sizer.Add(self.download_list_panel, 1, wx.EXPAND)
            main_sizer.Add(bottom_border, 0, wx.EXPAND)
            main_sizer.Add(hbox2, 0, wx.EXPAND)

            self.SetSizer(main_sizer)

        def Bind_EVT(self):
            self.open_btn.Bind(wx.EVT_BUTTON, self.open_EVT)
            self.clear_btn.Bind(wx.EVT_BUTTON, self.clear_EVT)

        def open_EVT(self, event):
            if Config.PLATFORM.startswith("Windows"):
                os.startfile(Config.download_path)
            else:
                os.system('xdg-open "{}"'.format(Config.download_path))

        def clear_EVT(self, event):
            sizer = self.download_list_panel.main_sizer

            for key, value in range(len(DownloadWindow.download_list)):
                if value.status == "completed":
                    value.Destroy()

                    sizer.Layout()
                    self.download_list_panel.SetupScrolling(scroll_x = False)

                    del DownloadWindow.download_list[key]
    
    class DownloadListPanel(wx.lib.scrolledpanel.ScrolledPanel):
        def __init__(self, parent):
            wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent)

            self.main_sizer = wx.BoxSizer(wx.VERTICAL)

            self.empty = False

            self.SetBackgroundColour('white')

            self.SetSizer(self.main_sizer)
        
        def add_panel(self, **kwargs):
            panel = DownloadWindow.DownloadItemPanel(self, **kwargs)

            self.main_sizer.Add(panel, 0, wx.EXPAND)

            self.SetupScrolling(scroll_x = False)

            DownloadWindow.download_list[DownloadWindow.download_count] = panel
            DownloadWindow.download_count += 1

    class DownloadItemPanel(wx.Panel):

        pid = title = bvid = cid = sid = quality_desc = quality_id = type = status = None
        video_path = audio_path = 0
        gid = []

        onComplete_ = onMerge_ = None

        def __init__(self, parent, **kwargs):
            self.parent = parent

            self.pid = kwargs["pid"]
            self.title = kwargs["title"]
            self.bvid = kwargs["bvid"]
            self.cid = kwargs["cid"]
            self.sid = kwargs["sid"]
            self.lyric = kwargs["lyric"]
            self.quality_desc = kwargs["quality_desc"]
            self.quality_id = kwargs["quality_id"]
            self.type = kwargs["type"]
            self.status = "waiting"

            self.onComplete_ = kwargs["onComplete"]
            self.onMerge_ = kwargs["onMerge"]

            wx.Panel.__init__(self, parent)

            self.init_UI()
            self.Bind_EVT()

        def init_UI(self):
            self.title_lab = wx.StaticText(self, -1, self.title, style = wx.ST_ELLIPSIZE_END)

            self.quality_lab = wx.StaticText(self, -1, self.quality_desc if self.type != AudioInfo else "音乐")
            self.quality_lab.SetForegroundColour(wx.Colour(108, 108, 108))
            self.size_lab = wx.StaticText(self, -1, "-")
            self.size_lab.SetForegroundColour(wx.Colour(108, 108, 108))

            hbox1 = wx.BoxSizer(wx.HORIZONTAL)
            hbox1.Add(self.quality_lab, 0, wx.ALL & (~wx.TOP), 10)
            hbox1.AddSpacer(self.FromDIP(75))
            hbox1.Add(self.size_lab, 0, wx.ALL & (~wx.TOP), 10)

            vbox1 = wx.BoxSizer(wx.VERTICAL)
            vbox1.Add(self.title_lab, 1, wx.ALL, 10)
            vbox1.Add(hbox1, 0, wx.EXPAND)

            self.gauge = wx.Gauge(self, -1, 100)

            self.speed_lab = wx.StaticText(self, -1, "等待下载...")
            self.speed_lab.SetForegroundColour(wx.Colour(108, 108, 108))

            vbox2 = wx.BoxSizer(wx.VERTICAL)
            vbox2.Add(self.gauge, 0, wx.ALL | wx.EXPAND, 10)
            vbox2.Add(self.speed_lab, 0, wx.ALL & (~wx.TOP), 10)

            self.pause_btn = wx.BitmapButton(self, -1, wx.Bitmap(Config.res_pause), size = self.FromDIP((16, 16)))
            self.pause_btn.SetToolTip("暂停下载")
            self.open_btn = wx.BitmapButton(self, -1, wx.Bitmap(Config.res_open), size = self.FromDIP((16, 16)))
            self.open_btn.SetToolTip("打开文件所在位置")
            self.cancel_btn = wx.BitmapButton(self, -1, wx.Bitmap(Config.res_delete), size = self.FromDIP((16, 16)))
            self.cancel_btn.SetToolTip("取消下载")

            hbox2 = wx.BoxSizer(wx.HORIZONTAL)
            hbox2.Add(vbox1, 1, wx.EXPAND)
            hbox2.Add(vbox2, 0, wx.EXPAND)
            hbox2.AddSpacer(self.FromDIP(10))
            hbox2.Add(self.pause_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
            hbox2.Add(self.open_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
            hbox2.Add(self.cancel_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)

            border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

            vbox3 = wx.BoxSizer(wx.VERTICAL)
            vbox3.Add(hbox2, 1, wx.EXPAND)
            vbox3.Add(border, 0, wx.EXPAND)

            self.SetSizer(vbox3)

        def Bind_EVT(self):
            self.pause_btn.Bind(wx.EVT_BUTTON, self.pause_EVT)
            self.open_btn.Bind(wx.EVT_BUTTON, self.open_EVT)
            self.cancel_btn.Bind(wx.EVT_BUTTON, self.cancel_EVT)

        def start_download(self):
            ThreadPool.submit(self.download_thread)

        def download_thread(self):
            self.status = "downloading"

            if self.type != AudioInfo:
                get_danmaku_subtitle_lyric(self.title, self.cid, self.bvid, None)
            else:
                get_danmaku_subtitle_lyric(self.title, None, None, self.lyric)
            
            self.start_download()

        def pause_EVT(self, event):
            ThreadPool.submit(self.pause_EVT_thread)

        def pause_EVT_thread(self):
            if self.status == "waiting" or self.status == "downloading":
                self.status = "pause"
                self.pause_btn.SetBitmap(wx.Bitmap(Config.res_resume))
                self.pause_btn.SetToolTip("继续下载")

                self.onPause()

                taskbar.SetProgressState(TaskBarProgress.TBPF_PAUSED)

            else:
                self.status = "downloading"
                self.pause_btn.SetBitmap(wx.Bitmap(Config.res_pause))
                self.pause_btn.SetToolTip("暂停下载")

                self.onResume()

                taskbar.SetProgressState(TaskBarProgress.TBPF_NORMAL)

        def open_EVT(self, event):
            if Config.PLATFORM.startswith("Windows"):
                os.startfile(Config.download_path)
            else:
                os.system('xdg-open "{}"'.format(Config.download_path))

        def cancel_EVT(self, event):
            ThreadPool.submit(self.cancel_EVT_thread)

        def cancel_EVT_thread(self):
            if self.status == "downloading":
                self.onCancel()
            
            if self.status != "error":
                self.onComplete_(update_title_only = True)

            wx.CallAfter(self.update_panel)

        def update_panel(self):
            self.Destroy()

            self.parent.main_sizer.Layout()
            self.parent.SetupScrolling(scroll_x = False)

        @property
        def video_durl_api(self) -> str:
            return "https://api.bilibili.com/x/player/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(self.bvid, self.cid)

        @property
        def bangumi_durl_api(self) -> str:
            return "https://api.bilibili.com/pgc/player/web/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(self.bvid, self.cid)

        @property
        def audio_durl_api(self) -> str:
            return "https://www.bilibili.com/audio/music-service-c/web/url?sid={}".format(self.sid)

        @property
        def get_full_url(self) -> str:
            if self.type == AudioInfo:
                return "https://www.bilibili.com/audio/au{}".format(self.sid)
            else:
                return "https://www.bilibili.com/video/{}".format(self.bvid)

        def get_video_durl(self):
            try:
                if self.type == VideoInfo:
                    request = requests.get(self.video_durl_api, headers = get_header(self.get_full_url, Config.user_sessdata), proxies = get_proxy())
                    request_json = json.loads(request.text)
                    json_dash = request_json["data"]["dash"]
                else:
                    request = requests.get(self.bangumi_durl_api, headers = get_header(self.get_full_url, Config.user_sessdata), proxies = get_proxy())
                    request_json = json.loads(request.text)
                    json_dash = request_json["result"]["dash"]
            except:
                self.OnError()
                return

            quality = json_dash["video"][0]["id"] if json_dash["video"][0]["id"] < self.quality_id else self.quality_id

            temp_video_durl = [i["baseUrl"] for i in json_dash["video"] if i["id"] == quality]
            self.video_durl = temp_video_durl[Config.codec] if len(temp_video_durl) > 1 else temp_video_durl[0]
            
            temp_audio_durl = sorted(json_dash["audio"], key = lambda x: x["id"], reverse = True)
            self.audio_durl = [i for i in temp_audio_durl if (i["id"] - 30200) == quality or (i["id"] - 30200) < quality][0]["baseUrl"]

        def get_audio_durl(self):
            audio_request = requests.get(self.audio_durl_api, headers = get_header(), proxies = get_proxy())
            audio_json = json.loads(audio_request.text)

            self.audio_durl = audio_json["data"]["cdns"][0]

        def merge_video_audio(self, out_name: str, pid: str):
            cmd = '''cd {0} && {1} -v quiet -i audio_{2}.mp3 -i video_{2}.mp4 -acodec copy -vcodec copy "{4}.mp4"&& {3} video_{2}.mp4 audio_{2}.mp3'''.format(Config.download_path, Config.FFMPEG_PATH, pid, Config.del_cmd, out_name)
            
            self.merge_process = subprocess.Popen(cmd, shell = True)
            self.merge_process.wait()

        def start_download(self):
            self.started_download = True
            DownloadWindow.downloading = True

            self.speed_lab.SetLabel("正在开始下载...")

            self.status = "downloading"

            downloader.start_listening(self.onStart, self.onDownload, self.onDownloadCompleted, self.OnError)

            if self.type != AudioInfo:
                self.get_video_durl()

                self.video_path = os.path.join(Config.download_path, "video_{}.mp4".format(self.pid))
                self.audio_path = os.path.join(Config.download_path, "audio_{}.mp3".format(self.pid))

                self.gid.append(downloader.download(self.video_durl, self.get_full_url, "video_{}.mp4".format(self.pid)))
                self.gid.append(downloader.download(self.audio_durl, self.get_full_url, "audio_{}.mp3".format(self.pid)))

            else:
                self.get_audio_durl()

                self.audio_path = os.path.join(Config.download_path, "{}.mp3".format(self.title))

                self.gid.append(downloader.download(self.audio_durl, self.get_full_url, "{}.mp3".format(self.title)))

        def onStart(self, gid: str):
            time.sleep(1)

            video_size = audio_size = 0

            if os.path.exists(self.video_path):
                video_size = os.path.getsize(self.video_path)

            if os.path.exists(self.audio_path):
                audio_size = os.path.getsize(self.audio_path)
            
            self.size_lab.SetLabel(format_size((video_size + audio_size) / 1024))

        def onDownload(self, progress: int, speed: str):
            self.gauge.SetValue(progress)
            self.speed_lab.SetLabel(speed)

            taskbar.SetProgressValue(progress)

        def onPause(self):
            if self.started_download:
                downloader.on_pause()
        
            self.speed_lab.SetLabel("暂停中...")

        def onResume(self):
            if self.started_download:
                downloader.on_unpause()
                self.speed_lab.SetLabel("")
            else:
                self.speed_lab.SetLabel("等待下载...")

        def onCancel(self):
            del DownloadWindow.download_list[self.pid]

            downloader.stop_listen()
            self.speed_lab.SetLabel("正在取消下载...")

            for i in self.gid:
                try:
                    downloader.force_remove(i)
                except:
                    pass
            
            taskbar.SetProgressState(TaskBarProgress.TBPF_NOPROGRESS)
            DownloadWindow.downloading = False

        def OnError(self):
            DownloadWindow.downloading = False

            del DownloadWindow.download_list[self.pid]

            self.speed_lab.SetLabel("下载失败")
            self.speed_lab.SetForegroundColour("red")
            self.pause_btn.Enable(False)
            self.open_btn.Enable(False)
            self.cancel_btn.SetToolTip("清除记录")

            self.status = "error"
            self.onComplete_(iserror = True)

        def onMerge(self):
            self.speed_lab.SetLabel("正在合成视频...")
            self.onMerge_()
            self.pause_btn.Enable(False)

        def onDownloadCompleted(self):
            DownloadWindow.downloading = False

            self.onMerge()
            if self.type != AudioInfo:
                self.merge_video_audio(self.title, self.pid)
                
            self.onMergeCompleted()

        def onMergeCompleted(self):
            del DownloadWindow.download_list[self.pid]

            self.status = "completed"
            self.onComplete_()

            self.speed_lab.SetLabel("下载完成")
            self.cancel_btn.SetToolTip("清除记录")
            self.gauge.SetValue(100)

            taskbar.SetProgressState(TaskBarProgress.TBPF_NOPROGRESS)

ThreadPool = ThreadPoolExecutor()
downloader = Downloader()
taskbar = TaskBarProgress()