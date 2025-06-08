import os

from utils.config import Config
from utils.common.data_type import DownloadTaskInfo

class DownloadPathManager:
    @classmethod
    def get_download_path(cls, task_info: DownloadTaskInfo):
        if Config.Advanced.enable_download_sort:
            folders = []

            if Config.Advanced.sort_by_up:
                up_name = task_info.up_info.get("up_name")

                if up_name:
                    folders.append(up_name)

            if Config.Advanced.sort_by_series:
                folders.append(task_info.series_title)

            path = os.path.join(Config.Download.path, *folders)

            cls.check_path(path)

            return path

        else:
            return Config.Download.path
    
    @staticmethod
    def check_path(path: str):
        if not os.path.exists(path):
            os.makedirs(path)
