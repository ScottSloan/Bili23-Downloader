import os
import time
import threading
from typing import List, Dict

from utils.config import Config

from utils.common.exception import GlobalException
from utils.common.enums import StatusCode
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.model.callback import DownloaderCallback
from utils.common.request import RequestUtils
from utils.common.thread import Thread
from utils.common.formatter.formatter import FormatUtils
from utils.common.formatter.file_name_v2 import FileNameFormatter
from utils.common.const import Const

from utils.module.web.cdn import CDN

class Utils:
    def __init__(self, parent, task_info: DownloadTaskInfo):
        self.parent: Downloader = parent
        self.task_info = task_info

        self.cache: Dict[str, dict] = {}

    def get_total_file_size(self):
        total_size = 0

        for entry in self.parent.downloader_info_list:
            url_list, file_name = entry.get("url_list"), entry.get("file_name")

            info = CDN.get_file_size(url_list)

            if not info:
                raise GlobalException(code = StatusCode.DownloadError, message = "无法获取下载链接，请在设置中关闭 CDN 替换功能后重试。")
            else:
                (url, file_size) = info

            total_size += file_size

            self.cache[file_name] = {
                "url": url,
                "file_size": file_size
            }

        if not self.task_info.total_file_size:
            self.task_info.total_file_size = total_size
    
    def get_file_range_list(self, file_name: str, file_path: str):
        entry = self.cache.get(file_name)

        self.parent.current_file_size = entry.get("file_size")

        self.create_local_file(file_path, self.parent.current_file_size)

        if not self.task_info.thread_info:
            self.task_info.thread_info = self.calc_file_ranges(self.parent.current_file_size)

    def calc_file_ranges(self, file_size: int):
        piece_size = self.get_piece_size(file_size)
        ranges = []

        for start in range(0, file_size, piece_size):
            end = min(start + piece_size - 1, file_size - 1)

            ranges.append([start, end])

        return ranges
    
    def get_piece_size(self, file_size: int):
        if file_size <= Const.Size_100MB:
            return 20 * Const.Size_1MB
        
        elif file_size <= Const.Size_1GB:
            return 35 * Const.Size_1MB
        
        else:
            return 50 * Const.Size_1MB
    
    def create_local_file(self, file_path: str, file_size: int):
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.seek(file_size - 1)
                f.write(b"\0")

    def retry_download(self, e):
        self.parent.retry_times += 1

        if self.parent.retry_times > Config.Advanced.download_error_retry_count:
            self.parent.stop_event.set()

            raise GlobalException(code = StatusCode.MaxRetry.value, callback = self.onDownloadError) from e
        
        elif not Config.Advanced.retry_when_download_error:
            self.parent.stop_event.set()

            raise GlobalException(code = StatusCode.DownloadError.value, callback = self.onDownloadError) from e
        
        self.parent.start_next_thread()

    def reset_flag(self):
        self.parent.stop_event.clear()

        self.parent.retry_times = 0
        self.parent.suspend_interval = 0

    def update_download_progress(self, progress: int = None, speed: str = None):
        if self.parent.stop_event.is_set():
            return
        
        if progress:
            self.task_info.progress = int(progress)

        if self.task_info.thread_info:
            self.task_info.thread_info[0] = self.parent.current_thread_info

        self.task_info.update()

        if speed:
            self.parent.callback.onDownloading(speed)

    def update_thread_info(self, chunk_size: int):
        self.task_info.current_downloaded_size += chunk_size
        self.task_info.total_downloaded_size += chunk_size
        self.parent.current_thread_info[0] += chunk_size

    def check_speed_limit(self, start_time: float):
        if Config.Download.enable_speed_limit:
            elapsed_time = time.time() - start_time
            expected_time = self.task_info.current_downloaded_size / self.speed_bps

            if elapsed_time < expected_time:
                time.sleep(expected_time - elapsed_time)

    def check_speed_suspend(self, speed: int):
        if Config.Advanced.retry_when_download_suspend:
            if speed == 0:
                self.parent.suspend_interval += 1
            else:
                self.parent.suspend_interval = 0

        if self.parent.suspend_interval > Config.Advanced.download_suspend_retry_interval and not self.parent.stop_event.is_set():
            self.parent.stop_download()

            Thread(target = self.restart_download).start()

    def update_start_time(self):
        if Config.Download.enable_speed_limit:
            if self.task_info.current_downloaded_size:
                return time.time() - self.task_info.current_downloaded_size / self.speed_bps
            else:
                return time.time()

    def restart_download(self):
        time.sleep(1)

        self.parent.start_download()

    def onDownloadError(self):
        self.parent.stop_download()

        self.parent.callback.onError()

    @property
    def speed_bps(self):
        return Config.Download.speed_mbps * 1024 * 1024
    
