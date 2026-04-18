from util.parse.preview import VideoInfoParser, AudioInfoParser, PreviewerInfo
from util.common.enum import MediaType, ToastNotificationCategory
from util.network import NetworkRequestWorker
from util.parse.episode.tree import Attribute
from util.parse.parser.base import ParserBase
from util.common import signal_bus, config
from util.thread import AsyncTask

from collections import defaultdict
from urllib.parse import urlencode

import logging

logger = logging.getLogger(__name__)

class Previewer(ParserBase):
    def __init__(self):
        super().__init__()

        self.video_info_parser = VideoInfoParser()
        self.audio_info_parser = AudioInfoParser()

        signal_bus.parse.preview_init.connect(self.on_init)

    def on_init(self, episode_data: dict):
        if episode_data is None:
            return
        
        self.clear_cache()

        ep_attr = episode_data.get("attribute", 0)
        PreviewerInfo.attribute = ep_attr

        if not self.check_need_parse(ep_attr):
            # 不需要获取媒体信息，直接调用 on_init_success 以继续后续流程
            self.on_init_success()
            return
        
        if ep_attr & Attribute.VIDEO_BIT:
            self.get_video_info(episode_data)

        elif ep_attr & Attribute.BANGUMI_BIT:
            self.get_bangumi_info(episode_data)

        elif ep_attr & Attribute.CHEESE_BIT:
            self.get_cheese_info(episode_data)

    def on_init_success(self):
        try:
            self.post_process()

        except Exception as e:
            self.on_init_error(str(e))

    def post_process(self):
        # 判断是否为 DRM
        if PreviewerInfo.info_data.get("is_drm", False):
            raise Exception("不支持下载受 DRM 保护的媒体")

        # 判断媒体类型（dash or mp4），前面不需要解析的视频类型在这里 media_type 仍然是 UNKNOWN
        # 不会影响后续流程
        if PreviewerInfo.info_data:
            if "dash" in PreviewerInfo.info_data.keys():
                PreviewerInfo.media_type = MediaType.DASH

            elif PreviewerInfo.info_data.get("format").startswith("mp4"):
                PreviewerInfo.media_type = MediaType.MP4

            elif PreviewerInfo.info_data.get("format").startswith("flv"):
                PreviewerInfo.media_type = MediaType.FLV

        self.parse_info()

    def on_init_error(self, error: str):
        # 标记出错 flag
        PreviewerInfo.error_occurred = True
        PreviewerInfo.error_message = error

        signal_bus.toast.show.emit(ToastNotificationCategory.ERROR, "获取媒体信息失败", error)

        logger.exception("获取媒体信息失败: %s", error)

    def parse_info(self):
        try:
            self.video_info_parser.parse_quality_info()
            self.video_info_parser.parse_codec_info()
            self.audio_info_parser.parse_info()

            # 标记成功获取媒体信息，允许下载和显示下载选项
            PreviewerInfo.error_occurred = False

        except Exception as e:
            self.on_init_error(str(e))

    def get_video_info(self, episode_data: dict):
        def on_success(response: dict):
            self.check_response(response)

            PreviewerInfo.info_data = response.copy()["data"]
            PreviewerInfo.info_data["parser_type"] = "video"
            PreviewerInfo.info_data["query_url"] = url

            self.on_init_success()

        params = {
            "bvid": episode_data["bvid"],
            "cid": episode_data["cid"],
            "qn": 80,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1,
        }

        url = f"https://api.bilibili.com/x/player/wbi/playurl?{self.enc_wbi(params)}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_init_error)

        AsyncTask.run(worker)

    def get_bangumi_info(self, episode_data: dict):
        def on_success(response: dict):
            self.check_response(response)

            PreviewerInfo.info_data = response.copy()["result"]
            PreviewerInfo.info_data["parser_type"] = "bangumi"
            PreviewerInfo.info_data["query_url"] = url

            self.on_init_success()

        params = {
            "bvid": episode_data["bvid"],
            "cid": episode_data["cid"],
            "qn": 80,
            "fnver": 0,
            "fnval": 12240,
            "fourk": 1
        }

        url = f"https://api.bilibili.com/pgc/player/web/playurl?{urlencode(params)}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_init_error)

        AsyncTask.run(worker)

    def get_cheese_info(self, episode_data: dict):
        def on_success(response: dict):
            self.check_response(response)

            PreviewerInfo.info_data = response.copy()["data"]
            PreviewerInfo.info_data["parser_type"] = "cheese"
            PreviewerInfo.info_data["query_url"] = url

            self.on_init_success()

        params = {
            "avid": episode_data["aid"],
            "cid": episode_data["cid"],
            "qn": 0,
            "fnver": 0,
            "fnval": 16,
            "fourk": 1,
            "ep_id": episode_data["ep_id"],
        }

        url = f"https://api.bilibili.com/pugv/player/web/playurl?{urlencode(params)}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_init_error)

        AsyncTask.run(worker)

    def check_need_parse(self, ep_attr: int):
        attr_list = [
            Attribute.SPACE_BIT,
            Attribute.FAVLIST_BIT,
            Attribute.COLLECTION_LIST_BIT,
            Attribute.WATCH_LATER_BIT,
            Attribute.HISTORY_BIT
        ]

        for attr in attr_list:
            if ep_attr & attr:
                return False

        return True

    def check_response(self, response: dict):
        if response.get("code", -1) != 0:
            message = response.get("message", "未知错误")

            self.on_init_error(message)

            raise Exception(message)

    def clear_cache(self):
        PreviewerInfo.info_data = {}
        PreviewerInfo.media_type = MediaType.UNKNOWN
        PreviewerInfo.attribute = 0
        PreviewerInfo.cache = {
            "video": defaultdict(lambda: defaultdict(dict)),
            "audio": defaultdict(dict)
        }

        PreviewerInfo.video_quality_choice_data = []
        PreviewerInfo.audio_quality_choice_data = []
        PreviewerInfo.video_codec_choice_data = []
        
        PreviewerInfo.error_occurred = True
        PreviewerInfo.error_message = ""

        config.target_naming_rule_id = None
