import os

from utils.config import Config

from utils.common.model.data_type import DownloadTaskInfo
from utils.common.model.callback import Callback
from utils.common.enums import StatusCode
from utils.common.request import RequestUtils
from utils.common.formatter.file_name_v2 import FileNameFormatter
from utils.common.exception import GlobalException

from utils.parse.preview import VideoPreview
from utils.parse.download import DownloadParser

from utils.module.pic.cover import Cover

class ExtraParser:
    class Cover:
        @classmethod
        def download(cls, task_info: DownloadTaskInfo):
            base_file_name = FileNameFormatter.format_file_basename(task_info)

            cover_type = Cover.get_cover_type()
            task_info.output_type = cover_type.lstrip(".")

            contents = Cover.download_cover(task_info.cover_url)

            ExtraParser.Utils.save_to_file(f"{base_file_name}{cover_type}", contents, task_info, "wb")

    class Utils:
        @staticmethod
        def download(task_info: DownloadTaskInfo, callback: Callback):
            def update_task_info():
                task_info.download_path = FileNameFormatter.get_download_path(task_info)
                task_info.file_name = FileNameFormatter.format_file_basename(task_info)

                task_info.update()

            try:
                if task_info.extra_option.get("download_cover_file"):
                    ExtraParser.Cover.download(task_info)

                task_info.total_downloaded_size = task_info.total_file_size

                update_task_info()

                callback.onSuccess()

            except Exception as e:
                raise GlobalException(code = StatusCode.DownloadError.value, callback = callback.onError) from e

        @staticmethod
        def request_get(url: str):
            return RequestUtils.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        @staticmethod
        def save_to_file(file_name: str, contents: str, task_info: DownloadTaskInfo, mode: str):
            download_path = FileNameFormatter.get_download_path(task_info)

            file_path = os.path.join(download_path, file_name)

            encoding = "utf-8" if mode == "w" else None

            with open(file_path, mode, encoding = encoding) as f:
                f.write(contents)

            task_info.total_file_size += os.stat(file_path).st_size

        @staticmethod
        def get_video_resolution(task_info: DownloadTaskInfo):
            if task_info.video_width:
                width, height = task_info.video_width, task_info.video_height
            else:
                data = DownloadParser.get_download_stream_json(task_info)

                width, height = VideoPreview.get_video_resolution(task_info, data)

            return {
                "width": width,
                "height": height
            }
