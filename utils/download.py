import os
import wx
import time
import json
import requests

from .config import Config
from .tools import *
from .thread import Thread, ThreadPool

class Downloader:
    def __init__(self, info, onStart, onDownload, onMerge):
        self.info, self.onStart, self.onDownload, self.onMerge = info, onStart, onDownload, onMerge

        self.init_utils()

    def init_utils(self):
        self.total_size = 0
        self.listen_thread = Thread(target = self.onListen, name = "ListenThread")
        self.listen_thread.setDaemon(True)

        self.session = requests.session()
        
        self.ThreadPool = ThreadPool()

        self.flag = False
        self.thread_info = {}

        self.download_info = DownloaderInfo()

        if not self.info["flag"]:
            self.download_info.init_info(self.info)
        else:
            contents = self.download_info.read_info()
            base_info = contents[str(self.info["id"])]["base_info"]
            thread_info = contents[str(self.info["id"])]["thread_info"]

            self.download_info.id = self.download_id = base_info["id"]

            if base_info["total_size"]:
                self.total_size = base_info["total_size"]
                self.completed_size = self.download_info.calc_completed_size(self.total_size, thread_info)
                self.thread_info = contents[str(self.info["id"])]["thread_info"]

    def add_url(self, info: dict):
        path = os.path.join(Config.Download.path, info["file_name"])

        file_size = self.get_total_size(info["url"], info["referer_url"], path)
        self.total_size += file_size

        for index, chunk_list in enumerate(self.get_chunk_list(file_size, Config.Download.max_thread)):
            url, referer_url, temp = info["url"], info["referer_url"], info.copy()

            thread_id = f"{info['type']}_{info['id']}_{index + 1}"
            temp["chunk_list"] = chunk_list
            self.thread_info[thread_id] = temp

            self.download_id = info["id"]

            self.ThreadPool.submit(self.range_download, args = (thread_id, url, referer_url, path, chunk_list,))

    def start(self, info: list):
        self.completed_size = 0

        for entry in info:
            self.add_url(entry)

        self.update_total_size(self.total_size)

        self.ThreadPool.start()

        self.listen_thread.start()

        wx.CallAfter(self.onStart)

        self.start_wait_thread()

    def restart(self):
        for key, entry in self.thread_info.items():
            path, chunk_list = os.path.join(Config.Download.path, entry["file_name"]), entry["chunk_list"]

            if chunk_list[0] >= chunk_list[1]:
                continue

            self.ThreadPool.submit(target = self.range_download, args = (key, entry["url"], entry["referer_url"], path, chunk_list,))
        
        self.ThreadPool.start()

        if self.info["flag"]:
            self.start_wait_thread()
            
    def start_wait_thread(self):
        wait_thread = Thread(target = self.thread_wait)
        wait_thread.setDaemon(True)

        wait_thread.start()

    def thread_wait(self):
        self.wait()

        self.onFinished()

    def range_download(self, thread_id: str, url: str, referer_url: str, path: str, chunk_list: list):
        req = self.session.get(url, headers = get_header(referer_url, Config.User.sessdata, chunk_list), stream = True, proxies = get_proxy(), auth = get_auth())
        
        with open(path, "rb+") as f:
            f.seek(chunk_list[0])

            for chunk in req.iter_content(chunk_size = 1024):
                if chunk:
                    f.write(chunk)
                    f.flush()

                    self.completed_size += len(chunk)

                    self.thread_info[thread_id]["chunk_list"][0] += len(chunk)

                    if self.completed_size >= self.total_size:
                        self.flag = True

    def onListen(self):
        while not self.flag:
            temp_size = self.completed_size

            time.sleep(1)
            
            info = {
                "progress": int(self.completed_size / self.total_size * 100),
                "speed": self.format_speed((self.completed_size - temp_size) / 1024),
                "size": "{}/{}".format(format_size(self.completed_size / 1024), format_size(self.total_size / 1024)),
                "complete": format_size(self.completed_size / 1024)
            }
            
            self.update_download_info()

            wx.CallAfter(self.onDownload, info)

    def onPause(self):
        self.ThreadPool.stop()
        self.listen_thread.stop()

        self.update_download_info()

    def onResume(self):
        self.restart()

        self.listen_thread = Thread(target = self.onListen, name = "ListenThread")
        self.listen_thread.setDaemon(True)

        self.listen_thread.start()

    def onStop(self):
        self.ThreadPool.stop()
        self.listen_thread.stop()

    def onFinished(self):
        self.ThreadPool.stop()
        self.listen_thread.stop()

        wx.CallAfter(self.onMerge)

    def wait(self):
        while not self.flag:
            time.sleep(1)
    
    def get_total_size(self, url: str, referer_url: str, path: str) -> int:
        req = self.session.head(url, headers = get_header(referer_url))

        total_size = int(req.headers["Content-Length"])
        
        with open(path, "wb") as f:
            f.truncate(total_size)

            return total_size

    def get_chunk_list(self, total_size: int, chunk: int) -> list:
        piece_size = int(total_size / chunk)
        chunk_list = []

        for i in range(chunk):
            start = i * piece_size + 1 if i != 0 else 0 
            end = (i + 1) * piece_size if i != chunk - 1 else total_size

            chunk_list.append([start, end])

        return chunk_list

    def format_speed(self, speed: int) -> str:
        return "{:.1f} MB/s".format(speed / 1024) if speed > 1024 else "{:.1f} KB/s".format(speed) if speed > 0 else "0 KB/s"
    
    def update_download_info(self):
        self.download_info.update_thread_info(self.thread_info, self.completed_size)

    def update_total_size(self, total_size):
        self.download_info.update_base_info_total_size(total_size)

