from utils.common.model.data_type import DownloadTaskInfo
from utils.common.model.callback import Callback
from utils.common.exception import GlobalException
from utils.common.enums import StatusCode

from utils.parse.extra.danmaku import DanmakuParser
from utils.parse.extra.subtitle import SubtitleParser

class ExtraParser:
    @staticmethod
    def download(task_info: DownloadTaskInfo, callback: Callback):
        try:
            if task_info.extra_option.get("download_danmaku_file"):
                parser = DanmakuParser(task_info)

            if task_info.extra_option.get("download_subtitle_file"):
                parser = SubtitleParser(task_info)

            if parser:
                parser.parse()
            else:
                raise GlobalException(code = StatusCode.DownloadError.value, message = "未指定下载类型", callback = callback.onError)

            task_info.total_downloaded_size = task_info.total_file_size
            
            callback.onSuccess()

        except Exception as e:
            raise GlobalException(code = StatusCode.DownloadError.value, callback = callback.onError) from e