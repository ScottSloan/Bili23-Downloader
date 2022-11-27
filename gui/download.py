import wx
import os
import re
import json
import requests
import subprocess
import wx.lib.scrolledpanel
from threading import Thread

from utils.video import VideoInfo
from utils.bangumi import BangumiInfo
from utils.audio import AudioInfo
from utils.download import Downloader
from utils.config import Config
from utils.tools import *

from .templates import Frame
from .notification import Notification

class DownloadInfo:
    download_list = {}

    download_count = 0

    download_task = 0

class ProcessError(Exception):
    pass

class DownloadWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "下载管理", False)

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        self.SetBackgroundColour("white")
    
        self.list_panel = WindowPanel(self)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def onClose(self, event):
        self.Hide()

    def add_download_task(self, type, quality_id):
        if type == VideoInfo:
            self.list_panel.download_list_panel.add_panel(self.get_video_download_list(quality_id))

        elif type == BangumiInfo:
            self.list_panel.download_list_panel.add_panel(self.get_bangumi_download_list(quality_id))

        elif type == AudioInfo:
            self.list_panel.download_list_panel.add_panel(self.get_audio_download_list())

        self.list_panel.task_lab.SetLabel("{} 个任务正在下载".format(len(DownloadInfo.download_list)))

        Thread(target = self.start_download).start()
    
    def get_download_info(self, url, title, type, bvid = None, cid = None, sid = None, lyric = None, quality_id = None):
        DownloadInfo.download_count += 1

        return {
            "id": DownloadInfo.download_count,
            "url": url,
            "title": title,
            "bvid": bvid,
            "cid": cid,
            "sid": sid,
            "lyric": lyric,
            "quality_id": quality_id,
            "onMerge": self.onMerge, 
            "onComplete": self.onComplete,
            "update_title": self.update_title,
            "type": type
        }

    def get_video_download_list(self, quality_id):
        download_list = []

        if VideoInfo.multiple:
            for i in VideoInfo.down_pages:
                info = self.get_download_info(VideoInfo.url, i["part"], "video", bvid = VideoInfo.bvid, cid = i["cid"], quality_id = quality_id)

                download_list.append(info)

        elif VideoInfo.collection:
            for i in VideoInfo.down_pages:
                info = self.get_download_info(VideoInfo.url, i["title"], "video", bvid = i["bvid"], cid = i["cid"], quality_id = quality_id)

                download_list.append(info)
        else:
            info = self.get_download_info(VideoInfo.url, VideoInfo.title, "video", bvid = VideoInfo.bvid, cid = VideoInfo.cid, quality_id = quality_id)

            download_list.append(info)

        return download_list

    def get_bangumi_download_list(self, quality_id: int) -> list:
        download_list = []

        for i in BangumiInfo.down_episodes:
            info = self.get_download_info(BangumiInfo.url, format_bangumi_title(i), "video", bvid = i["bvid"], cid = i["cid"], quality_id = quality_id)

            download_list.append(info)

        return download_list

    def get_audio_download_list(self):
        download_list = []

        for i in AudioInfo.down_list:
            info = self.get_download_info(AudioInfo.url, i["title"], "audio", sid = i["id"], lyric = i["lyric"])
        
            download_list.append(info)

        return download_list

    def start_download(self):
        keys = [key for key, value in DownloadInfo.download_list.items() if value.status == "waiting"]
        
        for i in keys:
            value = DownloadInfo.download_list[i]
                            
            value.start_download()

            break

    def onMerge(self):
        if len(DownloadInfo.download_list) != 0:
            Thread(target = self.start_download).start()

    def onComplete(self):
        if DownloadInfo.download_task == 0:
            if Config.show_notification:
                self.RequestUserAttention(flags = wx.USER_ATTENTION_INFO)

        self.update_title()

    def update_title(self, error = False):
        if DownloadInfo.download_task != 0:
            self.list_panel.task_lab.SetLabel("{} 个任务正在下载".format(DownloadInfo.download_task))
        else:
            self.list_panel.task_lab.SetLabel("下载管理")
            
            if Config.show_notification and not error:
                Notification.show_notification_download_finish()

        if error and Config.show_notification:
            Notification.show_notification_download_error()

class WindowPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.task_lab = wx.StaticText(self, -1, "下载管理")
        self.task_lab.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑"))

        top_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)
        self.download_list_panel = DownloadListPanel(self, size = self.FromDIP((650, 250)))
        bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        botton_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.open_btn = wx.Button(self, -1, "打开下载目录", size = self.FromDIP((100, 30)))
        self.clear_btn = wx.Button(self, -1, "清除下载记录", size = self.FromDIP((100, 30)))

        botton_hbox.Add(self.open_btn, 0, wx.ALL, 10)
        botton_hbox.AddStretchSpacer(1)
        botton_hbox.Add(self.clear_btn, 0, wx.ALL, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.task_lab, 0, wx.ALL, 10)
        vbox.Add(top_border, 0, wx.EXPAND)
        vbox.Add(self.download_list_panel, 1, wx.EXPAND)
        vbox.Add(bottom_border, 0, wx.EXPAND)
        vbox.Add(botton_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

        vbox.Fit(self.Parent)

    def Bind_EVT(self):
        self.open_btn.Bind(wx.EVT_BUTTON, self.open_btn_EVT)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.clear_btn_EVT)

    def open_btn_EVT(self, event):
        if Config.platform.startswith("Windows"):
            os.startfile(Config.download_path)
        else:
            os.system('xdg-open "{}"'.format(Config.download_path))

    def clear_btn_EVT(self, event):
        keys = [key for key, value in DownloadInfo.download_list.items() if value.status == "completed" or value.status == "error"]
        
        for i in keys:
            value = DownloadInfo.download_list[i]
            value.Destroy()

            self.layout_sizer()

            del DownloadInfo.download_list[i]

    def layout_sizer(self):
        self.download_list_panel.main_sizer.Layout()
        self.download_list_panel.SetupScrolling(scroll_x = False)

class DownloadListPanel(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, parent, size):
        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent, -1, size = size)

        self.init_UI()

        self.empty = False

    def init_UI(self):
        self.SetBackgroundColour('white')

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.main_sizer)

    def add_panel(self, info: list):
        for item in info:
            item["layout_sizer"] = self.Parent.layout_sizer

            panel = DownloadItemPanel(self, item)

            self.main_sizer.Add(panel, 0, wx.EXPAND)

            DownloadInfo.download_task += 1
            DownloadInfo.download_list[item["id"]] = panel

        self.SetupScrolling(scroll_x = False)

