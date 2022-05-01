import wx
import subprocess
import wx.lib.scrolledpanel
from concurrent.futures import ThreadPoolExecutor

from utils.video import VideoInfo
from utils.bangumi import BangumiInfo
from utils.audio import AudioInfo
from utils.download import Downloader
from utils.tools import *
from utils.config import Config

from gui.templates import Frame, Message
from gui.taskbar import TaskBarProgress

class DownloadList:
    download_count = 0
    download_list = {}
    
    downloading_count = 0

class DownloadWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "下载管理", (680, 420), False)

        self.SetBackgroundColour("white")
     
        self.list_panel = ListPanel(self)

        self.Bind_EVT()

        taskbar.Bind(self.GetHandle())

        #self.list_panel.download_list_panel.add_panel(0, "Video Title", "BVxxxxxx", 0, "1080P", 0, VideoInfo, self.on_finish, self.on_merge)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.On_Close)

    def On_Close(self, event):
        self.Hide()

    def add_download_task(self, theme, quality_desc: str, quality_id: int):
        if theme == VideoInfo:
            if VideoInfo.multiple:
                for i in VideoInfo.down_pages:
                    self.list_panel.download_list_panel.add_panel(DownloadList.download_count, i["part"], VideoInfo.bvid, i["cid"], quality_desc, quality_id, theme, self.on_finish, self.on_merge)

            elif VideoInfo.collection:
                for i in VideoInfo.down_pages:
                    self.list_panel.download_list_panel.add_panel(DownloadList.download_count, i["title"], i["bvid"], i["cid"], quality_desc, quality_id, theme, self.on_finish, self.on_merge)

            else:
                self.list_panel.download_list_panel.add_panel(DownloadList.download_count, VideoInfo.title, VideoInfo.bvid, VideoInfo.cid, quality_desc, quality_id, theme, self.on_finish, self.on_merge)

        elif theme == BangumiInfo:
            for i in BangumiInfo.down_episodes:
                self.list_panel.download_list_panel.add_panel(DownloadList.download_count, i["share_copy"], i["bvid"], i["cid"], quality_desc, quality_id, theme, self.on_finish, self.on_merge)

        else:
            self.list_panel.download_list_panel.add_panel(DownloadList.download_count, AudioInfo.title, None, None, None, None ,theme, self.on_finish, self.on_merge)

        self.list_panel.task_lb.SetLabel("{} 个任务正在下载".format(len(DownloadList.download_list)))

        self.start_download()

    def start_download(self):
        for key, value in DownloadList.download_list.items():
            panel = value[1]
            if panel.download_info["status"] == "waiting":
                panel.start_download()
                break

    def on_merge(self):
        if len(DownloadList.download_list) != 0:
            wx.CallAfter(self.start_download)

    def on_finish(self, iserror = False, video_name = None, update_title_only = False):
        self.update_title(len(DownloadList.download_list))

        if update_title_only: return

        if Config.show_notification:
            if not iserror:
                Message.show_notification_finish()
                self.RequestUserAttention(flags = wx.USER_ATTENTION_INFO)
            else:
                Message.show_notification_error(video_name)
                self.RequestUserAttention(flags = wx.USER_ATTENTION_ERROR)

    def update_title(self, count: int):
        if count != 0:
            self.list_panel.task_lb.SetLabel("{} 个任务正在下载".format(count))
        else:
            self.list_panel.task_lb.SetLabel("下载管理")

class ListPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        self.init_UI()
        self.Bind_EVT()

    def init_UI(self):
        self.task_lb = wx.StaticText(self, -1, "下载管理")
        self.task_lb.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑"))

        top_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        self.download_list_panel = DownloadListPanel(self)

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
        if Config.platform.startswith("Windows"):
            os.startfile(Config.download_path)
        else:
            os.system('xdg-open "{}"'.format(Config.download_path))

    def clear_EVT(self, event):
        sizer = self.download_list_panel.main_sizer

        for i in range(len(sizer.GetChildren())):
            child = sizer.GetChildren()[0].GetWindow()
            status = child.download_info["status"]
            if status == "completed" or status == "cancelled":
                child.Destroy()
                sizer.Layout()
                self.download_list_panel.SetupScrolling(scroll_x = False)
                continue

class DownloadListPanel(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, parent):
        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent)

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.empty = False

        self.SetBackgroundColour('white')

        self.SetSizer(self.main_sizer)
    
    def add_panel(self, pid, title, bvid, cid, quality_desc, quality_id, theme, on_finish, on_merge):
        download_info = {}

        download_info["pid"] = pid
        download_info["title"] = get_legal_name(title)
        download_info["bvid"] = bvid
        download_info["cid"] = cid
        download_info["quality_desc"] = quality_desc
        download_info["quality_id"] = quality_id
        download_info["theme"] = theme
        download_info["total_size"] = 0
        download_info["on_finish"] = on_finish
        download_info["on_merge"] = on_merge
        download_info["status"] = "waiting"

        panel = DownloadItemPanel(self, download_info, pid)

        self.main_sizer.Add(panel, 0, wx.EXPAND)

        self.SetupScrolling(scroll_x = False)

        DownloadList.download_count += 1

