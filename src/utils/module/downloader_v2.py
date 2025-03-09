import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from utils.common.data_type import DownloadTaskInfo, RangeDownloadInfo, DownloaderInfo
from utils.tool_v2 import DownloadFileTool, RequestTool
from utils.config import Config

class Downloader:
    def __init__(self, task_info: DownloadTaskInfo, file_tool: DownloadFileTool):
        self.task_info = task_info
        self.file_tool = file_tool

    def init_utils(self):
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers = Config.Download.max_thread_count)

        self.current_downloaded_size = 0
        self.total_downloaded_size = 0
        self.current_file_size = 0
        self.total_file_size = 0

        self.downloader_info = []
        self.progress_info = {}

    def set_downloader_info(self, downloader_info: DownloaderInfo):
        self.downloader_info = downloader_info

    def start_download(self):
        def get_downloader_info():
            downloader_info = self.downloader_info[:1]

            return downloader_info
        
        def get_range_info(index: int, file_name: str, url: str, range: list):
            range_info = RangeDownloadInfo()
            range_info.index = index
            range_info.file_path = os.path.join(Config.Download.path, file_name)
            range_info.url = url
            range_info.range = range

            return range_info
        
        downloader_info = DownloaderInfo()
        downloader_info.load_from_dict(get_downloader_info())

        ranges = self.generate_ranges()

        with ThreadPoolExecutor() as executor:
            for index, range in enumerate(ranges):
                self.progress_info[index] = range
                range_info = get_range_info(index, downloader_info.file_name)

                executor.submit(self.download_range, range_info)

    def download_range(self, info: RangeDownloadInfo):
        with open(info.file_path, "r+b") as f:
            f.seek(range[0])

            with RequestTool.request_get(info.url, headers = RequestTool.get_headers(referer_url = self.task_info.referer_url, sessdata = Config.User.SESSDATA, range = range), stream = True) as req:
                for chunk in req.iter_content(chunk_size = 1024):
                    if chunk:
                        with self.lock:
                            f.write(chunk)

                            self.downloaded_size += len(chunk)
                            self.progress_info[info.index][0] += len(chunk)

    def get_file_size(self, url: str, file_path: str):
        def create_local_file():
            if not os.path.exists(file_path):
                with open(file_path, "wb") as f:
                    f.seek(file_size - 1)
                    f.write(b"\0")

        req = RequestTool.request_head(url)
        file_size = int(req.headers.get("Content-Length"))

        create_local_file()

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
        while self.current_downloaded_size < self.current_file_size:
            temp_downloaded_size = self.current_downloaded_size

            time.sleep(1)

            with self.lock:
                speed = (self.current_downloaded_size - temp_downloaded_size) / 1024 / 1024
                current_progress = (self.current_downloaded_size / self.current_file_size) * 100
                total_progress = (self.total_downloaded_size / self.total_file_size) * 100

            print(f"Progress: {current_progress:.2f}%, Speed: {speed:.2f}MB/s")