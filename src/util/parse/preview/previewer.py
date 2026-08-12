from PySide6.QtCore import QObject, Signal, Slot

from ...common.enum import MediaType, ToastNotificationCategory
from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ...common.config import config

from ...network.request import NetworkRequestWorker
from ...thread.async_ import AsyncTask

from ..parser.base import ParserBase
from ..episode.tree import Attribute

from .audio_info import AudioInfoParser
from .info import PreviewerInfo
from .video_info import VideoInfoParser

from collections import defaultdict
from urllib.parse import urlencode

import logging

logger = logging.getLogger(__name__)

class Previewer(ParserBase, QObject):
    # 媒体信息请求跑在子线程里，而 PreviewerInfo 是全局状态，下载选项对话框会直接读它。
    # 连到闭包的回调会就地在子线程改写这些状态，因此子线程只负责把结果原样转发给这两个信号，
    # 由 Qt 排队回 GUI 线程后再落盘到 PreviewerInfo
    _media_info_ready = Signal(object, str, str, int)
    _media_info_failed = Signal(str, int)

    def __init__(self):
        ParserBase.__init__(self)
        QObject.__init__(self)

        self.show_toast = False

        self.video_info_parser = VideoInfoParser()
        self.audio_info_parser = AudioInfoParser()

        self._media_info_ready.connect(self._on_media_info_ready)
        self._media_info_failed.connect(self._on_media_info_failed)

        signal_bus.parse.preview_init.connect(self.on_init)

    def on_init(self, episode_data: dict, show_toast: bool):
        if episode_data is None:
            return

        self.show_toast = show_toast

        self.clear_cache()

        # clear_cache 已递增代号，此后到达的旧请求结果都会被丢弃
        token = PreviewerInfo.generation

        ep_attr = episode_data.get("attribute", 0)
        PreviewerInfo.attribute = ep_attr

        if not self.check_need_parse(ep_attr):
            # 不需要获取媒体信息，直接调用 on_init_success 以继续后续流程
            self.on_init_success()
            return

        if ep_attr & Attribute.VIDEO_BIT:
            self.get_video_info(episode_data, token)

        elif ep_attr & Attribute.BANGUMI_BIT:
            self.get_bangumi_info(episode_data, token)

        elif ep_attr & Attribute.CHEESE_BIT:
            self.get_cheese_info(episode_data, token)

        elif ep_attr & Attribute.AUDIO_BIT:
            self.get_audio_info(episode_data, token)

    def on_init_success(self):
        try:
            self.post_process()

            if self.show_toast:
                signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", Translator.TIP_MESSAGES("MEDIA_INFO_UPDATED"))

        except Exception as e:
            self.on_init_error(str(e))

    def post_process(self):
        # 判断是否为 DRM
        if PreviewerInfo.info_data.get("is_drm", False):
            raise RuntimeError("不支持下载受 DRM 保护的媒体")

        # 判断媒体类型（dash or mp4），前面不需要解析的视频类型在这里 media_type 仍然是 UNKNOWN
        # 不会影响后续流程
        if PreviewerInfo.info_data:
            if "dash" in PreviewerInfo.info_data.keys():
                PreviewerInfo.media_type = MediaType.DASH

            elif PreviewerInfo.info_data.get("format").startswith("mp4"):
                PreviewerInfo.media_type = MediaType.MP4

            elif PreviewerInfo.info_data.get("format").startswith("flv"):
                PreviewerInfo.media_type = MediaType.FLV

            elif PreviewerInfo.info_data.get("format").startswith("m4a"):
                PreviewerInfo.media_type = MediaType.M4A

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

            # 回调解析完成信号
            signal_bus.parse.preview_finish.emit()

        except Exception as e:
            self.on_init_error(str(e))

    def get_video_info(self, episode_data: dict, token: int):
        params = {
            "bvid": episode_data["bvid"],
            "cid": episode_data["cid"],
            "qn": 80,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1,
        }

        url = f"https://api.bilibili.com/x/player/wbi/playurl?{self.enc_wbi(params)}"

        self._request_media_info(url, "video", token)

    def get_bangumi_info(self, episode_data: dict, token: int):
        params = {
            "bvid": episode_data["bvid"],
            "cid": episode_data["cid"],
            "qn": 80,
            "fnver": 0,
            "fnval": 12240,
            "fourk": 1
        }

        url = f"https://api.bilibili.com/pgc/player/web/playurl?{urlencode(params)}"

        self._request_media_info(url, "bangumi", token)

    def get_cheese_info(self, episode_data: dict, token: int):
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

        self._request_media_info(url, "cheese", token)

    def get_audio_info(self, episode_data: dict, token: int):
        params = {
            "sid": episode_data["sid"],
            "privilege": 2,
            "quality": 2
        }

        url = f"https://www.bilibili.com/audio/music-service-c/web/url?{urlencode(params)}"

        self._request_media_info(url, "audio", token)

    def _request_media_info(self, url: str, parser_type: str, token: int):
        # 两个闭包都跑在请求线程里，只负责把结果连同发起时的代号转发出去，不碰任何共享状态
        def on_success(response: dict):
            self._media_info_ready.emit(response, parser_type, url, token)

        def on_error(error: str):
            self._media_info_failed.emit(error, token)

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

    @Slot(object, str, str, int)
    def _on_media_info_ready(self, response: dict, parser_type: str, url: str, token: int):
        if token != PreviewerInfo.generation:
            # 用户已切换到别的剧集，丢弃过期结果
            return

        try:
            self.check_response(response)

        except RuntimeError:
            # check_response 内部已经走过 on_init_error
            return

        if parser_type == "audio":
            response["data"]["format"] = "m4a"

        # 剧集接口的数据在 result 下，其余都在 data 下
        PreviewerInfo.info_data = response.copy()["result" if parser_type == "bangumi" else "data"]
        PreviewerInfo.info_data["parser_type"] = parser_type
        PreviewerInfo.info_data["query_url"] = url

        self.on_init_success()

    @Slot(str, int)
    def _on_media_info_failed(self, error: str, token: int):
        if token != PreviewerInfo.generation:
            return

        self.on_init_error(error)

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
        code = response.get("code", -1)

        if code != 0:
            if code in Translator.ERROR_CODE_EXPLANATION():
                message = Translator.ERROR_CODE_EXPLANATION(code)
            else:
                message = response.get("message", "未知错误")

            self.on_init_error(message)

            raise RuntimeError(message)

    def clear_cache(self):
        # 递增代号，让上一个剧集尚未返回的请求结果作废
        PreviewerInfo.generation += 1

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
