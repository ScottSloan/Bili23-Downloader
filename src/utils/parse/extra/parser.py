import os
import json

from utils.config import Config
from utils.common.request import RequestUtils
from utils.common.model.data_type import DownloadTaskInfo
from utils.common.enums import StatusCode
from utils.common.exception import GlobalException

class Parser:
    def __init__(self):
        self.total_file_size: int = 0
        self.task_info: DownloadTaskInfo = None
    
    def request_get(self, url: str, check: bool = False):
        req = RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = "https://www.bilibili.com/", sessdata = Config.User.SESSDATA))

        req.raise_for_status()

        if check:
            data = json.loads(req.text)

            self.check_json(data)

            return data

        return req
    
    def save_file(self, file_name: str, contents: str, mode: str):
        file_path = os.path.join(self.task_info.download_path, file_name)

        encoding = "utf-8" if mode == "w" else None

        with open(file_path, mode, encoding = encoding) as file:
            file.write(contents)

        self.total_file_size += os.stat(file_path).st_size

    def get_video_resolution(self):
        return {
            "width": self.task_info.video_width,
            "height": self.task_info.video_height
        }
    
    def check_json(self, data: dict):
        status_code = data.get("code", 0)
        message = data.get("message")

        if status_code != StatusCode.Success.value:
            raise GlobalException(code = status_code, message = message, json_data = data)