class DownloadItemPanel(wx.Panel):
    def __init__(self, parent, download_info, pid: int):
        self.parent = parent
        DownloadList.download_list[pid] = [download_info, self]
        wx.Panel.__init__(self, parent)

        self.init_UI(pid)
        self.Bind_EVT()

    def init_UI(self, pid: int):
        self.download_utils = DownloadItemUtils(pid)
        self.download_info = DownloadList.download_list[pid][0]

        self.title_lb = wx.StaticText(self, -1, self.download_info["title"], style = wx.ST_ELLIPSIZE_END | wx.ST_NO_AUTORESIZE)

        self.quality_lb = wx.StaticText(self, -1, self.download_info["quality_desc"] if self.download_info["theme"] != AudioInfo else "")
        self.quality_lb.SetForegroundColour(wx.Colour(108, 108, 108))
        self.size_lb = wx.StaticText(self, -1, "-")
        self.size_lb.SetForegroundColour(wx.Colour(108, 108, 108))

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.quality_lb, 0, wx.ALL & (~wx.TOP), 10)
        hbox1.AddSpacer(self.FromDIP(75))
        hbox1.Add(self.size_lb, 0, wx.ALL & (~wx.TOP), 10)

        vbox1 = wx.BoxSizer(wx.VERTICAL)
        vbox1.Add(self.title_lb, 1, wx.ALL, 10)
        vbox1.Add(hbox1, 0, wx.EXPAND)

        self.gauge = wx.Gauge(self, -1, 100)

        self.speed_lb = wx.StaticText(self, -1, "等待下载...")
        self.speed_lb.SetForegroundColour(wx.Colour(108, 108, 108))

        vbox2 = wx.BoxSizer(wx.VERTICAL)
        vbox2.Add(self.gauge, 0, wx.ALL | wx.EXPAND, 10)
        vbox2.Add(self.speed_lb, 0, wx.ALL & (~wx.TOP), 10)

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
        if self.download_info["status"] == "downloading": return

        self.download_info["status"] = "downloading"

        if self.download_info["theme"] != AudioInfo:
            get_danmaku_subtitle_lyric(self.download_info["title"], self.download_info["cid"], self.download_info["bvid"])
        else:
            get_danmaku_subtitle_lyric(self.download_info["title"], None, None)
        
        self.download_utils.start_download()

    def pause_EVT(self, event):
        if self.download_info["status"] == "waiting" or self.download_info["status"] == "downloading":
            self.download_info["status"] = "pause"
            self.pause_btn.SetBitmap(wx.Bitmap(Config.res_resume))
            self.pause_btn.SetToolTip("继续下载")

            self.download_utils.on_pause()

            taskbar.SetProgressState(TaskBarProgress.TBPF_PAUSED)

        else:
            self.download_info["status"] = "downloading"
            self.pause_btn.SetBitmap(wx.Bitmap(Config.res_pause))
            self.pause_btn.SetToolTip("暂停下载")

            self.download_utils.on_resume()

            taskbar.SetProgressState(TaskBarProgress.TBPF_NORMAL)

    def open_EVT(self, event):
        if Config.platform.startswith("Windows"):
            os.startfile(Config.download_path)
        else:
            os.system('xdg-open "{}"'.format(Config.download_path))

    def cancel_EVT(self, event):
        status = self.download_info["status"]
        if status == "downloading" or status == "waiting":
            status = "cancelled"
            self.download_utils.on_cancel()
        
        if status != "error":
            self.download_info["on_finish"](update_title_only = True)

        self.Destroy()
        self.parent.main_sizer.Layout()
        self.parent.SetupScrolling(scroll_x = False)

