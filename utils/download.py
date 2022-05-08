import wx
import time
from aria2p import Client, Stats
from threading import Thread

from utils.config import Config
from utils.tools import *

class Downloader(Client):
    pause_ = False

    def __init__(self):
        self.loop = False

        super().__init__()
    
    def download(self, url: str, referer: str, file_name: str):
        options = {"out": file_name, "referer": referer, "dir": Config.download_path, "x": Config.max_thread}

        self.add_uri([url], options = options)
    
    def start_listening(self, on_download, on_complete, on_error):
        self.on_download, self.on_completd, self.loop = on_download, on_complete, True

        kwargs = {
            "on_download_complete": self.__on_completd,
            "on_download_error": on_error,
            "handle_signals": False
        }

        Thread(target = self.listen_to_notifications, kwargs = kwargs, name = "Notifications_Listener").start()
        Thread(target = self.on_listen, name = "Status_Listener").start()

    def on_listen(self):
        while self.loop:
            keys = ['gid', 'totalLength', 'completedLength', 'downloadSpeed']
            info = self.tell_active(keys = keys)

            totalLength = completedLength = downloadSpeed = 0

            for task in info:
                totalLength += int(task['totalLength'])
                completedLength += int(task['completedLength'])
                downloadSpeed += int(task['downloadSpeed'])

            if not totalLength or self.pause_: continue

            progress = int((completedLength / totalLength) * 100)
            speed = self.format_speed(downloadSpeed / 1024)
            
            wx.CallAfter(self.on_download, progress, speed)
            time.sleep(1)
    
    def on_pause(self):
        self.pause_ = True
        self.pause_all()

    def on_unpause(self):
        self.pause_ = False
        self.unpause_all()
    
    def __on_completd(self, gid):
        stat = Stats(self.get_global_stat())

        if stat.num_active + stat.num_waiting == 0:
            self.loop = False
            self.stop_listening()

            Thread(target = self.on_completd, name = "merge_thread").start()

    def format_speed(self, speed: int) -> str:
        return "{:.1f} MB/s".format(speed / 1024) if speed > 1024 else "{:.1f} KB/s".format(speed) if speed > 0 else ""