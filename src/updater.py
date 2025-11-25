import os
import wx
import sys
import json
import time
import inspect
import hashlib
import textwrap
import tempfile
import subprocess
from threading import Event

from utils.common.request import RequestUtils
from utils.common.thread import Thread
from utils.common.formatter.formatter import FormatUtils
import utils.common.compile_data as json_data

from gui.component.window.frame import Frame

stop_event = Event()

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
                        if stop_event.is_set():
                            return
                        
                        self.downloaded_size += len(chunk)
                        f.write(chunk)

    def start(self):
        Thread(target = self.start_thread).start()
        
    def start_thread(self):
        if self.verify():
            self.complete_callback(self.destination)
            return

        if self.get_file_size():
            wx.CallAfter(wx.MessageDialog(self, "下载更新\n\n下载更新失败，请手动前往官网下载。", "警告", wx.ICON_WARNING).ShowModal)
            return

        Thread(target = self.daemon).start()

        self.download()

    def daemon(self):
        while self.downloaded_size < self.file_size:
            if stop_event.is_set():
                return

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
        
        else:
            return True

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
    def __init__(self, url: str, url_data: dict):
        self.url = url
        self.url_data = url_data

        Frame.__init__(self, None, "Software Updater", style = wx.DEFAULT_FRAME_STYLE & (~wx.MAXIMIZE_BOX) & (~wx.MINIMIZE_BOX) & (~wx.CLOSE_BOX))

        self.SetSize(self.FromDIP((400, 130)))

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.check_channel()

    def init_UI(self):
        panel = wx.Panel(self)

        self.msg_lab = wx.StaticText(panel, -1, "正在下载更新...")

        self.progress_bar = wx.Gauge(panel, -1, 100, size = self.FromDIP((400, 16)), style = wx.GA_HORIZONTAL | wx.GA_SMOOTH)

        self.progress_lab = wx.StaticText(panel, -1, "已下载 0 MB / 0 MB")

        self.cancel_btn = wx.Button(panel, wx.ID_CANCEL, "取消", size = self.FromDIP((90, 28)))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.msg_lab, 0, wx.ALL | wx.EXPAND, self.FromDIP(10))
        vbox.Add(self.progress_bar, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, self.FromDIP(10))
        vbox.Add(self.progress_lab, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(10))

        vbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_RIGHT, self.FromDIP(10))

        panel.SetSizerAndFit(vbox)

        self.Fit()

    def Bind_EVT(self):
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.onCancelEVT)

    def check_channel(self):
        extra_data: dict = json.loads(inspect.getsource(json_data))

        self.channel = extra_data.get("channel")

        match self.channel:
            case "source_code":
                wx.MessageDialog(self, "更新\n\n请手动执行 git pull 完成更新。", "提示", wx.ICON_INFORMATION).ShowModal()
                sys.exit()
                return

            case "windows_portable" | "windows_setup" | "linux_deb_package":
                self.init_downloader()

            case _:
                wx.MessageDialog(self, "未知错误\n\n发生未知错误，请前往官方网站下载最新版本。", "Fatal Error", wx.ICON_ERROR).ShowModal()
                wx.LaunchDefaultBrowser(self.url)
                return
                    
    def download_callback(self, downloaded: int, total: int):
        def worker():
            self.progress_bar.SetValue(progress)
            self.progress_lab.SetLabel("已下载 {} / {}".format(FormatUtils.format_size(downloaded), FormatUtils.format_size(total)))

            self.Layout()

        progress = int(downloaded / total * 100)

        wx.CallAfter(worker)

    def complete_callback(self, filepath: str):
        if stop_event.is_set():
            return
        
        match self.channel:
            case "windows_portable":
                # 解压 zip 文件
                self.init_extractor(filepath)

            case "windows_setup":
                # 启动安装程序
                subprocess.Popen(filepath, shell = True, creationflags = subprocess.DETACHED_PROCESS)

            case "linux_deb_package":
                # 告知用户手动 sudo dpkg -i
                wx.CallAfter(wx.MessageDialog(self, "下载完成\n\n安装包已下载至：{}\n请在终端手动执行以下命令安装：\n\nsudo dpkg -i {}".format(filepath, filepath), "提示", wx.ICON_INFORMATION).ShowModal)

        wx.GetApp().ExitMainLoop()

    def init_extractor(self, archive_path: str):
        extract_path = tempfile.gettempdir()

        cwd = os.getenv("PYSTAND_CWD")

        runtime_path = os.path.join(cwd, "runtime", "python.exe")

        code_path = self.save_updater_code(archive_path, extract_path, cwd)

        args = f'''"{runtime_path}" "{code_path}"'''

        subprocess.Popen(args = args, shell = True)

    def save_updater_code(self, archive_path: str, extract_path: str, cwd: str):
        code = textwrap.dedent(f"""\
        import os
        import shutil
        import zipfile
        
        def remove_file(path: str):
            if os.path.exists(path):
                os.remove(path)
               
        def remove_dir(path: str):
            if os.path.exists(path):
                shutil.rmtree(path)
        
        def remove_dst(dst_path: str):
            script_path = os.path.join(dst_path, "script")
            script_zip_path = os.path.join(dst_path, "script.zip")
            site_packages_path = os.path.join(dst_path, "site-packages")
            int_path = os.path.join(dst_path, "_pystand_static.int")
            loader_path = os.path.join(dst_path, "Bili23.exe")
            ffmpeg_path = os.path.join(dst_path, "ffmpeg.exe")
            
            remove_dir(script_path)
            remove_dir(site_packages_path)
            
            remove_file(int_path)
            remove_file(loader_path)
            remove_file(ffmpeg_path)
            remove_file(script_zip_path)
                               
        def copy_src(src_path: str, dst_path: str):
            src_script_path = os.path.join(src_path, "script")
            src_site_packages_path = os.path.join(src_path, "site-packages")
            src_int_path = os.path.join(src_path, "_pystand_static.int")
            src_loader_path = os.path.join(src_path, "Bili23.exe")
            src_ffmpeg_path = os.path.join(src_path, "ffmpeg.exe")
                               
            dst_script_path = os.path.join(dst_path, "script")
            dst_site_packages_path = os.path.join(dst_path, "site-packages")
            dst_int_path = os.path.join(dst_path, "_pystand_static.int")
            dst_loader_path = os.path.join(dst_path, "Bili23.exe")
            dst_ffmpeg_path = os.path.join(dst_path, "ffmpeg.exe")
            
            shutil.copytree(src_script_path, dst_script_path)
            shutil.copytree(src_site_packages_path, dst_site_packages_path)
            shutil.copy(src_int_path, dst_int_path)
            shutil.copy(src_loader_path, dst_loader_path)
            shutil.copy(src_ffmpeg_path, dst_ffmpeg_path)
        
        def update(archive_path: str, extract_path: str, cwd: str):
            src_path = os.path.join(extract_path, "Bili23 Downloader")
            dst_path = cwd
            
            if os.path.exists(src_path):
                remove_dir(src_path)
            
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)
            
            remove_dst(dst_path)
            copy_src(src_path, dst_path)
            
            subprocess.Popen(os.path.join(dst_path, "Bili23.exe"), shell = True, cwd = dst_path)
            
            remove_dir(src_path)
            remove_file(archive_path)
        
        update(r"{archive_path}", r"{extract_path}", r"{cwd}")
        """)

        path = os.path.join(tempfile.gettempdir(), "updater.py")

        with open(path, "w", encoding = "utf-8") as f:
            f.write(code)

        return path

    def init_downloader(self):
        channel_info = self.get_channel_info(self.channel)

        downloader = MiniDownloader(channel_info["url"], channel_info["sha256"], downloading_callback = self.download_callback, complete_callback = self.complete_callback)
        downloader.start()

    def get_channel_info(self, channel: str):
        for entry in self.url_data:
            if entry["channel"] == channel:
                return entry
            
    def onCancelEVT(self, event: wx.CommandEvent):
        stop_event.set()

        self.Close()