class DownloaderInfo:
    def __init__(self):
        self.path = os.path.join(os.getcwd(), "download.json")
    
    def check_file(self):
        if not os.path.exists(self.path):
            contents = {}

            self.write(contents)

    def read_info(self):
        self.check_file()
        
        with open(self.path, "r", encoding = "utf-8") as f:
            try:
                return json.loads(f.read())
            except:
                return {}
    
    def init_info(self, info):
        self.id = info["id"]
        contents = self.read_info()

        contents[str(info["id"])] = {
                "base_info": info,
                "thread_info": {}
            }
        
        self.write(contents)
        
    def update_thread_info(self, thread_info, completed_size):
        contents = self.read_info()

        contents[f"{self.id}"]["thread_info"] = thread_info
        contents[f"{self.id}"]["base_info"]["completed_size"] = completed_size

        self.write(contents)

    def update_base_info(self, base_info):
        contents = self.read_info()

        contents[f"{self.id}"]["base_info"]["size"] = base_info["size"]
        contents[f"{self.id}"]["base_info"]["codec"] = base_info["codec"]
        contents[f"{self.id}"]["base_info"]["complete"] = base_info["complete"]
        contents[f"{self.id}"]["base_info"]["resolution"] = base_info["resolution"]
        
        self.write(contents)

    def update_base_info_progress(self, progress, complete):
        contents = self.read_info()

        contents[f"{self.id}"]["base_info"]["progress"] = progress
        contents[f"{self.id}"]["base_info"]["complete"] = complete

        self.write(contents)

    def update_base_info_status(self, status):
        contents = self.read_info()

        contents[f"{self.id}"]["base_info"]["status"] = status

        self.write(contents)

    def update_base_info_total_size(self, total_size):
        contents = self.read_info()

        contents[f"{self.id}"]["base_info"]["total_size"] = total_size

        self.write(contents)

    def write(self, contents):
        with open(self.path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False))
    
    def clear(self):
        contents = self.read_info()

        id_string = str(self.id)

        if id_string in contents:
            contents.pop(id_string)

        self.write(contents)
    
    def calc_completed_size(self, total_size, thread_info):
        uncompleted_size = 0

        for key, thread_entry in thread_info.items():
            chunk_list = thread_entry["chunk_list"]

            if chunk_list[0] < chunk_list[1]:
                uncompleted_size += chunk_list[1] - chunk_list[0]
        
        return total_size - uncompleted_size