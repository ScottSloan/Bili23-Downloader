import os
import wx
import time
import requests
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from utils.config import Config
from utils.tools import *

class Downloader:
    def __init__(self, on_start, on_download):
        self.on_start, self.on_download = on_start, on_download

        self.session = requests.session()
        self.Thread_Pool = ThreadPoolExecutor(max_workers = Config.max_thread)

        self.status = "waiting"
        self.started_download = False

    def add_url(self, url: str, referer_url: str, file_name: str):
        if self.status == "cancelled": return

        self.complete_size, self._flag, task = 0, True, []
        self.file_path = os.path.join(Config.download_path, file_name)

        self.total_size = self.get_total_size(url, referer_url)

        self.status = "downloading"

        for chunk_list in self.calc_chunk(self.total_size, Config.max_thread):
            task.append(self.Thread_Pool.submit(self.range_download, url, referer_url, chunk_list))

        Thread(target = self.on_listen, name = "Listen_Thread").start()
        wx.CallAfter(self.on_start, self.total_size / 1024)
        self.started_download = True

        wait(task, return_when = ALL_COMPLETED)
        self._flag = False

    def range_download(self, url: str, referer_url: str, chunk_list: list):
        req = self.session.get(url, headers = get_header(referer_url, "", chunk_list), stream = True, proxies = get_proxy())

        with open(self.file_path, "rb+") as f:
            f.seek(chunk_list[0])

            for chunk in req.iter_content(chunk_size = 32 * 1024):
                while self.status == "pause":
                    time.sleep(1)
                    continue

                if self.status == "cancelled": break
                
                if chunk:
                    f.write(chunk)
                    f.flush()

                    self.complete_size += len(chunk)

    def on_listen(self):
        while self._flag:
            if self.status == "pause":
                time.sleep(1)
                continue

            temp_size = self.complete_size

            time.sleep(1)
            
            if not self._flag: return
            if self.status == "pause": continue

            speed = self.format_speed((self.complete_size - temp_size) / 1024)
            progress = int(self.complete_size / self.total_size * 100)
            size = "{}/{}".format(format_size(self.complete_size / 1024), format_size(self.total_size / 1024))

            wx.CallAfter(self.on_download, progress, speed, size)

        self.temp_size = 0

    def on_pause(self):
        self.status = "pause"

    def on_resume(self):
        self.status = "downloading"

    def on_cancel(self):
        self._flag = False
        self.status = "cancelled"
        self.Thread_Pool.shutdown(wait = False)

    def get_total_size(self, url: str, referer_url: str) -> int:
        req = self.session.head(url, headers = get_header(referer_url))

        total_size = int(req.headers["Content-Length"])
        
        with open(self.file_path, "wb") as f:
            f.truncate(total_size)
            return total_size

    def calc_chunk(self, total_size: int, chunk: int) -> list:
        base_size = int(total_size / chunk)
        chunk_list = []

        for i in range(chunk):
            start = i * base_size + 1 if i != 0 else 0 
            end = (i + 1) * base_size if i != chunk - 1 else total_size

            chunk_list.append([start, end])

        return chunk_list

    def format_speed(self, speed: int) -> str:
        return "{:.1f} MB/s".format(speed / 1024) if speed > 1024 else "{:.1f} KB/s".format(speed) if speed > 0 else ""
