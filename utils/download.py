import os
import wx
import time
import requests
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from .config import Config
from .tools import *

class Downloader:
    def __init__(self, onStart, onDownload, onComplete):
        self.onStart, self.onDownload, self.onComplete = onStart, onDownload, onComplete

        self.session = requests.session()
        
        self.Thread_Pool = ThreadPoolExecutor(Config.max_thread)

        self.status = "waiting"
        self.total_size = 0
        self.started_download = False

    def add_url(self, info: dict):
        path = os.path.join(Config.download_path, info["file_name"])

        file_size = self.get_total_size(info["url"], info["referer_url"], path)
        self.total_size += file_size

        for chunk_list in self.calc_chunk(file_size, Config.max_thread):
            url, referer_url = info["url"], info["referer_url"]

            self.task.append(self.Thread_Pool.submit(self.range_download, url, referer_url, path, chunk_list))

    def start_download(self, info: list):
        self.complete_size, self._flag, self.task = 0, True, []

        self.status = "downloading"

        for value in info:
            self.add_url(value)

        Thread(target = self.onListen, name = "ListenThread").start()

        wx.CallAfter(self.onStart)
        self.started_download = True

        wait(self.task, return_when = ALL_COMPLETED)
        self._flag = False

        wx.CallAfter(self.onComplete)

        self.Thread_Pool.shutdown(False)

    def range_download(self, url: str, referer_url: str, path: str, chunk_list: list):
        req = self.session.get(url, headers = get_header(referer_url, None, chunk_list), stream = True, proxies = get_proxy())
        
        with open(path, "rb+") as f:
            f.seek(chunk_list[0])

            for chunk in req.iter_content(chunk_size = 32 * 1024):
                while self.status == "pause":
                    time.sleep(1)
                    continue

                if self.status == "cancelled":
                    break
                
                if chunk:
                    f.write(chunk)
                    f.flush()

                    self.complete_size += len(chunk)

    def onListen(self):
        while self._flag:
            if self.status == "pause":
                time.sleep(1)
                continue

            temp_size = self.complete_size

            time.sleep(1)
            
            if not self._flag: 
                break

            if self.status == "pause": 
                continue
        
            speed = self.format_speed((self.complete_size - temp_size) / 1024)

            size = "{}/{}".format(format_size(self.complete_size / 1024), format_size(self.total_size / 1024))
            
            progress = int(self.complete_size / self.total_size * 100)
            
            wx.CallAfter(self.onDownload, progress, speed, size)

    def onPause(self):
        self.status = "pause"

    def onContinue(self):
        self.status = "downloading"

    def onCancel(self):
        self._flag = False
        self.status = "cancelled"

        self.Thread_Pool.shutdown(False)

    def get_total_size(self, url: str, referer_url: str, path: str) -> int:
        request = self.session.head(url, headers = get_header(referer_url))

        total_size = int(request.headers["Content-Length"])
        
        with open(path, "wb") as f:
            f.truncate(total_size)

            return total_size

    def calc_chunk(self, total_size: int, chunk: int) -> list:
        piece_size = int(total_size / chunk)
        chunk_list = []

        for i in range(chunk):
            start = i * piece_size + 1 if i != 0 else 0 
            end = (i + 1) * piece_size if i != chunk - 1 else total_size

            chunk_list.append([start, end])

        return chunk_list

    def format_speed(self, speed: int) -> str:
        return "{:.1f} MB/s".format(speed / 1024) if speed > 1024 else "{:.1f} KB/s".format(speed) if speed > 0 else ""
