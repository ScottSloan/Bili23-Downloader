import re
import os
import time
import threading

from utils.common.data_type import DownloadTaskInfo, RangeDownloadInfo, DownloaderInfo, DownloaderCallback
from utils.common.enums import CDNMode, StatusCode
from utils.common.thread import Thread, DaemonThreadPoolExecutor
from utils.common.map import cdn_map
from utils.common.exception import GlobalException

from utils.module.cdn import CDN

from utils.tool_v2 import DownloadFileTool, RequestTool, FormatTool
from utils.config import Config

class Downloader:
    def __init__(self, task_info: DownloadTaskInfo, file_tool: DownloadFileTool, callback: DownloaderCallback):
        self.task_info = task_info
        self.file_tool = file_tool
        self.callback = callback

        self.init_utils()

    def init_utils(self):
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.executor = DaemonThreadPoolExecutor()

        self.current_file_size = 0
        self.current_downloaded_size = 0
        self.total_downloaded_size = 0

        self.retry_count = 0
        self.has_stopped = False

        self.downloader_info = []
        self.cache = {}
        self.progress_info = {}

    def set_downloader_info(self, downloader_info: DownloaderInfo):
        self.downloader_info = downloader_info

    def start_download(self):
        def get_downloader_info():
            downloader_info = DownloaderInfo()
            downloader_info.load_from_dict(self.downloader_info[:1][0])

            return downloader_info
        
        def get_total_file_size():
            if not self.task_info.total_file_size:
                for entry in self.downloader_info:
                    file_name = entry["file_name"]
                    url_list = entry["url_list"]

                    new_url, file_size = self.get_file_size(url_list)

                    self.task_info.total_file_size += file_size
                    self.cache[file_name] = {
                        "url": new_url,
                        "file_size": file_size
                    }
        
        def get_ranges(file_name: str):
            if file_name in self.cache:
                entry = self.cache[file_name]

                url, self.current_file_size = entry["url"], entry["file_size"]
            else:
                url, self.current_file_size = self.get_file_size(downloader_info.url_list)

            self.create_local_file(file_path, self.current_file_size)

            if self.task_info.current_downloaded_size:
                self.progress_info = self.file_tool.get_info("thread_info")
                self.current_downloaded_size = self.task_info.current_downloaded_size
                self.total_downloaded_size = self.task_info.total_downloaded_size
    
                return url, list(self.progress_info.values())

            else:
                return url, self.generate_ranges(self.current_file_size)

        def worker():
            def get_range_info(index: int, file_path: str, url: str, range: list):
                range_info = RangeDownloadInfo()
                range_info.index = index
                range_info.file_path = file_path
                range_info.url = url
                range_info.range = range

                return range_info

            def update_flag():
                self.progress_info.clear()

                self.retry_count = 0
                self.has_stopped = False

            self.callback.onStartDownloadCallback()

            update_flag()

            Thread(target = self.progress_tracker).start()

            with DaemonThreadPoolExecutor(max_workers = Config.Download.max_thread_count) as self.executor:
                for index, range in enumerate(ranges):
                    if range[0] < range[1]:
                        self.progress_info[index] = range

                        range_info = get_range_info(index, file_path, url, range)

                        self.executor.submit(self.download_range, range_info)

        self.stop_event.clear()

        downloader_info = get_downloader_info()

        file_path = os.path.join(Config.Download.path, downloader_info.file_name)

        get_total_file_size()

        url, ranges = get_ranges(downloader_info.file_name)

        worker()

    def stop_download(self):
        self.stop_event.set()

        self.cache.clear()

    def download_range(self, info: RangeDownloadInfo):
        def update(chunk_size):
            self.current_downloaded_size += chunk_size
            self.total_downloaded_size += chunk_size
            self.progress_info[info.index][0] += chunk_size

        def speed_limit():
            if Config.Download.enable_speed_limit:
                elapsed_time = time.time() - start_time
                expected_time = self.current_downloaded_size / speed_bps

                if elapsed_time < expected_time:
                    time.sleep(expected_time - elapsed_time)

        try:
            with open(info.file_path, "r+b") as f:
                speed_bps = Config.Download.speed_mbps * 1024 * 1024

                f.seek(info.range[0])

                start_time = time.time()

                if self.current_downloaded_size:
                    start_time -= self.current_downloaded_size / speed_bps

                with RequestTool.request_get(info.url, headers = RequestTool.get_headers(referer_url = self.task_info.referer_url, sessdata = Config.User.SESSDATA, range = info.range), stream = True) as req:
                    for chunk in req.iter_content(chunk_size = 1024):
                        if chunk:
                            with self.lock:
                                if self.stop_event.is_set():
                                    break

                                f.write(chunk)

                                update(len(chunk))

                                speed_limit()

        except Exception as e:
            self.retry_count += 1

            if self.retry_count > Config.Advanced.download_error_retry_count:
                raise GlobalException(code = StatusCode.MaxRety.value, callback = self.download_error) from e
            
            elif not Config.Advanced.retry_when_download_error:
                raise GlobalException(code = StatusCode.Download.value, callback = self.download_error) from e
            
            info.range = self.progress_info[info.index]
            self.executor.submit(self.download_range, info)

    def get_file_size(self, url_list: list):
        def request_head(url: str, cdn: str):
            new_url = CDN.replace_cdn(url, cdn)
            
            return new_url, RequestTool.request_head(new_url, headers = RequestTool.get_headers(self.task_info.referer_url))

        for url in url_list:
            for cdn in CDN.get_cdn_list():
                new_url, req = request_head(url, cdn)

                if "Content-Length" in req.headers:
                    file_size = int(req.headers.get("Content-Length"))

                    if file_size:
                        return new_url, file_size
    
    def generate_ranges(self, file_size: int):
        num_threads = Config.Download.max_thread_count
        part_size = file_size // num_threads

        ranges = []

        for i in range(num_threads):
            start = i * part_size
            end = start + part_size - 1 if i != num_threads - 1 else file_size - 1
            ranges.append([start, end])
        
        return ranges

    def create_local_file(self, file_path: str, file_size: int):
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.seek(file_size - 1)
                f.write(b"\0")

    def progress_tracker(self):
        def download_finish():
            item = self.downloader_info[:1][0]["type"]
            self.task_info.download_items.remove(item)

            self.downloader_info = self.downloader_info[1:]

            self.current_downloaded_size = 0

            update_progress()

            if self.downloader_info:
                Thread(target = self.start_download).start()
            else:
                self.callback.onDownloadFinish()

        def update_progress():
            if not self.stop_event.is_set():
                self.task_info.progress = int(total_progress)
                self.task_info.current_downloaded_size = self.current_downloaded_size
                self.task_info.total_downloaded_size = self.total_downloaded_size

                self.file_tool.update_info("task_info", self.task_info.to_dict())
                self.file_tool.update_info("thread_info", self.progress_info)

                self.callback.onDownloadingCallback(speed_str)

        def check_speed():
            def worker():
                self.stop_download()

                time.sleep(1)

                self.start_download()

            if speed_str == "0 KB/s" and Config.Advanced.retry_when_download_suspend:
                self.retry_interval += 1
            else:
                self.retry_interval = 0
            
            if self.retry_interval > Config.Advanced.download_suspend_retry_interval:
                if not self.stop_event.is_set():
                    Thread(target = worker).start()

        self.retry_interval = 0

        while self.current_downloaded_size < self.current_file_size and not self.stop_event.is_set():
            temp_downloaded_size = self.current_downloaded_size

            time.sleep(1)

            with self.lock:
                speed = self.current_downloaded_size - temp_downloaded_size
                # current_progress = (self.task_info.current_downloaded_size / self.current_file_size) * 100
                total_progress = (self.total_downloaded_size / self.task_info.total_file_size) * 100

                speed_str = FormatTool.format_speed(speed)

                update_progress()

                check_speed()

        if not self.stop_event.is_set():
            download_finish()

    def download_error(self):
        if not self.has_stopped:
            self.has_stopped = True

            self.stop_download()

            self.callback.onErrorCallback()