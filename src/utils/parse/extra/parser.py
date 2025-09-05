import os

from utils.config import Config
from utils.common.request import RequestUtils
from utils.common.model.data_type import DownloadTaskInfo

class Parser:
    total_file_size: int = 0
    task_info: DownloadTaskInfo = None
    
    @staticmethod
    def request_get(url: str):
        return RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = "https://www.bilibili.com/", sessdata = Config.User.SESSDATA))
    
    @classmethod
    def save_file(cls, file_name: str, contents: str, mode: str):
        file_path = os.path.join(cls.task_info.download_path, file_name)

        encoding = "utf-8" if mode == "w" else None

        with open(file_path, "wb", encoding = encoding) as file:
            file.write(contents)

        cls.total_file_size += os.stat(file_path).st_size