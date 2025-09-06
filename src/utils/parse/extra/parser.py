import os

from utils.config import Config
from utils.common.request import RequestUtils
from utils.common.model.data_type import DownloadTaskInfo

from utils.parse.download import DownloadParser
from utils.parse.preview import VideoPreview

class Parser:
    def __init__(self):
        self.total_file_size: int = 0
        self.task_info: DownloadTaskInfo = None
    
    def request_get(self, url: str):
        return RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = "https://www.bilibili.com/", sessdata = Config.User.SESSDATA))
    
    def save_file(self, file_name: str, contents: str, mode: str):
        file_path = os.path.join(self.task_info.download_path, file_name)

        encoding = "utf-8" if mode == "w" else None

        with open(file_path, mode, encoding = encoding) as file:
            file.write(contents)

        self.total_file_size += os.stat(file_path).st_size

    def get_video_resolution(self):
        if self.task_info.video_width:
            return {
                "width": self.task_info.video_width,
                "height": self.task_info.video_height
            }
        else:
            data = DownloadParser.get_download_stream_json(self.task_info)

            width, height = VideoPreview.get_video_resolution(self.task_info, data)

            return {
                "width": width,
                "height": height
            }