class DownloadItemPanel(wx.Panel):
    def __init__(self, parent, info: dict):
        self.info = info

        wx.Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.status = "waiting"
        self.started_download = False

    def init_UI(self):
        self.title_lab = wx.StaticText(self, -1, self.info["title"], size = self.FromDIP((300, 24)), style = wx.ST_ELLIPSIZE_END)

        self.quality_lab = wx.StaticText(self, -1)
        self.quality_lab.SetForegroundColour(wx.Colour(108, 108, 108))
        
        self.size_lab = wx.StaticText(self, -1, "-")
        self.size_lab.SetForegroundColour(wx.Colour(108, 108, 108))

        quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        quality_hbox.Add(self.quality_lab, 0, wx.ALL & (~wx.TOP), 10)
        quality_hbox.AddSpacer(self.FromDIP(75))
        quality_hbox.Add(self.size_lab, 0, wx.ALL & (~wx.TOP), 10)

        info_vbox = wx.BoxSizer(wx.VERTICAL)
        info_vbox.Add(self.title_lab, 0, wx.ALL, 10)
        info_vbox.Add(quality_hbox, 0, wx.EXPAND)

        self.gauge = wx.Gauge(self, -1, 100)

        self.speed_lab = wx.StaticText(self, -1, "等待下载...")
        self.speed_lab.SetForegroundColour(wx.Colour(108, 108, 108))

        gauge_vbox = wx.BoxSizer(wx.VERTICAL)
        gauge_vbox.Add(self.gauge, 0, wx.ALL | wx.EXPAND, 10)
        gauge_vbox.Add(self.speed_lab, 0, wx.ALL & (~wx.TOP), 10)

        self.pause_btn = wx.BitmapButton(self, -1, wx.Bitmap(Config.res_pause), size = self.FromDIP((16, 16)))
        self.pause_btn.SetToolTip("暂停下载")
        self.cancel_btn = wx.BitmapButton(self, -1, wx.Bitmap(Config.res_delete), size = self.FromDIP((16, 16)))
        self.cancel_btn.SetToolTip("取消下载")

        panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel_hbox.Add(info_vbox, 1, wx.EXPAND)
        panel_hbox.Add(gauge_vbox, 0, wx.EXPAND)
        panel_hbox.AddSpacer(self.FromDIP(10))
        panel_hbox.Add(self.pause_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.Add(self.cancel_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        panel_vbox = wx.BoxSizer(wx.VERTICAL)
        panel_vbox.Add(panel_hbox, 1, wx.EXPAND)
        panel_vbox.Add(border, 0, wx.EXPAND)

        self.SetSizer(panel_vbox)

    def Bind_EVT(self):
        self.pause_btn.Bind(wx.EVT_BUTTON, self.pause_btn_EVT)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.cancel_btn_EVT)

    def pause_btn_EVT(self, event):
        if self.status == "waiting" or self.status == "downloading":
            self.status = "pause"
            self.pause_btn.SetBitmap(wx.Bitmap(Config.res_continue))
            self.pause_btn.SetToolTip("继续下载")

            wx.CallAfter(self.onPause)
        else:
            if not self.started_download:
                wx.CallAfter(self.start_download)

            self.status = "downloading"

            self.pause_btn.SetBitmap(wx.Bitmap(Config.res_pause))
            self.pause_btn.SetToolTip("暂停下载")

            wx.CallAfter(self.onContinue)

    def cancel_btn_EVT(self, event):
        if self.started_download:
            self.downloader.onCancel()

        del DownloadInfo.download_list[self.info["id"]]

        if self.status != "completed" and self.status != "error":
            DownloadInfo.download_task -= 1

        self.Destroy()

        self.info["layout_sizer"]()
        self.info["update_title"]()

    def show_video_quality(self):
        quality_desc = [key for key, value in quality_wrap.items() if value == self.utils.quality][0]

        self.quality_lab.SetLabel(quality_desc)

    def show_audio_info(self):
        self.quality_lab.SetLabel("音乐")

    def onStart(self):
        self.speed_lab.SetLabel("")
        self.size_lab.SetLabel(format_size(self.downloader.total_size / 1024))

    def onDownload(self, progress: int, speed: str):
        self.gauge.SetValue(progress)
        self.speed_lab.SetLabel(speed)

    def onPause(self):
        if self.started_download:
            self.downloader.onPause()  
    
        self.speed_lab.SetLabel("暂停中...")

    def onContinue(self):
        if self.started_download:
            self.speed_lab.SetLabel("")
            self.downloader.onContinue()
        else:
            self.speed_lab.SetLabel("等待下载...")

    def onDownloadComplete(self):
        self.onMerge()

    def onMergeComplete(self):
        self.status = "completed"

        self.speed_lab.SetLabel("下载完成")
        self.cancel_btn.SetToolTip("清除记录")
        self.gauge.SetValue(100)

        DownloadInfo.download_task -= 1

        wx.CallAfter(self.info["onComplete"])

    def onMerge(self):
        self.speed_lab.SetLabel("正在合成视频...")
        self.utils.merge_video(self.onMergeComplete)
        self.pause_btn.Enable(False)

        self.status = "merging"

        wx.CallAfter(self.info["onMerge"])

    def onError(self):
        self.speed_lab.SetLabel("下载失败")
        self.speed_lab.SetForegroundColour("red")
        self.pause_btn.Enable(False)
        self.cancel_btn.SetToolTip("清除记录")

        self.status = "error"
        DownloadInfo.download_task -= 1
        
        self.info["update_title"](error = True)

        raise ProcessError("下载失败：无法获取下载链接")

    def start_download(self):
        self.started_download = True
        self.status = "downloading"

        self.downloader = Downloader(self.onStart, self.onDownload, self.onDownloadComplete)
        self.utils = DownloadUtils(self.info, self.downloader, self.onError)
        
        if self.info["type"] != "audio":
            self.utils.get_video_durl()

            self.show_video_quality()

            self.utils.add_video_durl_to_downloader()
        else:
            self.utils.get_audio_durl()

            self.show_audio_info()

            self.utils.add_audio_durl_to_downloader()

class DownloadUtils:
    def __init__(self, info, downloader, onError):
        self.info, self.downloader, self.onError = info, downloader, onError

    @property
    def video_durl_api(self):
        return "https://api.bilibili.com/x/player/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(self.info["bvid"], self.info["cid"])

    @property
    def bangumi_durl_api(self):
        return "https://api.bilibili.com/pgc/player/web/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(self.info["bvid"], self.info["cid"])

    @property
    def audio_durl_api(self):
        return "https://www.bilibili.com/audio/music-service-c/web/url?sid={}".format(self.info["sid"])

    @property
    def get_full_url(self):
        return "https://www.bilibili.com/video/" + self.info["bvid"]

    def get_video_durl(self):
        if Config.mode == "api":
            json_dash = self.get_video_durl_via_api()
        elif Config.mode == "html":
            json_dash = self.get_video_durl_via_html()

        self.quality = json_dash["video"][0]["id"] if json_dash["video"][0]["id"] < self.info["quality_id"] else self.info["quality_id"]

        temp_video_durl = [i["baseUrl"] for i in json_dash["video"] if i["id"] == self.quality]
        self.video_durl = temp_video_durl[codec_wrap[Config.codec]] if len(temp_video_durl) > 1 else temp_video_durl[0]
        
        temp_audio_durl = sorted(json_dash["audio"], key = lambda x: x["id"], reverse = True)
        self.audio_durl = [i for i in temp_audio_durl if (i["id"] - 30200) == self.quality or (i["id"] - 30200) < self.quality][0]["baseUrl"]

    def get_video_durl_via_api(self):
        type = self.info["type"]

        try:
            if type == "video":
                request = requests.get(self.video_durl_api, headers = get_header(self.info["url"], Config.user_sessdata), proxies = get_proxy())
            elif type == "bangumi":
                request = requests.get(self.bangumi_durl_api, headers = get_header(self.info["url"], Config.user_sessdata), proxies = get_proxy())
        
            request_json = json.loads(request.text)
            json_dash = request_json["result"]["dash"]

        except:
            wx.CallAfter(self.onError)

        return json_dash

    def get_video_durl_via_html(self):
        re_pattern = r"window.__playinfo__=(.*?)</script>"
        
        request = requests.get(self.get_full_url, headers = get_header(self.info["url"], Config.user_sessdata), proxies = get_proxy())

        try:
            json_raw = re.findall(re_pattern, request.text, re.S)[0]
            return json.loads(json_raw)["data"]["dash"]
        
        except:
            wx.CallAfter(self.onError)

    def get_audio_durl(self):
        audio_request = requests.get(self.audio_durl_api, headers = get_header(self.info["url"]), proxies = get_proxy())
        audio_json = json.loads(audio_request.text)

        self.audio_durl = audio_json["data"]["cdns"][0]
        
    def add_video_durl_to_downloader(self):
        video_info = {
            "url": self.video_durl,
            "referer_url": self.info["url"],
            "file_name": "video_{}.mp4".format(self.info["id"])
        }

        audio_info = {
            "url": self.audio_durl,
            "referer_url": self.info["url"],
            "file_name": "audio_{}.mp3".format(self.info["id"])
        }

        self.get_danmaku()
        self.get_subtitle()

        self.downloader.start_download([video_info, audio_info])

    def add_audio_durl_to_downloader(self):
        audio_info = {
            "url": self.audio_durl,
            "referer_url": self.info["url"],
            "file_name": "{}.mp3".format(get_legal_name(self.info["title"]))
        }

        self.get_lyric()

        self.downloader.start_download([audio_info])

    def merge_video(self, onMergeComplete):
        if self.info["type"] == "audio":
            wx.CallAfter(onMergeComplete)
            return
            
        id = self.info["id"]
        title = get_legal_name(self.info["title"])

        cmd = f'''cd "{Config.download_path}" && ffmpeg -v quiet -i audio_{id}.mp3 -i video_{id}.mp4 -acodec copy -vcodec copy "{title}.mp4"'''
            
        self.merge_process = subprocess.Popen(cmd, shell = True)
        self.merge_process.wait()

        remove_files(Config.download_path, [f"video_{id}.mp4", f"audio_{id}.mp3"])
        
        wx.CallAfter(onMergeComplete)
    
    def get_danmaku(self):
        if not Config.save_danmaku:
            return
        
        durl = "https://api.bilibili.com/x/v1/dm/list.so?oid={}".format(self.info["cid"])

        get_file_from_url(durl, "{}.xml".format(self.info["title"]))

    def get_subtitle(self):
        if not Config.save_subtitle:
            return

        subtitle_url = "https://api.bilibili.com/x/player.so?id=cid:{}&bvid={}".format(self.info["cid"], self.info["bvid"])
        req = requests.get(subtitle_url, headers = get_header(), proxies = get_proxy())

        subtitle_raw = re.findall(r'<subtitle>(.*?)</subtitle>', req.text)[0]
        subtitle_json = json.loads(subtitle_raw)["subtitles"]

        subtitle_num = len(subtitle_json)

        if subtitle_num == 0:
            return

        elif subtitle_num == 1:
            durl = "https:{}".format(subtitle_json[0]["subtitle_url"])
        
            get_file_from_url(durl, "{}.srt".format(self.info["title"]), True)

        else:
            for i in range(subtitle_num):
                lan_name = subtitle_json[i]["lan_doc"]
                durl = "https:{}".format(subtitle_json[i]["subtitle_url"])
            
                get_file_from_url(durl, "({}) {}.srt".format(lan_name, self.info["title"]), True)

    def get_lyric(self):         
        if not Config.save_lyric and self.info["lyric"] == "":
            return
    
        get_file_from_url(self.info["lyric"], "{}.lrc".format(self.info["title"]))
