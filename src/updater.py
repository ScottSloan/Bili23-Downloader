import os
import wx
import json
import time
import inspect
import hashlib
import tempfile
import subprocess

from utils.config import Config
from utils.common.request import RequestUtils
from utils.common.thread import Thread
from utils.common.formatter.formatter import FormatUtils
import utils.common.compile_data as json_data

from gui.component.window.frame import Frame

class MiniDownloader:
    def __init__(self, url: str, sha256: str, downloading_callback = None, complete_callback = None):
        self.url = url
        self.sha256 = sha256

        self.downloaded_size = 0
        self.file_size = 0
        self.destination = os.path.join(tempfile.gettempdir(), os.path.basename(self.url))

        self.downloading_callback = downloading_callback
        self.complete_callback = complete_callback

    def download(self):
        with open(self.destination, "r+b") as f:
            f.seek(0)

            with RequestUtils.request_get(self.url, headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth(), stream = True) as req:
                for chunk in req.iter_content(chunk_size = 2048):
                    if chunk:
                        self.downloaded_size += len(chunk)
                        f.write(chunk)

    def start(self):
        Thread(target = self.start_thread).start()
        
    def start_thread(self):
        if self.verify():
            self.complete_callback(self.destination)
            return

        self.get_file_size()

        Thread(target = self.daemon).start()

        self.download()

    def daemon(self):
        while self.downloaded_size < self.file_size:
            time.sleep(0.5)

            self.downloading_callback(self.downloaded_size, self.file_size)

        if self.verify():
            self.complete_callback(self.destination)
        else:
            wx.CallAfter(wx.MessageDialog(self, "文件校验失败\n\n校验下载文件失败，请重试。", "警告", wx.ICON_WARNING).ShowModal)

    def get_file_size(self):
        req = RequestUtils.request_get(self.url, headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth(), allow_redirects = False)

        if req.status_code in [301, 302]:
            self.url = req.headers["Location"]

        req = RequestUtils.request_head(self.url, headers = RequestUtils.get_headers(), proxies = RequestUtils.get_proxies(), auth = RequestUtils.get_auth())

        if "Content-Length" in req.headers:
            self.file_size = int(req.headers["Content-Length"])

        if not os.path.exists(self.destination):
            with open(self.destination, "wb") as f:
                f.seek(self.file_size - 1)
                f.write(b"\0")

    def verify(self):
        if os.path.exists(self.destination):
            return self.get_sha256() == self.sha256
        else:
            return False
        
    def get_sha256(self):
        sha256 = hashlib.sha256()

        with open(self.destination, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

class UpdaterWindow(Frame):
    def __init__(self):
        Frame.__init__(self, None, "Software Updater", style = wx.DEFAULT_FRAME_STYLE & (~wx.MAXIMIZE_BOX) & (~wx.MINIMIZE_BOX) & (~wx.CLOSE_BOX))

        self.SetSize(self.FromDIP((400, 130)))

        self.init_UI()

        self.CenterOnParent()

        self.check_channel()

    def init_UI(self):
        panel = wx.Panel(self)

        self.msg_lab = wx.StaticText(panel, -1, "正在下载更新...")

        self.progress_bar = wx.Gauge(panel, -1, 100, style = wx.GA_HORIZONTAL | wx.GA_SMOOTH)

        self.progress_lab = wx.StaticText(panel, -1, "已下载 0 MB / 0 MB")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.msg_lab, 0, wx.ALL | wx.EXPAND, self.FromDIP(10))
        vbox.Add(self.progress_bar, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, self.FromDIP(10))
        vbox.Add(self.progress_lab, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(10))

        panel.SetSizer(vbox)

    def check_channel(self):
        extra_data: dict = json.loads(inspect.getsource(json_data))

        extra_data["channel"] = "windows_setup"

        self.channel = extra_data.get("channel")

        match self.channel:
            case "source_code":
                pass

            case "windows_portable":
                pass

            case "windows_setup":
                url = "https://drive.scott-sloan.cn/f/zbTd/Bili23_Downloader-1.70.2-windows-x64-setup.exe"
                sha256 = "51998610bf24f5f39b4555b32f00f4e8fbab0f022881e9882b3d6232f83f287f"

                downloader = MiniDownloader(url, sha256, downloading_callback = self.download_callback, complete_callback = self.complete_callback)
                downloader.start()

            case "linux_deb_package":
                pass

            case _:
                wx.MessageDialog(self, "未知错误\n\n发生未知错误，请前往官方网站下载最新版本。", "Fatal Error", wx.ICON_ERROR).ShowModal()
                return
            
    def download_callback(self, downloaded: int, total: int):
        def worker():
            self.progress_bar.SetValue(progress)
            self.progress_lab.SetLabel("已下载 {} / {}".format(FormatUtils.format_size(downloaded), FormatUtils.format_size(total)))

            self.Layout()

        progress = int(downloaded / total * 100)

        wx.CallAfter(worker)

    def complete_callback(self, filepath: str):
        subprocess.Popen(filepath, shell = True, creationflags = subprocess.DETACHED_PROCESS)

        wx.GetApp().ExitMainLoop()
