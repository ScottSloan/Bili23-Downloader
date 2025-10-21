from utils.common.model.task_info import DownloadTaskInfo
from utils.common.model.callback import Callback
from utils.common.exception import GlobalException
from utils.common.enums import StatusCode

from utils.parse.extra.danmaku import DanmakuParser
from utils.parse.extra.subtitle import SubtitleParser
from utils.parse.extra.cover import CoverParser
from utils.parse.extra.metadata import MetadataParser

class ExtraParser:
    @staticmethod
    def download(task_info: DownloadTaskInfo, callback: Callback):
        try:
            if task_info.extra_option.get("download_danmaku_file"):
                parser = DanmakuParser(task_info)
                parser.parse()

            if task_info.extra_option.get("download_subtitle_file"):
                parser = SubtitleParser(task_info)
                parser.parse()

            if task_info.extra_option.get("download_cover_file"):
                parser = CoverParser(task_info)
                parser.parse()

            if task_info.extra_option.get("download_metadata_file"):
                parser = MetadataParser(task_info)
                parser.parse()

            task_info.total_file_size = parser.total_file_size
            task_info.total_downloaded_size = task_info.total_file_size
            
            callback.onSuccess()

        except Exception as e:
            raise GlobalException(code = StatusCode.DownloadError.value, callback = callback.onError) from e