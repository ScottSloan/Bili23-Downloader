import os
import wx
import time
import requests
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from utils.config import Config
from utils.tools import get_header

class Downloader:
    def __init__(self, on_start, on_download):
        self.on_start, self.on_download = on_start, on_download

        self.session = requests.session()

    def add_url(self, url: str, referer_url: str, file_name: str, index: list, title: str):
        Download_Thread_Pool =ThreadPoolExecutor(max_workers = 4)

        self.index, self.complete_size, self._flag, task = index, 0, True, []
        self.file_path = os.path.join(Config.download_path, file_name)

        self.total_size = self.get_total_size(url, referer_url)

        for chunk_list in self.calc_chunk(self.total_size, 4):
            task.append(Download_Thread_Pool.submit(self.range_download, url, referer_url, chunk_list))

        Thread(target = self.on_listen).start()
        wx.CallAfter(self.on_start, self.format_size(self.total_size / 1024), self.index, file_name, title)

        wait(task, return_when = ALL_COMPLETED)
        self._flag = False

    def range_download(self, url: str, referer_url: str, chunk_list: list):
        req = self.session.get(url, headers = get_header(referer_url, "", chunk_list), stream = True)

        with open(self.file_path, "rb+") as f:
            f.seek(chunk_list[0])

            for chunk in req.iter_content(chunk_size = 512 * 1024):
                if chunk:
                    f.write(chunk)
                    f.flush()

                    self.complete_size += len(chunk)

    def on_listen(self):
        while self._flag:
            temp_size = self.complete_size

            time.sleep(1)

            speed = self.format_speed((self.complete_size - temp_size) / 1024)
            progress = int(self.complete_size / self.total_size * 100)

            wx.CallAfter(self.on_download, progress, speed)

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

    def format_size(self, size: int) -> str:
        if size > 1048576:
            return "{:.1f}GB".format(size / 1024 / 1024)
        elif size > 1024:
            return "{:.1f}MB".format(size / 1024)
        else:
            return "{:.1f}KB".format(size)

    def format_speed(self, speed: int) -> str:
        return "{:.1f}MB/s".format(speed / 1024) if speed > 1024 else "{:.1f}KB/s".format(speed)