class DownloadItemUtils:
    def __init__(self, pid: int) -> None:
        self.download_info = DownloadList.download_list[pid][0]
        self.panel = DownloadList.download_list[pid][1]

        self.downloader = Downloader(self.on_start, self.on_download)

    def video_durl_api(self) -> str:
        return "https://api.bilibili.com/x/player/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(self.download_info["bvid"], self.download_info["cid"])

    def bangumi_durl_api(self) -> str:
        return "https://api.bilibili.com/pgc/player/web/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(self.download_info["bvid"], self.download_info["cid"])

    def audio_durl_api(self) -> str:
        return "https://www.bilibili.com/audio/music-service-c/web/url?sid={}".format(AudioInfo.sid)

    def get_full_url(self) -> str:
        return "https://www.bilibili.com/video/" + self.download_info["bvid"]

    def get_durl(self):
        self.referer_url = self.get_full_url()
        self.pid = self.download_info["pid"]

        try:
            if self.download_info["theme"] == VideoInfo:
                request = requests.get(self.video_durl_api(), headers = get_header(self.referer_url, Config.user_sessdata), proxies = get_proxy())
                request_json = json.loads(request.text)
                json_dash = request_json["data"]["dash"]
            else:
                request = requests.get(self.bangumi_durl_api(), headers = get_header(self.referer_url, Config.user_sessdata), proxies = get_proxy())
                request_json = json.loads(request.text)
                json_dash = request_json["result"]["dash"]
        except:
            self.on_error()

        quality = json_dash["video"][0]["id"] if json_dash["video"][0]["id"] < self.download_info["quality_id"] else self.download_info["quality_id"]

        temp_video_durl = [i["baseUrl"] for i in json_dash["video"] if i["id"] == quality]
        self.video_durl = temp_video_durl[Config.codec] if len(temp_video_durl) > 1 else temp_video_durl[0]
        
        temp_audio_durl = sorted(json_dash["audio"], key = lambda x: x["id"], reverse = True)
        self.audio_durl = [i for i in temp_audio_durl if (i["id"] - 30200) == quality or (i["id"] - 30200) < quality][0]["baseUrl"]

    def get_audio_durl(self):
        self.referer_url = "https://www.bilibili.com/audio/au{}".format(AudioInfo.sid)

        audio_request = requests.get(self.audio_durl_api(), headers = get_header(), proxies = get_proxy())
        audio_json = json.loads(audio_request.text)

        self.audio_durl = audio_json["data"]["cdns"][0]

    def merge_video_audio(self, out_name: str, pid: str):
        cmd = '''cd {0} && {1} -v quiet -i audio_{2}.mp3 -i video_{2}.mp4 -acodec copy -vcodec copy "{4}.mp4"&& {3} video_{2}.mp4 audio_{2}.mp3'''.format(Config.download_path, Config.ffmpeg_path, pid, Config.del_cmd, out_name)
        
        self.merge_process = subprocess.Popen(cmd, shell = True)
        self.merge_process.wait()

    def start_download(self):
        if self.download_info["theme"] != AudioInfo:
            self.get_durl()

            self.downloader.add_url(self.video_durl, self.referer_url, "video_{}.mp4".format(self.pid))
            self.downloader.add_url(self.audio_durl, self.referer_url, "audio_{}.mp3".format(self.pid))

            if self.download_info["status"] == "cancelled": return

            self.on_merge()
            self.merge_video_audio(self.download_info["title"], self.pid)
            self.on_finish()
        else:
            self.get_audio_durl()

            self.downloader.add_url(self.audio_durl, self.referer_url, "{}.mp3".format(self.download_info["title"]))

            self.on_finish()

    def on_start(self, size: str):
        self.download_info["total_size"] += size

        taskbar.SetProgressState(TaskBarProgress.TBPF_NORMAL)

    def on_download(self, progress: int, speed: str, size: str):
        self.panel.gauge.SetValue(progress)
        self.panel.speed_lb.SetLabel(speed)
        self.panel.size_lb.SetLabel(size)

        taskbar.SetProgressValue(progress)

    def on_pause(self):
        self.downloader.on_pause()
        self.panel.speed_lb.SetLabel("暂停中...")

    def on_resume(self):
        if self.downloader.started_download:
            self.downloader.on_resume()
            self.panel.speed_lb.SetLabel("")
        else:
            self.panel.start_download()

    def on_cancel(self):
        del DownloadList.download_list[self.download_info["pid"]]
        self.downloader.on_cancel()

    def on_error(self):
        del DownloadList.download_list[self.download_info["pid"]]

        self.panel.speed_lb.SetLabel("下载失败")
        self.panel.speed_lb.SetForegroundColour("red")
        self.panel.pause_btn.Enable(False)
        self.panel.open_btn.Enable(False)
        self.panel.cancel_btn.SetToolTip("清除记录")

        self.download_info["status"] = "error"
        self.download_info["on_finish"]("True", self.download_info["title"])

    def on_merge(self):
        self.panel.speed_lb.SetLabel("正在合成...")
        self.panel.size_lb.SetLabel(format_size(self.download_info["total_size"]))
        self.download_info["on_merge"]()
        self.panel.pause_btn.Enable(False)

    def on_finish(self):
        del DownloadList.download_list[self.download_info["pid"]]

        self.panel.size_lb.SetLabel(format_size(self.download_info["total_size"]))
        self.download_info["status"] = "completed"
        self.download_info["on_finish"]()

        self.panel.speed_lb.SetLabel("下载完成")
        self.panel.cancel_btn.SetToolTip("清除记录")
        self.panel.gauge.SetValue(100)

        taskbar.SetProgressState(TaskBarProgress.TBPF_NOPROGRESS)

ThreadPool = ThreadPoolExecutor()
taskbar = TaskBarProgress()