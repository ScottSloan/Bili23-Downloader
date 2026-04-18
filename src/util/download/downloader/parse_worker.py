from PySide6.QtCore import QRunnable, QMetaObject, Qt, Q_ARG

from util.download.parse.video_info import VideoInfoParser
from util.download.parse.audio_info import AudioInfoParser
from util.common.enum import DownloadType, MediaType
from util.parse.episode.tree import Attribute
from util.parse.parser.base import ParserBase
from util.network import SyncNetWorkRequest
from util.common import config, Translator

from ..task.info import TaskInfo

from urllib.parse import urlencode
import logging
import json

logger = logging.getLogger(__name__)

class ParseWorker(QRunnable, ParserBase):
    def __init__(self, task_info: TaskInfo, parent = None):
        super().__init__()

        self.task_info = task_info
        self.info_data: dict = None

        self.parent = parent
        self.error = False

    def run(self):
        try:
            self.get_info()

            if not self.error:
                download_info = self.parse_download_info()
                download_info_json = json.dumps(download_info, ensure_ascii = False)

                QMetaObject.invokeMethod(
                    self.parent,
                    "on_parse_finished",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, download_info_json)     # 由于不支持直接传递字典，所以传递 json 字符串，在主线程再转换回来
                )

        except:
            logger.exception("解析下载链接失败")

            self.on_parse_error(Translator.ERROR_MESSAGES("PARSE_FAILED"))

    def get_info(self):
        if self.task_info.Episode.attribute & Attribute.VIDEO_BIT:
            self.get_video_info()

        elif self.task_info.Episode.attribute & Attribute.BANGUMI_BIT:
            self.get_bangumi_info()

        elif self.task_info.Episode.attribute & Attribute.CHEESE_BIT:
            self.get_cheese_info()

        if not self.error:
            if "dash" in self.info_data.keys():
                self.task_info.Download.media_type = MediaType.DASH

            elif self.info_data.get("format").startswith("mp4"):
                self.task_info.Download.media_type = MediaType.MP4

            elif self.info_data.get("format").startswith("flv"):
                self.task_info.Download.media_type = MediaType.FLV

    def get_video_info(self):
        params = {
            "bvid": self.task_info.Episode.bvid,
            "cid": self.task_info.Episode.cid,
            "qn": self.task_info.Download.video_quality_id,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1,
        }

        url = f"https://api.bilibili.com/x/player/wbi/playurl?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response.copy()["data"]

    def get_bangumi_info(self):
        params = {
            "bvid": self.task_info.Episode.bvid,
            "cid": self.task_info.Episode.cid,
            "qn": self.task_info.Download.video_quality_id,
            "fnver": 0,
            "fnval": 12240,
            "fourk": 1
        }

        url = f"https://api.bilibili.com/pgc/player/web/playurl?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response.copy()["result"]

    def get_cheese_info(self):
        params = {
            "avid": self.task_info.Episode.aid,
            "cid": self.task_info.Episode.cid,
            "qn": self.task_info.Download.video_quality_id,
            "fnver": 0,
            "fnval": 16,
            "fourk": 1,
            "ep_id": self.task_info.Episode.ep_id,
        }

        url = f"https://api.bilibili.com/pugv/player/web/playurl?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response.copy()["data"]

    def parse_download_info(self):
        total_size = 0
        download_list = {}

        if self.task_info.Download.type & DownloadType.VIDEO != 0:
            video_info_parser = VideoInfoParser(self.info_data, self.task_info)

            for entry in video_info_parser.parse_info():
                total_size += entry.get("file_size", 0)
                file_key = entry.get("file_key", "video")

                download_list[file_key] = entry

        if self.task_info.Download.type & DownloadType.AUDIO != 0:
            audio_info_parser = AudioInfoParser(self.info_data, self.task_info)

            for entry in audio_info_parser.parse_info():
                total_size += entry.get("file_size", 0)
                file_key = entry.get("file_key", "audio")

                download_list[file_key] = entry

        self.get_output_file_ext()

        download_list = self.filter_download_list(download_list)

        return {
            "total_size": total_size,
            "download_queue": list(download_list.keys()),
            "download_list": download_list
        }

    def on_parse_error(self, error_message: str):
        self.error = True

        QMetaObject.invokeMethod(
            self.parent,
            "on_parse_error",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, error_message)
        )

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "无法获取下载链接")

            self.on_parse_error(message)

            raise Exception(message)
        
    def get_output_file_ext(self):
        has_video = self.task_info.Download.type & DownloadType.VIDEO != 0
        has_audio = self.task_info.Download.type & DownloadType.AUDIO != 0

        if not has_video or not has_audio:
            self.task_info.Download.merge_video_audio = False
            self.task_info.Download.keep_original_files = False

        if self.task_info.Download.merge_video_audio or self.task_info.Download.video_parts_count > 0:
            self.task_info.File.merge_file_ext = config.get(config.video_container).value
    
    def filter_download_list(self, download_list: dict):
        # 根据 task_info 中已有的 queue 过滤下载列表，去掉不需要下载的条目
        if not self.task_info.Download.queue:
            # 如果没有 queue 信息，说明是首次解析，直接返回完整的下载列表
            return download_list
        
        # 否则根据 queue 过滤下载列表，去掉不需要下载的条目
        filtered_download_list = {key: entry for key, entry in download_list.items() if key in self.task_info.Download.queue}

        return filtered_download_list
    