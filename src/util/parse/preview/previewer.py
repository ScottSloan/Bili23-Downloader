from PySide6.QtCore import QObject, Signal, Slot

from ...common.enum import MediaType, ToastNotificationCategory
from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ...common.config import config

from ...network.request import NetworkRequestWorker, RequestType
from ...thread.async_ import AsyncTask

from ..parser.base import ParserBase
from ..parser.lesson import LESSON_PLAY_DETAIL_URL, build_lesson_media_info, build_lesson_play_payload
from ..episode.tree import Attribute

from .audio_info import AudioInfoParser
from .info import PreviewerInfo
from .video_info import VideoInfoParser

from collections import defaultdict
from urllib.parse import urlencode

import logging

logger = logging.getLogger(__name__)

class Previewer(ParserBase, QObject):
    # 媒体信息请求及其补充处理跑在子线程里，而 PreviewerInfo 是全局状态，下载选项对话框会直接读它。
    # 子线程处理完响应后通过这两个信号转发结果，由 Qt 排队回 GUI 线程后再落盘到 PreviewerInfo
    _media_info_ready = Signal(object, str, str, int)
    _media_info_failed = Signal(str, int)

    def __init__(self):
        ParserBase.__init__(self)
        QObject.__init__(self)

        self.show_toast = False
        self.candidates = []

        self.video_info_parser = VideoInfoParser()
        self.audio_info_parser = AudioInfoParser()

        self._media_info_ready.connect(self._on_media_info_ready)
        self._media_info_failed.connect(self._on_media_info_failed)

        signal_bus.parse.preview_init.connect(self.on_init)

    def on_init(self, episode_data_list: list, show_toast: bool):
        # 候选项按顺序尝试，取不到媒体信息就换下一个。
        # 用户手动指定某一项时只会传来这一项，失败即失败，不会擅自换成别的视频
        self.candidates = [episode_data for episode_data in episode_data_list if episode_data]

        if not self.candidates:
            return

        self.show_toast = show_toast

        self.start_next_candidate(from_fallback = False)

    def start_next_candidate(self, from_fallback: bool):
        episode_data = self.candidates.pop(0)

        self.clear_cache()

        # 记录媒体信息取自哪个视频，供下载选项对话框显示
        PreviewerInfo.episode_title = episode_data.get("title", "")
        PreviewerInfo.episode_number = episode_data.get("number", "")
        PreviewerInfo.from_fallback = from_fallback

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

        elif ep_attr & Attribute.LESSON_BIT:
            self.get_lesson_info(episode_data, token)

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

    def on_init_error(self, error: str, allow_fallback: bool = True):
        # 标记出错 flag
        PreviewerInfo.error_occurred = True
        PreviewerInfo.error_message = error

        logger.exception("获取媒体信息失败: %s", error)

        if allow_fallback and self.candidates:
            # 充电专属、付费等内容取不到媒体信息，整个解析结果就都会被判定为不可下载，
            # 用户只能自己右键换一项重新获取。此处自动换下一个候选，
            # 全部失败时才提示，避免中途弹出会被重试消解掉的错误
            logger.info("尝试使用下一个视频重新获取媒体信息")

            self.start_next_candidate(from_fallback = True)
            return

        signal_bus.toast.show.emit(ToastNotificationCategory.ERROR, "获取媒体信息失败", error)

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
        # 先请求最高支持档，才能拿到账号实际可用的最高画质。
        bvid = episode_data["bvid"]
        cid = episode_data["cid"]
        url = self._build_video_info_url(bvid, cid, 127)

        self._request_media_info(
            url,
            "video",
            token,
            response_processor = lambda response: self._supplement_video_info(response, bvid, cid),
            # 渐进式流的文件大小查询仍从 qn=80 地址派生，保持原有行为。
            query_url = self._build_video_info_url(bvid, cid, 80)
        )

    def get_bangumi_info(self, episode_data: dict, token: int):
        params = {
            "bvid": episode_data["bvid"],
            "cid": episode_data["cid"],
            "qn": 80,
            "fnver": 0,
            "fnval": 143312,
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

    def get_lesson_info(self, episode_data: dict, token: int):
        payload = build_lesson_play_payload(
            episode_data.get("course_id", 0),
            episode_data.get("lesson_id", 0),
            episode_data.get("item_id", 0),
            episode_data.get("section_id", 0)
        )

        self._request_media_info(LESSON_PLAY_DETAIL_URL, "lesson", token, request_type = RequestType.POST, json_data = payload)

    def get_audio_info(self, episode_data: dict, token: int):
        params = {
            "sid": episode_data["sid"],
            "privilege": 2,
            "quality": 2
        }

        url = f"https://www.bilibili.com/audio/music-service-c/web/url?{urlencode(params)}"

        self._request_media_info(url, "audio", token)

    def _request_media_info(self, url: str, parser_type: str, token: int, request_type: RequestType = RequestType.GET, json_data: dict = None, response_processor = None, query_url = None):
        # 两个闭包都跑在请求线程里；响应处理器只加工局部响应，不碰 PreviewerInfo
        def on_success(response: dict):
            if response_processor:
                response = response_processor(response)

            self._media_info_ready.emit(response, parser_type, query_url or url, token)

        def on_error(error: str):
            self._media_info_failed.emit(error, token)

        worker = NetworkRequestWorker(url, request_type, json_data = json_data)
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

        try:
            if parser_type == "lesson":
                # 商城课程拿到的是一条 mp4 直链，先包装成 playurl 的 mp4 格式
                info_data = build_lesson_media_info(response.copy()["data"])
            else:
                # 剧集接口的数据在 result 下，其余都在 data 下
                info_data = response.copy()["result" if parser_type == "bangumi" else "data"]

        except Exception as e:
            self.on_init_error(str(e))
            return

        PreviewerInfo.info_data = info_data
        PreviewerInfo.info_data["parser_type"] = parser_type
        PreviewerInfo.info_data["query_url"] = url

        self.on_init_success()

    @Slot(str, int)
    def _on_media_info_failed(self, error: str, token: int):
        if token != PreviewerInfo.generation:
            return

        # 网络层就失败了，换一个视频同样请求不到，直接把错误报给用户
        self.on_init_error(error, allow_fallback = False)

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
        PreviewerInfo.episode_title = ""
        PreviewerInfo.from_fallback = False
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
