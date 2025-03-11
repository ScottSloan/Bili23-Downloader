import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from utils.common.data_type import DownloadTaskInfo, RangeDownloadInfo, DownloaderInfo, DownloaderCallback
from utils.common.thread import Thread
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
        self.executor = ThreadPoolExecutor(max_workers = Config.Download.max_thread_count)

        self.current_file_size = 0
        self.current_downloaded_size = 0
        self.total_downloaded_size = 0
        self.thread_alive_num = 0

        self.downloader_info = []
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
                    url = entry["url_list"][:1][0]
                    file_path = os.path.join(Config.Download.path, entry["file_name"])

                    self.task_info.total_file_size += self.get_file_size(url, file_path, create_file = False)
        
        def get_ranges():
            self.current_file_size = self.get_file_size(url, file_path)

            if self.task_info.current_downloaded_size:
                self.progress_info = self.file_tool.get_info("thread_info")
                self.current_downloaded_size = self.task_info.current_downloaded_size
                self.total_downloaded_size = self.task_info.total_downloaded_size
    
                return list(self.progress_info.values())

            else:
                return self.generate_ranges(self.current_file_size)

        def worker():
            def get_range_info(index: int, file_path: str, url: str, range: list):
                range_info = RangeDownloadInfo()
                range_info.index = index
                range_info.file_path = file_path
                range_info.url = url
                range_info.range = range

                return range_info

            self.callback.onStartDownloadCallback()

            self.progress_info.clear()

            Thread(target = self.progress_tracker).start()

            with ThreadPoolExecutor() as executor:
                for index, range in enumerate(ranges):
                    if range[0] < range[1]:
                        self.progress_info[index] = range

                        range_info = get_range_info(index, file_path, url, range)

                        executor.submit(self.download_range, range_info)

        self.stop_event.clear()

        downloader_info = get_downloader_info()

        url = downloader_info.url_list[:1][0]
        file_path = os.path.join(Config.Download.path, downloader_info.file_name)

        get_total_file_size()

        ranges = get_ranges()

        worker()

    def stop_download(self):
        self.stop_event.set()

    def download_range(self, info: RangeDownloadInfo):
        try:
            with open(info.file_path, "r+b") as f:
                self.thread_alive_num += 1
                f.seek(info.range[0])

                with RequestTool.request_get(info.url, headers = RequestTool.get_headers(referer_url = self.task_info.referer_url, sessdata = Config.User.SESSDATA, range = info.range), stream = True) as req:
                    for chunk in req.iter_content(chunk_size = 1024):
                        if chunk:

                            with self.lock:
                                if self.stop_event.is_set():
                                    break

                                f.write(chunk)

                                _chunk_size = len(chunk)

                                self.current_downloaded_size += _chunk_size
                                self.total_downloaded_size += _chunk_size
                                self.progress_info[info.index][0] += _chunk_size

        except Exception as e:
            print(e)

        self.thread_alive_num -= 1

    def get_file_size(self, url: str, file_path: str, create_file: bool = True):
        def create_local_file():
            if not os.path.exists(file_path) and create_file:
                with open(file_path, "wb") as f:
                    f.seek(file_size - 1)
                    f.write(b"\0")

        req = RequestTool.request_head(url, headers = RequestTool.get_headers(referer_url = self.task_info.referer_url))

        if "Content-Length" in req.headers:
            file_size = int(req.headers.get("Content-Length"))

            create_local_file()
        else:
            print("Not")

        return file_size
    
    def generate_ranges(self, file_size: int):
        num_threads = Config.Download.max_thread_count
        part_size = file_size // num_threads

        ranges = []

        for i in range(num_threads):
            start = i * part_size
            end = start + part_size - 1 if i != num_threads - 1 else file_size - 1
            ranges.append([start, end])
        
        return ranges

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

                self.callback.onDownloadingCallback(FormatTool.format_speed(speed))

        while self.current_downloaded_size < self.current_file_size and not self.stop_event.is_set():
            temp_downloaded_size = self.current_downloaded_size

            time.sleep(1)

            with self.lock:
                speed = self.current_downloaded_size - temp_downloaded_size
                # current_progress = (self.task_info.current_downloaded_size / self.current_file_size) * 100
                total_progress = (self.total_downloaded_size / self.task_info.total_file_size) * 100

                update_progress()

        if not self.stop_event.is_set():
            download_finish()