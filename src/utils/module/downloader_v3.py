import os
import time
import threading
from typing import List, Dict

from utils.config import Config

from utils.common.exception import GlobalException
from utils.common.enums import StatusCode
from utils.common.model.data_type import RangeDownloadInfo
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

    def get_downloader_info_batch(self):
        temp_downloader_info = self.parent.downloader_info_list[:1]

        for entry in temp_downloader_info:
            return entry
        
    def get_total_file_size(self):
        total_size = 0

        for entry in self.parent.downloader_info_list:
            url_list, file_name = entry.get("url_list"), entry.get("file_name")

            (url, file_size) = CDN.get_file_size(url_list)

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

        if self.task_info.current_downloaded_size:
            self.parent.current_downloaded_size = self.task_info.current_downloaded_size
            self.parent.total_downloaded_size = self.task_info.total_downloaded_size

            return list(self.task_info.thread_info.values())
        else:
            return self.calc_file_ranges(self.parent.current_file_size)

    def calc_file_ranges(self, file_size: int):
        piece_size = self.get_piece_size(file_size)
        ranges = []

        for start in range(0, file_size, piece_size):
            end = min(start + piece_size - 1, file_size - 1)

            ranges.append((start, end))

        return ranges
    
    def get_piece_size(self, file_size: int):
        if file_size <= Const.Size_100MB:
            return 10 * Const.Size_1MB
        
        elif file_size <= Const.Size_1GB:
            return 25 * Const.Size_1MB
        
        else:
            return 40 * Const.Size_1MB
    
    def create_local_file(self, file_path: str, file_size: int):
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.seek(file_size - 1)
                f.write(b"\0")

    def get_range_info(self, index: int, file_path: str, url: str, range: list):
        info = RangeDownloadInfo()
        info.index = str(index)
        info.file_path = file_path
        info.url = url
        info.range = range

        return info

    def retry_download(self, e):
        self.parent.retry_times += 1

        if self.parent.retry_times > Config.Advanced.download_error_retry_count:
            self.parent.stop_event.set()

            raise GlobalException(code = StatusCode.MaxRetry.value, callback = self.onDownloadError) from e
        
        elif not Config.Advanced.retry_when_download_error:
            self.parent.stop_event.set()

            raise GlobalException(code = StatusCode.DownloadError.value, callback = self.onDownloadError) from e

    def reset_flag(self):
        self.parent.stop_event.clear()

        self.parent.retry_times = 0
        self.parent.suspend_interval = 0

        self.parent.shutdown = True

    def update_download_progress(self, progress: int = None, speed: str = None):
        if self.parent.stop_event.is_set():
            return
        
        if progress:
            self.task_info.progress = int(progress)

        self.task_info.current_downloaded_size = self.parent.current_downloaded_size
        self.task_info.total_downloaded_size = self.parent.total_downloaded_size
        self.task_info.thread_info = self.parent.thread_info.copy()

        self.task_info.update()

        if speed:
            self.parent.callback.onDownloading(speed)

    def update_thread_info(self, chunk_size: int):
        self.parent.current_downloaded_size += chunk_size
        self.parent.total_downloaded_size += chunk_size

    def on_thread_exit(self):
        with self.parent.lock:
            if not self.parent.shutdown:
                self.task_info.current_downloaded_size = self.parent.total_downloaded_size
                self.task_info.total_downloaded_size = self.parent.total_downloaded_size
                self.task_info.thread_info = self.parent.thread_info

                self.task_info.update()

    def check_speed_limit(self, start_time: float):
        if Config.Download.enable_speed_limit:
            elapsed_time = time.time() - start_time
            expected_time = self.parent.current_downloaded_size / self.get_speed_bps()

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
            if self.parent.current_downloaded_size:
                return time.time() - self.parent.current_downloaded_size / self.get_speed_bps()
            else:
                return time.time()

    def get_speed_bps(self):
        return Config.Download.speed_mbps * 1024 * 1024

    def restart_download(self):
        time.sleep(1)

        self.parent.start_download()

    def check_future_exception(self, future_list: list):
        for future in future_list:
            if e := future.exception():
                raise GlobalException(code = StatusCode.DownloadError.value) from e

    def onDownloadError(self):
        self.parent.stop_download()

        self.parent.callback.onError()

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
        self.thread_info = {}
        self.cdn_host_list = CDN.get_cdn_host_list()

        self.retry_times = 0
        self.suspend_interval = 0

        self.current_file_size = 0
        self.current_downloaded_size = 0
        self.total_downloaded_size = 0

        self.shutdown = False

        self.download_path = FileNameFormatter.get_download_path(self.task_info)

    def set_downloader_info(self, downloader_info: List[dict]):
        self.downloader_info_list = downloader_info

    def start_download(self):
        downloader_info = self.utils.get_downloader_info_batch()

        file_name = downloader_info.get("file_name")
        file_path = os.path.join(self.download_path, file_name)
        self.utils.reset_flag()

        try:
            self.utils.get_total_file_size()

            url = self.utils.cache.get(file_name).get("url")
            file_range_list = self.utils.get_file_range_list(file_name, file_path)

            self.callback.onStart()

            Thread(target = self.listener).start()

            for index, range in enumerate(file_range_list):
                range_info = self.utils.get_range_info(index, file_path, url, range)

                self.range_download(range_info)

        except Exception as e:
            raise GlobalException(code = StatusCode.DownloadError.value, callback = self.utils.onDownloadError) from e

    def range_download(self, info: RangeDownloadInfo):
        try:
            with open(info.file_path, "r+b") as f:
                f.seek(info.range[0])

                start_time = self.utils.update_start_time()

                with RequestUtils.request_get(info.url, headers = RequestUtils.get_headers(referer_url = self.task_info.referer_url, sessdata = Config.User.SESSDATA, range = info.range), stream = True) as req:
                    for chunk in req.iter_content(chunk_size = 1024):
                        if chunk:
                            with self.lock:
                                if self.stop_event.is_set():
                                    break

                                f.write(chunk)

                                self.utils.update_thread_info(len(chunk))

                                self.utils.check_speed_limit(start_time)

        except Exception as e:
            raise e
            #self.utils.retry_download(e)
            
            #self.range_download(info)

        self.utils.on_thread_exit()

    def stop_download(self, shutdown: bool = False):
        self.stop_event.set()
        self.shutdown = shutdown

        self.utils.cache.clear()

    def listener(self):
        while self.current_downloaded_size < self.current_file_size and not self.stop_event.is_set():
            temp_downloaded_size = self.current_downloaded_size

            time.sleep(1)

            with self.lock:
                speed = self.current_downloaded_size - temp_downloaded_size
                total_progress = (self.total_downloaded_size / self.task_info.total_file_size) * 100

                self.utils.update_download_progress(total_progress, FormatUtils.format_speed(speed))

                self.utils.check_speed_suspend(speed)

        if not self.stop_event.is_set():
            self.download_complete()

    def download_complete(self):
        downloader_info = self.utils.get_downloader_info_batch()

        self.task_info.download_items.remove(downloader_info.get("type"))
        self.current_downloaded_size = 0

        del self.downloader_info_list[:1]

        self.utils.update_download_progress()

        if self.downloader_info_list:
            Thread(self.start_download).start()
        else:
            self.callback.onComplete()