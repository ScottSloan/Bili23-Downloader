import io
import wx
import json
import time
import wx.adv
import requests
import subprocess
from typing import List
from threading import Thread

from gui.templates import Frame, ScrolledPanel
from gui.show_error import ShowErrorDialog
from gui.cover_viewer import CoverViewerDialog

from utils.icons import *
from utils.config import Config, Download, conf, Audio
from utils.download import Downloader, DownloaderInfo
from utils.tools import *

class DownloadInfo:
    download_list = {}
    no_task = True

class DownloadUtils:
    def __init__(self, info: dict, onError, onComplete):
        self.info, self.onError, self.merge_error, self.audio_type, self.onComplete = info, onError, False, "mp3", onComplete

    def getVideoDurl(self):
        json_dash = self.getVideoDurlJson()

        # 获取视频最高清晰度
        highest_resolution = self.getHigestResolution(json_dash["video"])

        if self.info["resolution"] == 200:
            # 当选择自动时，选取最高可用清晰度
            self.resolution = highest_resolution
        else:
            if highest_resolution < self.info["resolution"]:
                # 当视频不存在选取的清晰度时，选取最高可用的清晰度
                self.resolution = highest_resolution
            else:
                self.resolution = self.info["resolution"]

        temp_video_durl = [i for i in json_dash["video"] if i["id"] == self.resolution]

        self.codec_id = codec_id_map[Config.Download.codec]

        resp = self.hasCodec(temp_video_durl, self.codec_id)

        if resp["result"]:
            self.video_durl = temp_video_durl[resp['index']]["backupUrl"][0]
        else:
            self.video_durl = temp_video_durl[0]["backupUrl"][0]
            self.codec_id = 7

        if Audio.audio_only:
            self.merge_type = Config.Type.MERGE_TYPE_AUDIO # 仅下载音频
        else:
            self.merge_type = Config.Type.MERGE_TYPE_V_A # 合成视频和音频
        
        if json_dash["audio"]:
            # 除杜比全景声和无损以外
            if Audio.audio_quality != 30250:
                temp_audio_durl = [i for i in json_dash["audio"] if i["id"] == Audio.audio_quality]
                self.audio_durl = temp_audio_durl[0]["backupUrl"][0]

                self.audio_type = "mp3"
                self.audio_quality = Audio.audio_quality
            else:
                # 默认为 192K
                self.getAudioDurl_192k(json_dash)

                try:
                    # 无损
                    if json_dash["flac"]:
                        if "audio" in json_dash:
                            if json_dash["flac"]["audio"]:
                                self.audio_durl = json_dash["flac"]["audio"]["backupUrl"][0]

                                self.audio_type = "flac"
                                self.audio_quality = 30251
                    else:
                        if json_dash["dolby"]:
                            if "audio" in json_dash:
                                if json_dash["dolby"]["audio"]:
                                    # 杜比全景声
                                    self.audio_durl = json_dash["dolby"]["audio"][0]["backupUrl"][0]

                                    self.audio_type = "ec3"
                                    self.audio_quality = 30250
                except:
                    # 无法获取无损或杜比链接，换回 192K
                    self.getAudioDurl_192k(json_dash)

        else:
            # 视频不存在音频，标记 flag
            self.merge_type = Config.Type.MERGE_TYPE_VIDEO

        # 更新 info 中的 merge_type
        self.info["merge_type"] = self.merge_type
    
    def getVideoDurlJson(self):
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

    def getAudioDurl_192k(self, json_dash):
        temp_audio_durl = [i for i in json_dash["audio"] if i["id"] == 30280]
        self.audio_durl = temp_audio_durl[0]["backupUrl"][0]

        self.audio_type = "mp3"
        self.audio_quality = 30280

    def getDownloadInfo(self) -> list:
        self.getVideoDurl()

        temp_info = []
        video_info = audio_info = None

        match self.merge_type:
            case Config.Type.MERGE_TYPE_V_A:
                video_info = self.getVideoDownloadInfo()
                audio_info = self.getAudioDownloadInfo()

            case Config.Type.MERGE_TYPE_VIDEO:
                video_info = self.getVideoDownloadInfo()

            case Config.Type.MERGE_TYPE_AUDIO:
                audio_info = self.getAudioDownloadInfo()

        if video_info:
            temp_info.append(video_info)

        if audio_info:
            temp_info.append(audio_info)

        return temp_info

    def getVideoDownloadInfo(self):
        return {
            "id": self.info["id"],
            "type": "video",
            "url": self.video_durl,
            "referer_url": self.info["url"],
            "file_name": "video_{}.mp4".format(self.info["id"]),
            "chunk_list": []
        } 
    
    def getAudioDownloadInfo(self):
        return {
                "id": self.info["id"],
                "type": "audio",
                "url": self.audio_durl,
                "referer_url": self.info["url"],
                "file_name": "audio_{}.{}".format(self.info["id"], self.audio_type),
                "chunk_list": []
            } 

    def mergeVideo(self):
        title = get_legal_name(self.info["title"])

        video_f_name = f"video_{self.info['id']}.mp4"
        audio_f_name = f"audio_{self.info['id']}.{self.audio_type}"

        self.merge_error = False

        match self.merge_type:
            case Config.Type.MERGE_TYPE_V_A:
                # 存在音频文件，调用 FFmpeg 合成
                cmd = f'"{Config.FFmpeg.path}" -y -i "{video_f_name}" -i "{audio_f_name}" -acodec copy -vcodec copy -strict experimental "{title}.mp4"'

            case Config.Type.MERGE_TYPE_VIDEO:
                # 无音频文件，仅有视频，直接重命名
                cmd = f'rename "{video_f_name}" "{title}.mp4"'

            case Config.Type.MERGE_TYPE_AUDIO:
                # 无视频文件，仅有音频，直接重命名
                cmd = f'rename "{audio_f_name}" "{title}.{self.audio_type}"'

        try:
            self.merge_process = self.runSubprocess(cmd)
        except Exception as e:
            # subprocess 运行出错
            self.onMergeError(f"尝试启动 subprocess 时出错：{e}")

            wx.CallAfter(self.onComplete, [video_f_name, audio_f_name])
            
            return
        
        if self.merge_process.returncode == 0:
            if self.merge_type == Config.Type.MERGE_TYPE_V_A:
                if Config.Merge.auto_clean:
                    remove_files(Config.Download.path, [video_f_name, audio_f_name])
                else:
                    cmd = f'rename "{video_f_name}" "{title}_video.mp4" && rename "{audio_f_name}" "{title}_audio.{self.audio_type}"'

                    self.merge_process = self.runSubprocess(cmd)
        else:
            # 合成失败时，获取错误信息
            try:
                output = self.merge_process.stdout.decode("cp936").replace("\r\n", "")
            except:
                output = "无法获取错误信息"

            self.onMergeError(output)

        wx.CallAfter(self.onComplete, [video_f_name, audio_f_name])

    def runSubprocess(self, cmd):
        process = subprocess.run(cmd, cwd = Config.Download.path, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True)
        
        # subprocess 执行完成后，返回 process 指针

        return process
    
    def onMergeError(self, output):
        if hasattr(self, "merge_process"):
            return_code = self.merge_process.returncode
        else:
            return_code = "未知"
            
        self.merge_error_log = {"log": output, "time": get_current_time(), "return_code": return_code}

        self.merge_error = True

    def hasCodec(self, video_durl: List[dict], codec_id: int):
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

    def getHigestResolution(self, data):
        # 默认为 360P
        highest_resolution = 16

        for entry in data:
            # 遍历列表，选取其中最高的清晰度
            if entry["id"] > highest_resolution:
                highest_resolution = entry["id"]

        return highest_resolution

class DownloadWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "下载管理", style = wx.DEFAULT_FRAME_STYLE & (~wx.MINIMIZE_BOX) & (~wx.MAXIMIZE_BOX))

        self.init_UI()

        self.SetSize(self.FromDIP((810, 500)))
        self.SetMinSize(self.FromDIP((810, 500)))

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
        self.download_list_panel.SetBackgroundColour(get_background_color())

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

        self.SetBackgroundColour(get_background_color())
        
    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.clear_btn.Bind(wx.EVT_BUTTON, self.onClear)
        self.open_btn.Bind(wx.EVT_BUTTON, self.onOpenDir)

        self.max_download_choice.Bind(wx.EVT_CHOICE, self.onMaxDownloadChoice)
        self.stop_all_btn.Bind(wx.EVT_BUTTON, self.onStopAll)
        self.pause_all_btn.Bind(wx.EVT_BUTTON, self.onPauseAll)
        self.start_all_btn.Bind(wx.EVT_BUTTON, self.onStartAll)

    def init_utils(self):
        self.update_max_download_choice()

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
        # 打开下载目录
        match Config.Sys.platform:
            case "windows":
                os.startfile(Config.Download.path)
            case "linux":
                subprocess.Popen(f'xdg-open "{Config.Download.path}"', shell = True)
            case "darwin":
                subprocess.Popen(f'open "{Config.Download.path}"', shell = True)

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

            if multiple:
                # 只有在批量下载视频时，才更新 index，否则都为 None
                entry["index"] = index + 1

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
        # 检查下载任务是否在下载列表中，防止重复下载
        for key, value in DownloadInfo.download_list.items():
            if value["title"] == title and value["cid"] == cid:
                return True
            else:
                return False

    def update_max_download_choice(self):
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
        # 获取视频封面
        Thread(target = self.getCover).start()

        self.downloader = Downloader(self.info, self.onStart, self.onDownload, self.onMerge, self.onError)
        self.utils = DownloadUtils(self.info, self.onError, self.onMergeComplete)

        self.loadDownloadInfo()
    
    def loadDownloadInfo(self):
        # 恢复下载 flag
        if self.info["flag"]:
            if self.info["complete"]:
                self.size_lab.SetLabel("{}/{}".format(self.info["complete"], self.info["size"]))

                self.gauge.SetValue(self.info["progress"])
            else:
                if self.info["size"]:
                    self.size_lab.SetLabel("0 MB/{}".format(self.info["size"]))

            if self.info["codec"]:
                self.resolution_lab.SetLabel(self.info["resolution"])
                self.codec_lab.SetLabel(self.info["codec"])

            if self.info["total_size"]:
                self.total_size = self.info["size"]

            self.updatePauseBtn(self.info["status"])

            self.utils.merge_type = self.info["merge_type"]

    def init_scale(self):
        self.scale_size = self.FromDIP((16, 16))
        self.is_scaled = True if self.scale_size != (16, 16) else False

    def init_UI(self):
        self.cover = wx.StaticBitmap(self, -1, size = self.FromDIP((112, 63)))
        self.cover.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        self.title_lab = wx.StaticText(self, -1, self.info["title"], size = self.FromDIP((300, 24)), style = wx.ST_ELLIPSIZE_MIDDLE)
        self.title_lab.SetToolTip(self.info["title"])

        self.resolution_lab = wx.StaticText(self, -1, "--          ")
        self.resolution_lab.SetForegroundColour(wx.Colour(108, 108, 108))

        self.codec_lab = wx.StaticText(self, -1, "--          ")
        self.codec_lab.SetForegroundColour(wx.Colour(108, 108, 108))
        
        self.size_lab = wx.StaticText(self, -1, "--          ")
        self.size_lab.SetForegroundColour(wx.Colour(108, 108, 108))

        resolution_hbox = wx.BoxSizer(wx.HORIZONTAL)
        resolution_hbox.Add(self.resolution_lab, 0, wx.ALL & (~wx.TOP), 10)
        resolution_hbox.AddSpacer(40)
        resolution_hbox.Add(self.codec_lab, 0, wx.ALL & (~wx.TOP), 10)
        resolution_hbox.AddSpacer(40)
        resolution_hbox.Add(self.size_lab, 0, wx.ALL & (~wx.TOP), 10)

        info_vbox = wx.BoxSizer(wx.VERTICAL)
        info_vbox.AddSpacer(5)
        info_vbox.Add(self.title_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, 10)
        info_vbox.AddStretchSpacer()
        info_vbox.Add(resolution_hbox, 0, wx.EXPAND)
        info_vbox.AddSpacer(5)

        match Config.Sys.platform:
            case "windows" | "linux":
                size = (294, 24)
            case "darwin":
                size = (190, 24)

        self.gauge = wx.Gauge(self, -1, 100, size = size)

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
        panel_hbox.Add(info_vbox, 10, wx.EXPAND)
        panel_hbox.AddStretchSpacer(1)
        panel_hbox.Add(gauge_vbox, 0, wx.EXPAND)
        panel_hbox.AddSpacer(10)
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

    def getCover(self):
        req = requests.get(self.info["pic"])

        wx.Image.SetDefaultLoadFlags(0) # 避免出现 iCCP sRGB 警告

        scale_size = self.FromDIP((112, 63))

        temp_cover_image = wx.Image(io.BytesIO(req.content))

        # 判断封面是否为 16:9，若不是，进行裁剪
        if not self.isCover16_9(temp_cover_image):
            temp_cover_image = self.resizeCoverTo16_9(temp_cover_image)

        self.cover_image = temp_cover_image

        self.cover_image_raw = req.content

        image = self.cover_image.Scale(scale_size[0], scale_size[1], wx.IMAGE_QUALITY_HIGH)
        
        self.cover.SetBitmap(image.ConvertToBitmap())

        self.panel_vbox.Layout()

    def start(self):
        self.setStatus("downloading")

        # 开启线程，防止 UI 阻塞
        self.start_thread = Thread(target = self.startDownloadThread)
        self.start_thread.setDaemon(True)
        self.start_thread.start()
    
    def startDownloadThread(self):
        self.speed_lab.SetLabel("准备下载...")

        # 获取下载信息，开始下载
        info_list = self.utils.getDownloadInfo()

        self.downloader.start(info_list)

    def onPause_EVT(self, event):
        match self.info["status"]:
            case "wait":
                self.start()
                self.setStatus("downloading")
            
            case "downloading":
                self.onPause()
                self.setStatus("pause")

            case "pause":
                self.onResume()
                self.setStatus("downloading")
            
            case "completed":
                self.onOpenFolder()
                return
            
            case "retry":
                self.onMerge(retry = True)
                return
        
        self.updatePauseBtn(self.info["status"])

        self.downloader.download_info.update_base_info_status(self.info["status"])

    def onStart(self):
        # 开始下载，更新下载信息
        self.total_size = format_size(self.downloader.total_size / 1024)

        self.speed_lab.SetLabel("")
        self.size_lab.SetLabel("0 MB/{}".format(self.total_size))

        video_quality_dict = dict(map(reversed, resolution_map.items()))
        codec_dict = {7: "AVC/H.264", 12: "HEVC/H.265", 13: "AVC"}
        audio_dict = {value: key for key, value in audio_quality_map.items()}

        match self.utils.merge_type:
            case Config.Type.MERGE_TYPE_V_A | Config.Type.MERGE_TYPE_VIDEO:
                self.resolution_lab.SetLabel(video_quality_dict[self.utils.resolution])
                self.codec_lab.SetLabel(codec_dict[self.utils.codec_id])
            case Config.Type.MERGE_TYPE_AUDIO:
                self.resolution_lab.SetLabel("音频")
                self.codec_lab.SetLabel(audio_dict[self.utils.audio_quality])

        self.updatePauseBtn("downloading")

        self.Layout()

        base_info = {
            "complete": None,
            "size": self.total_size,
            "resolution": video_quality_dict[self.utils.resolution],
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
        self.setStatus("pause")

        self.updatePauseBtn("pause")

    def onResume(self):
        if self.info["download_complete"]:
            self.onMerge()
        else:
            self.downloader.onResume()

    def onResumeCallback(self, event):
        self.onResume()
        self.setStatus("downloading")

        self.updatePauseBtn("downloading")

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
        self.setStatus("merging")

        self.speed_lab.SetForegroundColour(wx.Colour(108, 108, 108))

        self.size_lab.SetLabel(self.total_size)
        self.speed_lab.SetLabel("正在合成视频...")
        self.pause_btn.Enable(False)

        self.downloader.download_info.update_base_info_download_complete(True)

        if not retry:
            parent = self.GetParent().GetParent()

            parent.update_task_lab()
            parent.start_download()

        Thread(target = self.utils.mergeVideo).start()

    def onMergeComplete(self, file_names):
        self.setStatus("completed")
        
        if self.utils.merge_error:
            self.speed_lab.SetLabel("合成视频失败，点击查看详情")
            self.speed_lab.SetForegroundColour(wx.Colour("red"))
            self.speed_lab.SetCursor(wx.Cursor(wx.CURSOR_HAND))

            self.updatePauseBtn("retry")

            return
                
        else:
            self.speed_lab.SetLabel("下载完成")

            self.pause_btn.Enable(True)

            if Config.Merge.auto_clean:
                # 再次删除文件，防止残留
                remove_files(Config.Download.path, file_names)
        
        self.downloader.download_info.clear()

        self.stop_btn.SetToolTip("清除记录")

        self.updatePauseBtnImage("folder")

        self.pause_btn.SetToolTip("打开所在位置")

        self.gauge.SetValue(100)

        self.Layout()

    def onError(self):
        print("onError")

        self.setStatus("error")

        self.speed_lab.SetLabel("下载失败")
        self.speed_lab.SetForegroundColour("red")
        self.stop_btn.SetToolTip("清除记录")

        self.pause_btn.Enable(False)

        self.Layout()

        self.GetParent().GetParent().update_task_lab()

        self.start_thread.stop()

        self.downloader.download_info.clear()
    
    def onOpenFolder(self):
        # 当 index 不为 None 时，添加 index，避免无法打开文件所在位置
        match self.utils.merge_type:
            case Config.Type.MERGE_TYPE_V_A | Config.Type.MERGE_TYPE_VIDEO:
                file_type = "mp4"
            case Config.Type.MERGE_TYPE_AUDIO:
                file_type = f"{self.utils.audio_type}"

        self.file_full_name = f"{self.info['title']}.{file_type}"

        if not os.path.exists(os.path.join(Config.Download.path, self.file_full_name)):
            wx.MessageDialog(self.GetParent().GetParent(), f"文件不存在\n\n无法打开文件：{self.file_full_name}\n文件不存在。", "警告", wx.ICON_WARNING).ShowModal()
            return

        match Config.Sys.platform:
            case "windows":
                cmd = f'explorer.exe /select,{self.file_full_name}'

            case "linux":
                # Linux 下 xdg-open 并不支持选中文件，故仅打开所在文件夹
                cmd = f'xdg-open "{Config.Download.path}"'

            case "darwin":
                cmd = f'open -R "{self.file_full_name}"'
        
        subprocess.Popen(cmd, cwd = Config.Download.path, shell = True)

    def onViewCover(self, event):
        cover_viewer_dlg = CoverViewerDialog(self.GetParent().GetParent(), self.cover_image, self.cover_image_raw)
        cover_viewer_dlg.ShowModal()

    def onShowError(self, event):
        if not self.pause_btn.Enabled or self.info["status"] == "retry":
            show_error_dlg = ShowErrorDialog(self.GetParent().GetParent(), self.utils.merge_error_log)
            show_error_dlg.ShowModal()

    def updatePauseBtn(self, status: str):
        match status:
            case "downloading":
                self.pause_btn.SetToolTip("暂停下载")

                self.speed_lab.SetLabel("准备下载...")

            case "pause":
                self.pause_btn.SetToolTip("继续下载")

                self.speed_lab.SetLabel("暂停中")

            case "retry":
                self.pause_btn.SetToolTip("重试")

                self.setStatus("retry")

                self.pause_btn.Enable(True)

                self.updatePauseBtnImage("retry")

        self.updatePauseBtnImage(status)

    def updatePauseBtnImage(self, status: str):
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

    def setStatus(self, status: str):
        self.info["status"] = status

        if self.info["id"] in DownloadInfo.download_list:
            # 防止任务 id 不在下载列表中而报错
            DownloadInfo.download_list[self.info["id"]]  = self.info

    def resizeCoverTo16_9(self, image: wx.Image):
        # 将非 16:9 封面调整为 16:9
        width, height = image.GetSize()

        new_height = int(width * (9 / 16))

        y_offset = (height - new_height) // 2

        cropped_image = image.GetSubImage(wx.Rect(0, y_offset, width, new_height))

        return cropped_image
    
    def isCover16_9(self, image: wx.Image):
        # 判断封面原始比例是否为 16:9
        width, height = image.GetSize()

        return (width / height) == (16 / 9)
