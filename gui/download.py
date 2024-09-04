import io
import wx
import json
import time
import wx.adv
import requests
import subprocess
from typing import List

from gui.templates import Frame, ScrolledPanel
from gui.show_error import ShowErrorDialog
from gui.cover_viewer import CoverViewerDialog

from utils.icons import *
from utils.config import Config, Download, conf, Audio
from utils.thread import Thread
from utils.download import Downloader, DownloaderInfo
from utils.tools import *

class DownloadInfo:
    download_list = {}
    no_task = True

class DownloadUtils:
    def __init__(self, info: dict, onError, onComplete):
        self.info, self.onError, self.none_audio, self.merge_error, self.audio_type, self.onComplete = info, onError, False, False, "mp3", onComplete

    def get_video_durl(self):
        json_dash = self.get_video_durl_json()

        self.resolution = json_dash["video"][0]["id"] if json_dash["video"][0]["id"] < self.info["resolution"] else self.info["resolution"]

        temp_video_durl = [i for i in json_dash["video"] if i["id"] == self.resolution]

        self.codec_id = codec_id_map[Config.Download.codec]

        resp = self.has_codec(temp_video_durl, self.codec_id)

        if resp["result"]:
            self.video_durl = temp_video_durl[resp['index']]["backupUrl"][0]
        else:
            self.video_durl = temp_video_durl[0]["backupUrl"][0]
            self.codec_id = 7
        
        if json_dash["audio"]:
            # 除杜比全景声和无损以外
            if Audio.audio_quality != 30250:
                temp_audio_durl = [i for i in json_dash["audio"] if i["id"] == Audio.audio_quality]
                self.audio_durl = temp_audio_durl[0]["backupUrl"][0]

                self.audio_type = "mp3"
            else:
                # 默认为 192K
                self.get_audio_durl_192k(json_dash)

                try:
                    # 无损
                    if json_dash["flac"]:
                        if "audio" in json_dash:
                            if json_dash["flac"]["audio"]:
                                self.audio_durl = json_dash["flac"]["audio"]["backupUrl"][0]

                                self.audio_type = "flac"
                    else:
                        if json_dash["dolby"]:
                            if "audio" in json_dash:
                                if json_dash["dolby"]["audio"]:
                                    # 杜比全景声
                                    self.audio_durl = json_dash["dolby"]["audio"][0]["backupUrl"][0]

                                    self.audio_type = "ec3"
                except:
                    # 无法获取无损或杜比链接，换回 192K
                    self.get_audio_durl_192k(json_dash)

            self.none_audio = False
        else:
            self.none_audio = True
    
    def get_video_durl_json(self):
        try:
            match self.info["type"]:
                case Config.Type.VIDEO:
                    url = f"https://api.bilibili.com/x/player/playurl?bvid={self.info['bvid']}&cid={self.info['cid']}&qn=0&fnver=0&fnval=4048&fourk=1"

                    req = requests.get(url, headers = get_header(self.info["url"], Config.User.sessdata), proxies = get_proxy(), auth = get_auth())
                    resp = json.loads(req.text)
                        
                    json_dash = resp["data"]["dash"]

                case Config.Type.BANGUMI:
                    url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={self.info['bvid']}&cid={self.info['cid']}&qn=0&fnver=0&fnval=12240&fourk=1"
                    
                    req = requests.get(url, headers = get_header(self.info["url"], Config.User.sessdata), proxies = get_proxy(), auth = get_auth())
                    resp = json.loads(req.text)
                        
                    json_dash = resp["result"]["dash"]
        except:
            self.onError()

        return json_dash

    def get_audio_durl_192k(self, json_dash):
        temp_audio_durl = [i for i in json_dash["audio"] if i["id"] == 30280]
        self.audio_durl = temp_audio_durl[0]["backupUrl"][0]

        self.audio_type = "mp3"

    def get_download_info(self) -> list:
        self.get_video_durl()

        video_info = {
            "id": self.info["id"],
            "type": "video",
            "url": self.video_durl,
            "referer_url": self.info["url"],
            "file_name": "video_{}.mp4".format(self.info["id"]),
            "chunk_list": []
        }

        if not self.none_audio:
            audio_info = {
                "id": self.info["id"],
                "type": "audio",
                "url": self.audio_durl,
                "referer_url": self.info["url"],
                "file_name": "audio_{}.{}".format(self.info["id"], self.audio_type),
                "chunk_list": []
            }

        return [video_info] if self.none_audio else [video_info, audio_info]

    def merge_video(self):
        title = get_legal_name(self.info["title"])

        video_f_name = f"video_{self.info['id']}.mp4"
        audio_f_name = f"audio_{self.info['id']}.{self.audio_type}"

        self.merge_error = False

        if self.none_audio:
            cmd = ["cd", Config.Download.path, "&&", "rename", video_f_name, f"{title}.mp4"]
        else:
            cmd = ["cd", Config.Download.path, "&&", Config.FFmpeg.path, "-y", "-i", video_f_name, "-i", audio_f_name, "-acodec", "copy", "-vcodec", "copy", "-strict", "experimental", f"{title}.mp4"]
                
        self.merge_process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        self.merge_process.wait()
        
        if self.merge_process.returncode == 0:
            if Config.Merge.auto_clean:
                remove_files(Config.Download.path, [video_f_name, audio_f_name])
            else:
                cmd = ["cd", Config.Download.path, "&&", "rename", video_f_name, f"{title}_video.mp4", "&&", "rename", audio_f_name, f"{title}_audio.{self.audio_type}"]

                process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
                process.wait()
        else:
            if self.merge_process.stdout:
                output = self.merge_process.stdout.read().decode("cp936").replace("\r\n", "")
            else:
                output = "无法获取错误信息"
            
            self.merge_error_log = {"log": output, "time": get_current_time(), "return_code": self.merge_process.returncode}

            self.merge_error = True

        self.onComplete()

    def has_codec(self, video_durl: List[dict], codec_id: int):
        for index, entry in enumerate(video_durl):
            if entry["codecid"] == codec_id:
                return {
                    "result": True,
                    "index": index
                }
        
        return {
            "result": False,
            "index": None
        }

class DownloadWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "下载管理", style = wx.DEFAULT_FRAME_STYLE & (~wx.MINIMIZE_BOX) & (~wx.MAXIMIZE_BOX))

        self.init_UI()

        self.SetSize(self.FromDIP((780, 500)))

        self.Bind_EVT()

        self.init_utils()
    
    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetPointSize(14)

        self.task_lab = wx.StaticText(self, -1, "下载管理")
        self.task_lab.SetFont(font)

        max_download_lab = wx.StaticText(self, -1, "并行下载数：")
        self.max_download_choice = wx.Choice(self, -1, choices = ["1 个", "2 个", "3 个", "4 个"])

        self.start_all_btn = wx.Button(self, -1, "全部开始")
        self.pause_all_btn = wx.Button(self, -1, "全部暂停")
        self.stop_all_btn = wx.Button(self, -1, "全部取消")

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.Add(max_download_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        action_hbox.Add(self.max_download_choice, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP), 10)
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.start_all_btn, 0, wx.ALL & (~wx.TOP), 10)
        action_hbox.Add(self.pause_all_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        action_hbox.Add(self.stop_all_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        top_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        self.download_list_panel = ScrolledPanel(self, size = self.FromDIP((720, 280)))
        self.download_list_panel.SetBackgroundColour("white")

        bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        botton_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.open_btn = wx.Button(self, -1, "打开下载目录", size = self.FromDIP((100, 30)))
        self.clear_btn = wx.Button(self, -1, "清除下载记录", size = self.FromDIP((100, 30)))

        botton_hbox.Add(self.open_btn, 0, wx.ALL, 10)
        botton_hbox.AddStretchSpacer(1)
        botton_hbox.Add(self.clear_btn, 0, wx.ALL, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.task_lab, 0, wx.ALL, 10)
        vbox.Add(action_hbox, 0, wx.EXPAND)
        vbox.Add(top_border, 0, wx.EXPAND)
        vbox.Add(self.download_list_panel, 1, wx.EXPAND)
        vbox.Add(bottom_border, 0, wx.EXPAND)
        vbox.Add(botton_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

        self.SetBackgroundColour("white")

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.clear_btn.Bind(wx.EVT_BUTTON, self.onClear)
        self.open_btn.Bind(wx.EVT_BUTTON, self.onOpenDir)

        self.max_download_choice.Bind(wx.EVT_CHOICE, self.onMaxDownloadChoice)
        self.stop_all_btn.Bind(wx.EVT_BUTTON, self.onStopAll)
        self.pause_all_btn.Bind(wx.EVT_BUTTON, self.onPauseAll)
        self.start_all_btn.Bind(wx.EVT_BUTTON, self.onStartAll)

    def init_utils(self):
        max_download = Config.Download.max_download

        match max_download:
            case max_download if max_download < 1:
                index = 0
            case 1 | 2 | 3 | 4:
                index = max_download - 1
            case max_download if max_download > 4:
                choices = self.max_download_choice.GetItems()
                choices.append(f"{max_download} 个")

                index = len(choices) - 1

                self.max_download_choice.Set(choices)

        self.max_download_choice.SetSelection(index)

        self.load_tasks()
    
    def load_tasks(self):
        self.download_info = DownloaderInfo()

        tasks = self.download_info.read_info()

        for task_id, info in tasks.items():
            entry = info["base_info"]
            entry["flag"] = True

            if entry["status"] == "downloading":
                entry["status"] = "pause"

            Download.download_list.append(entry)

        if len(tasks):
            self.add_download_item(start_download = False)

    def OnClose(self, event):
        Config.Temp.download_window_pos = self.GetPosition()

        self.Hide()

    def onClear(self, event):
        # 首先遍历下载列表
        callback_list = [value["stop_callback"]for key, value in DownloadInfo.download_list.items() if value["status"] == "completed"]
        self.run_callback_list(callback_list)

        # 遍历scrollpanel中的项目
        callback_list = [item["stop_callback"] for item in self.download_list_panel.GetChildren() if item.info["status"] == "completed"]
        self.run_callback_list(callback_list)

    def onOpenDir(self, event):
        os.startfile(Config.Download.path)

    def onMaxDownloadChoice(self, event):
        index = self.max_download_choice.GetSelection()

        Config.Download.max_download = index + 1

        conf.config.set("download", "max_download", str(Config.Download.max_download))
        conf.config_save()

        self.start_download()

    def onStartAll(self, event):
        callback_list = [value["resume_callback"] for key, value in DownloadInfo.download_list.items() if value["status"] == "pause"]

        self.run_callback_list(callback_list)

    def onPauseAll(self, event):
        callback_list = [value["pause_callback"] for key, value in DownloadInfo.download_list.items() if value["status"] == "downloading"]

        self.run_callback_list(callback_list)

    def onStopAll(self, event):
        callback_list = [value["stop_callback"] for key, value in DownloadInfo.download_list.items() if value["status"] == "wait" or value["status"] == "downloading" or value["status"] == "pause"]

        self.run_callback_list(callback_list)

    def run_callback_list(self, callback_list):
        for callback in callback_list:
            callback(0)

        self.download_list_panel.Layout()
        self.update_task_lab()

    def add_download_item(self, start_download = True):
        multiple = True if len(Download.download_list) > 1 else False
        
        for index, entry in enumerate(Download.download_list):
            if self.is_already_in_list(entry["title"], entry["cid"]):
                continue

            item = DownloadItemPanel(self.download_list_panel, entry)

            self.download_list_panel.sizer.Add(item, 0, wx.EXPAND)

            if multiple and Config.Download.add_number:
                entry["title"] = f"{index + 1} - {entry['title']}"

            entry["start_callback"] = item.start
            entry["pause_callback"] = item.onPauseCallback
            entry["resume_callback"] = item.onResumeCallback
            entry["stop_callback"] = item.onStop

            DownloadInfo.download_list[entry["id"]] = entry

            self.download_list_panel.SetupScrolling(scroll_x = False)
        
        self.layout_sizer()

        if start_download:
            self.start_download()

    def layout_sizer(self):
        self.update_task_lab()

        self.download_list_panel.Layout()
        self.download_list_panel.SetupScrolling(scroll_x = False, scrollToTop = False)
    
    def update_task_lab(self):
        count = 0

        for key, value in DownloadInfo.download_list.items():
            if value["status"] == "wait" or value["status"] == "downloading" or value["status"] == "pause":
                count += 1

        if count:
            self.task_lab.SetLabel(f"{count} 个任务正在下载")

            DownloadInfo.no_task = False
        else:
            self.task_lab.SetLabel("下载管理")

            if not DownloadInfo.no_task:
                self.ShowNotificationToast()

            DownloadInfo.no_task = True
            

    def start_download(self):
        for key, value in DownloadInfo.download_list.items():
            if value["status"] == "wait" and self.get_downloading_count() < Config.Download.max_download:
                value["start_callback"]()
    
    def get_downloading_count(self):
        count = 0

        for key, value in DownloadInfo.download_list.items():
            if value["status"] == "downloading":
                count += 1

        return count
    
    def ShowNotificationToast(self):
        if Config.Download.show_notification:
            self.GetParent().RequestUserAttention(wx.USER_ATTENTION_ERROR) # 任务栏闪烁，需主窗口失去焦点的情况下才有效

            notification = wx.adv.NotificationMessage("下载完成", "所有任务已下载完成", self) # 弹出 Toast 通知

            notification.Show()

    def is_already_in_list(self, title, cid) -> bool:
        for key, value in DownloadInfo.download_list.items():
            if value["title"] == title and value["cid"] == cid:
                return True
            else:
                return False
            
class DownloadItemPanel(wx.Panel):
    def __init__(self, parent, info: dict):
        self.info = info

        wx.Panel.__init__(self, parent)

        self.init_scale()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CentreOnParent()

    def init_utils(self):
        self.downloader = Downloader(self.info, self.onStart, self.onDownload, self.onMerge, self.onError)
        self.utils = DownloadUtils(self.info, self.onError, self.onMergeComplete)

        Thread(target = self.get_preview_pic).start()

        if self.info["flag"]:
            if self.info["complete"]:
                self.size_lab.SetLabel("{}/{}".format(self.info["complete"], self.info["size"]))

                self.gauge.SetValue(self.info["progress"])
            else:
                if self.info["size"]:
                    self.size_lab.SetLabel("0 MB/{}".format(self.info["size"]))

            if self.info["codec"]:
                self.resolution_lab.SetLabel("{}      {}".format(self.info["resolution"], self.info["codec"]))

            if self.info["total_size"]:
                self.total_size = self.info["size"]

            self.update_pause_btn(self.info["status"])

    def init_scale(self):
        self.scale_size = self.FromDIP((16, 16))
        self.is_scaled = True if self.scale_size != (16, 16) else False

    def init_UI(self):
        self.cover = wx.StaticBitmap(self, -1, size = self.FromDIP((112, 63)))
        self.cover.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        self.title_lab = wx.StaticText(self, -1, self.info["title"], size = self.FromDIP((300, 24)), style = wx.ST_ELLIPSIZE_MIDDLE)
        self.title_lab.SetToolTip(self.info["title"])

        self.resolution_lab = wx.StaticText(self, -1)
        self.resolution_lab.SetForegroundColour(wx.Colour(108, 108, 108))
        
        self.size_lab = wx.StaticText(self, -1, "")
        self.size_lab.SetForegroundColour(wx.Colour(108, 108, 108))

        resolution_hbox = wx.BoxSizer(wx.HORIZONTAL)
        resolution_hbox.Add(self.resolution_lab, 0, wx.ALL & (~wx.TOP), 10)
        resolution_hbox.AddStretchSpacer()
        resolution_hbox.Add(self.size_lab, 0, wx.ALL & (~wx.TOP), 10)
        resolution_hbox.AddStretchSpacer()

        info_vbox = wx.BoxSizer(wx.VERTICAL)
        info_vbox.AddSpacer(5)
        info_vbox.Add(self.title_lab, 0, wx.ALL & (~wx.BOTTOM), 10)
        info_vbox.AddStretchSpacer()
        info_vbox.Add(resolution_hbox, 0, wx.EXPAND)
        info_vbox.AddSpacer(5)

        self.gauge = wx.Gauge(self, -1, 100)

        self.speed_lab = wx.StaticText(self, -1, "等待下载...")
        self.speed_lab.SetForegroundColour(wx.Colour(108, 108, 108))

        gauge_vbox = wx.BoxSizer(wx.VERTICAL)
        gauge_vbox.AddSpacer(5)
        gauge_vbox.Add(self.gauge, 0, wx.ALL | wx.EXPAND, 10)
        gauge_vbox.AddStretchSpacer()
        gauge_vbox.Add(self.speed_lab, 0, wx.ALL & (~wx.TOP), 10)
        gauge_vbox.AddSpacer(5)

        pause_image = wx.Image(io.BytesIO(getResumeIcon24())) if self.is_scaled else wx.Image(io.BytesIO(getResumeIcon16()))
        self.pause_btn = wx.BitmapButton(self, -1, pause_image.Scale(self.scale_size[0], self.scale_size[1], wx.IMAGE_QUALITY_HIGH).ConvertToBitmap(), size = self.FromDIP((24, 24)))
        self.pause_btn.SetToolTip("开始下载")

        stop_image = wx.Image(io.BytesIO(getDeleteIcon24())) if self.is_scaled else wx.Image(io.BytesIO(getDeleteIcon16()))
        self.stop_btn = wx.BitmapButton(self, -1, stop_image.Scale(self.scale_size[0], self.scale_size[1], wx.IMAGE_QUALITY_HIGH).ConvertToBitmap(), size = self.FromDIP((24, 24)))
        self.stop_btn.SetToolTip("取消下载")

        panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel_hbox.Add(self.cover, 0, wx.ALL, 10)
        panel_hbox.Add(info_vbox, 0, wx.EXPAND)
        panel_hbox.Add(gauge_vbox, 0, wx.EXPAND)
        panel_hbox.AddStretchSpacer()
        panel_hbox.Add(self.pause_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.Add(self.stop_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.AddSpacer(10)

        border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        self.panel_vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel_vbox.Add(panel_hbox, 1, wx.EXPAND)
        self.panel_vbox.Add(border, 0, wx.EXPAND)

        self.SetSizer(self.panel_vbox)
    
    def Bind_EVT(self):
        self.pause_btn.Bind(wx.EVT_BUTTON, self.onPause_EVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStop)

        self.speed_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowError)
        self.cover.Bind(wx.EVT_LEFT_DOWN, self.onViewCover)

    def get_preview_pic(self):
        req = requests.get(self.info["pic"])

        wx.Image.SetDefaultLoadFlags(0) # 避免出现 iCCP sRGB 警告

        scale_size = self.FromDIP((112, 63))

        self.cover_image = wx.Image(io.BytesIO(req.content))
        self.cover_image_raw = req.content

        image = self.cover_image.Scale(scale_size[0], scale_size[1], wx.IMAGE_QUALITY_HIGH)
        
        self.cover.SetBitmap(image.ConvertToBitmap())

        self.panel_vbox.Layout()

    def start(self):
        self.set_status("downloading")

        self.start_thread = Thread(target = self.thread_start_download)
        self.start_thread.setDaemon(True)
        self.start_thread.start()
    
    def thread_start_download(self):
        self.speed_lab.SetLabel("准备下载...")

        info_list = self.utils.get_download_info()

        self.downloader.start(info_list)

    def onPause_EVT(self, event):
        match self.info["status"]:
            case "wait":
                self.start()
                self.set_status("downloading")
            
            case "downloading":
                self.onPause()
                self.set_status("pause")

            case "pause":
                self.onResume()
                self.set_status("downloading")
            
            case "completed":
                self.onOpenFolder()
                return
            
            case "retry":
                self.onMerge(retry = True)
                return
        
        self.update_pause_btn(self.info["status"])

        self.downloader.download_info.update_base_info_status(self.info["status"])

    def onStart(self):
        self.total_size = format_size(self.downloader.total_size / 1024)

        self.speed_lab.SetLabel("")
        self.size_lab.SetLabel("0 MB/{}".format(self.total_size))

        quality_dict = dict(map(reversed, resolution_map.items()))
        codec_dict = {7: "AVC/H.264", 12: "HEVC/H.265", 13: "AVC"}
        
        self.resolution_lab.SetLabel("{}      {}".format(quality_dict[self.utils.resolution], codec_dict[self.utils.codec_id]))

        self.update_pause_btn("downloading")

        self.Layout()

        base_info = {
            "complete": None,
            "size": self.total_size,
            "resolution": quality_dict[self.utils.resolution],
            "codec": codec_dict[self.utils.codec_id]
        }

        self.downloader.download_info.update_base_info(base_info)
        self.downloader.download_info.update_base_info_status("downloading")

    def onDownload(self, info: dict):
        if self.info["status"] == "downloading":
            self.gauge.SetValue(info["progress"])
            self.speed_lab.SetLabel(info["speed"])
            self.size_lab.SetLabel(info["size"])

            self.downloader.download_info.update_base_info_progress(info["progress"], info["complete"])

            self.Layout()

    def onPause(self):
        self.downloader.onPause()

    def onPauseCallback(self, event):
        self.onPause()
        self.set_status("pause")

        self.update_pause_btn("pause")

    def onResume(self):
        if self.info["download_complete"]:
            self.onMerge()
        else:
            self.downloader.onResume()

    def onResumeCallback(self, event):
        self.onResume()
        self.set_status("downloading")

        self.update_pause_btn("downloading")

    def onStop(self, event):
        self.downloader.onStop()

        self.Hide()

        DownloadInfo.download_list.pop(self.info["id"])

        self.GetParent().GetParent().layout_sizer()

        self.Destroy()

        self.downloader.download_info.clear()

        Thread(target = self.onStopThread).start()

    def onStopThread(self):
        time.sleep(0.5)

        remove_files(Config.Download.path, [f"video_{self.info['id']}.mp4", f"audio_{self.info['id']}.mp3"])
    
    def onMerge(self, retry = False):
        self.set_status("merging")

        self.speed_lab.SetForegroundColour(wx.Colour(108, 108, 108))

        self.size_lab.SetLabel(self.total_size)
        self.speed_lab.SetLabel("正在合成视频...")
        self.pause_btn.Enable(False)

        self.downloader.download_info.update_base_info_download_complete(True)

        if not retry:
            parent = self.GetParent().GetParent()

            parent.update_task_lab()
            parent.start_download()

        Thread(target = self.utils.merge_video).start()

    def onMergeComplete(self):
        self.set_status("completed")
        
        if self.utils.merge_error:
            self.speed_lab.SetLabel("合成视频失败，点击查看详情")
            self.speed_lab.SetForegroundColour(wx.Colour("red"))
            self.speed_lab.SetCursor(wx.Cursor(wx.CURSOR_HAND))

            self.update_pause_btn("retry")

            return
                
        else:
            self.speed_lab.SetLabel("下载完成")

            self.pause_btn.Enable(True)
        
        self.downloader.download_info.clear()

        self.stop_btn.SetToolTip("清除记录")

        self.update_pause_btn_image("folder")

        self.pause_btn.SetToolTip("打开所在位置")

        self.gauge.SetValue(100)

        self.Layout()

    def onError(self):
        self.set_status("error")

        self.speed_lab.SetLabel("下载失败")
        self.speed_lab.SetForegroundColour("red")
        self.stop_btn.SetToolTip("清除记录")

        self.pause_btn.Enable(False)

        self.Layout()

        self.GetParent().GetParent().update_task_lab()

        self.start_thread.stop()

        self.downloader.download_info.clear()
    
    def onOpenFolder(self):
        subprocess.Popen(f'explorer /select,{Config.Download.path}\\{self.info["title"]}.mp4', shell = True)

    def onViewCover(self, event):
        cover_viewer_dlg = CoverViewerDialog(self.GetParent().GetParent(), self.cover_image, self.cover_image_raw)
        cover_viewer_dlg.ShowModal()

    def onShowError(self, event):
        if not self.pause_btn.Enabled or self.info["status"] == "retry":
            show_error_dlg = ShowErrorDialog(self.GetParent().GetParent(), self.utils.merge_error_log)
            show_error_dlg.ShowModal()

    def update_pause_btn(self, status: str):
        match status:
            case "downloading":
                self.pause_btn.SetToolTip("暂停下载")

                self.speed_lab.SetLabel("")

            case "pause":
                self.pause_btn.SetToolTip("继续下载")

                self.speed_lab.SetLabel("暂停中")

            case "retry":
                self.pause_btn.SetToolTip("重试")

                self.set_status("retry")

                self.pause_btn.Enable(True)

                self.update_pause_btn_image("retry")

        self.update_pause_btn_image(status)

    def update_pause_btn_image(self, status: str):
        match status:
            case "downloading":
                image = wx.Image(io.BytesIO(getPauseIcon24())) if self.is_scaled else wx.Image(io.BytesIO(getPauseIcon16()))
            case "pause":
                image = wx.Image(io.BytesIO(getResumeIcon24())) if self.is_scaled else wx.Image(io.BytesIO(getResumeIcon16()))
            case "retry":
                image = wx.Image(io.BytesIO(getRetryIcon24())) if self.is_scaled else wx.Image(io.BytesIO(getRetryIcon16()))
            case "folder":
                image = wx.Image(io.BytesIO(getFolderIcon24())) if self.is_scaled else wx.Image(io.BytesIO(getFolderIcon16()))

        self.pause_btn.SetBitmap(image.Scale(self.scale_size[0], self.scale_size[1], wx.IMAGE_QUALITY_HIGH).ConvertToBitmap())

    def set_status(self, status: str):
        self.info["status"] = status

        if self.info["id"] in DownloadInfo.download_list:
            # 防止任务 id 不在下载列表中而报错
            DownloadInfo.download_list[self.info["id"]]  = self.info