class Downloader:
    def __init__(self, task_info: DownloadTaskInfo, callback: DownloaderCallback):
        self.task_info = task_info
        self.callback = callback

        self.init_utils()

    def init_utils(self):
        self.utils = Utils(self, self.task_info)

        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        self.downloader_info_list: List[dict] = []
        self.cdn_host_list = CDN.get_cdn_host_list()

        self.retry_times: int = 0
        self.suspend_interval: int = 0
        self.current_file_size: int = 0
        self.current_thread_info: list = []
        self.download_type: str = ""

        self.url: str = ""
        self.file_path: str = ""

        self.download_path = FileNameFormatter.get_download_path(self.task_info)

    def set_downloader_info(self, downloader_info: List[dict]):
        self.downloader_info_list = downloader_info

    def start_download(self):
        downloader_info = self.downloader_info_list[:1][0]

        self.download_type = downloader_info.get("type")

        file_name = downloader_info.get("file_name")
        self.file_path = os.path.join(self.download_path, file_name)
        self.utils.reset_flag()

        try:
            self.utils.get_total_file_size()

            self.url = self.utils.cache.get(file_name).get("url")
            self.utils.get_file_range_list(file_name, self.file_path)

            self.callback.onStart()

            Thread(target = self.listener).start()

            self.start_next_thread()

        except Exception as e:
            raise GlobalException(code = StatusCode.DownloadError.value, callback = self.utils.onDownloadError) from e

    def start_next_thread(self):
        if not self.stop_event.is_set():
            if self.current_thread_info and self.current_thread_info[0] >= self.current_thread_info[1]:
                del self.task_info.thread_info[:1]

            range = self.task_info.thread_info[:1]

            for entry in range:
                self.current_thread_info = entry

                self.range_download(self.url, self.file_path, self.current_thread_info)

    def range_download(self, url: str, file_path: str, range: list):
        try:
            with open(file_path, "r+b") as f:
                f.seek(range[0])

                start_time = self.utils.update_start_time()

                with RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = self.task_info.referer_url, sessdata = Config.User.SESSDATA, range = range), stream = True) as req:
                    for chunk in req.iter_content(chunk_size = 2048):
                        if chunk:
                            with self.lock:
                                if self.stop_event.is_set():
                                    break

                                f.write(chunk)

                                self.utils.update_thread_info(len(chunk))

                                self.utils.check_speed_limit(start_time)

        except Exception as e:
            self.utils.retry_download(e)

        self.start_next_thread()

    def stop_download(self):
        self.stop_event.set()

        self.utils.cache.clear()

    def listener(self):
        while self.task_info.current_downloaded_size < self.current_file_size and not self.stop_event.is_set():
            temp_downloaded_size = self.task_info.current_downloaded_size

            time.sleep(1)

            with self.lock:
                speed = self.task_info.current_downloaded_size - temp_downloaded_size
                total_progress = (self.task_info.total_downloaded_size / self.task_info.total_file_size) * 100

                self.utils.update_download_progress(total_progress, FormatUtils.format_speed(speed))

                self.utils.check_speed_suspend(speed)

        if not self.stop_event.is_set():
            self.download_complete()

    def download_complete(self):
        self.task_info.download_items.remove(self.download_type)
        self.task_info.current_downloaded_size = 0
        self.task_info.thread_info.clear()
        self.current_thread_info.clear()

        del self.downloader_info_list[:1]

        self.utils.update_download_progress()

        if self.downloader_info_list:
            Thread(self.start_download).start()
        else:
            self.callback.onComplete()
