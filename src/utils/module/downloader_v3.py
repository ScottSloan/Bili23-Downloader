import threading
from typing import List
from urllib.parse import urlparse, urlunparse

from utils.config import Config

from utils.common.thread import DaemonThreadPoolExecutor
from utils.common.exception import GlobalException
from utils.common.enums import StatusCode
from utils.common.data_type import DownloadTaskInfo, DownloaderCallback
from utils.common.request import RequestUtils

class Utils:
    def __init__(self, parent):
        self.parent: Downloader = parent

    def get_downloader_info_batch(self):
        temp_downloader_info = self.parent.downloader_info[:1]

        for entry in temp_downloader_info:
            return entry
        
    def get_total_file_size(self):
        for entry in self.parent.downloader_info:
            url_list = entry.get("url_list")

            (url, file_size) = self.get_file_size(url_list)

            self.parent.task_info.total_file_size += file_size

    def get_file_size(self, url_list: List[str]):
        for download_url in url_list:
            if self.parent.cdn_host_list:
                for cdn_host in self.parent.cdn_host_list:
                    new_url = self.replace_host(download_url, cdn_host)

                    file_size = self.request_head(new_url)

                    if file_size:
                        return (new_url, file_size)
            else:
                file_size = self.request_head(download_url)

                if file_size:
                    return (download_url, file_size)
            
    def request_head(self, url: str):
        req = RequestUtils.request_head(url, headers = RequestUtils.get_headers(self.parent.task_info.referer_url))

        return req.headers.get("Content-Length", 0)

    def get_cdn_host_list(self):
        if Config.Advanced.enable_switch_cdn:
            return Config.Advanced.cdn_list
        
    def replace_host(url: str, cdn_host: str):
        parsed_url = urlparse(url)._replace(netloc = cdn_host)

        return urlunparse(parsed_url)
        
    def onDownloadError(self):
        pass

class Downloader:
    def __init__(self, task_info: DownloadTaskInfo, callback: DownloaderCallback):
        self.task_info = task_info
        self.callback = callback

        self.init_utils()


    def init_utils(self):
        self.utils = Utils(self)

        self.stop_event = threading.Event()
        self.executor = DaemonThreadPoolExecutor()

        self.downloader_info: List[dict] = []
        self.cdn_host_list = self.utils.get_cdn_host_list()

    def set_downloader_info(self, downloader_info: List[dict]):
        self.downloader_info = downloader_info

    def start_download(self):
        downloader_info = self.utils.get_downloader_info_batch()

        try:
            self.utils.get_total_file_size()

        except Exception as e:
            raise GlobalException(code = StatusCode.DownloadError.value, callback = self.utils.onDownloadError) from e



