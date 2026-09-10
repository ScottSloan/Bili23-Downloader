"""
媒体信息预览的纯逻辑 —— 不依赖 Qt

桌面版的 `Previewer` 是围绕 Qt 信号搭的：请求跑在子线程，结果发回 GUI 线程再落到全局的
`PreviewerInfo` 上，中间还有一个 `generation` 代号用来丢弃过期响应。服务端不需要那一套 ——
它是一次请求一个答案，同步等着就行。

这里给出的是同样的三步：**按剧集类型拼 URL → 取媒体信息 → 算出可选的画质 / 编码 / 音质**。
第一步与第三步都与桌面共用（URL 构造在本模块，可选项计算在 `quality_base.py`），
所以两端得出的档位列表必然一致。

## 为什么串行

档位计算读写的是全局的 `PreviewerInfo`（桌面版整个预览流程都建在它上面，搬走牵动面太大）。
两个预览同时跑会互相覆盖，于是这里加一把锁。单用户场景下这不是限制 ——
用户一次也只看一个视频的信息。

## 候选项与回退

首选项常常是充电专属、付费等取不到媒体信息的视频。桌面版会自动换下一个候选，
并在界面上标注「信息来自另一个视频」。这里保留同样的行为，并把 `from_fallback`
如实返回，让前端也能提示 —— 不提示的话，用户看到的清晰度其实属于别的视频。
"""

from collections import defaultdict
from threading import Lock
from typing import List, Optional
from urllib.parse import urlencode
import logging

from ...auth.session import ensure_wbi_keys
from ...common.enum import MediaType
from ...network.request import RequestType, SyncNetWorkRequest

from ..episode.tree import Attribute
from ..parser.base import build_video_info_url
from ..parser.lesson import LESSON_PLAY_DETAIL_URL, build_lesson_media_info, build_lesson_play_payload

from .info import PreviewerInfo
from .stream_info import audio_stream_info, video_stream_info
from .quality_base import AudioQualityBase, VideoQualityBase

logger = logging.getLogger(__name__)

# PreviewerInfo 是全局的，预览必须一个一个来（理由见模块说明）
_preview_lock = Lock()

def build_request(episode: dict) -> Optional[dict]:
    """
    按剧集类型拼出取媒体信息的请求

    返回 None 表示这一类不需要取（比如需要二次解析的节点）。
    **与桌面版 `Previewer` 用的是同一批参数** —— 参数不同会导致两端拿到的档位不同，
    而那种差异只有对着看才发现得了
    """
    attribute = episode.get("attribute", 0)

    if attribute & Attribute.VIDEO_BIT:
        # **必须走 build_video_info_url**：投稿视频的 playurl 要带 wbi 签名，
        # 自己拼参数拿到的是一句「请求错误」。qn 给 127（最高支持档），
        # 才能拿到账号实际可用的最高画质
        return {"url": build_video_info_url(episode["bvid"], episode["cid"], 127),
                "parser_type": "video"}

    if attribute & Attribute.BANGUMI_BIT:
        params = {
            "bvid": episode["bvid"],
            "cid": episode["cid"],
            "qn": 80,
            "fnver": 0,
            "fnval": 143312,
            "fourk": 1,
        }

        return {"url": f"https://api.bilibili.com/pgc/player/web/playurl?{urlencode(params)}",
                "parser_type": "bangumi"}

    if attribute & Attribute.CHEESE_BIT:
        params = {
            "avid": episode["aid"],
            "cid": episode["cid"],
            "qn": 0,
            "fnver": 0,
            "fnval": 16,
            "fourk": 1,
            "ep_id": episode["ep_id"],
        }

        return {"url": f"https://api.bilibili.com/pugv/player/web/playurl?{urlencode(params)}",
                "parser_type": "cheese"}

    if attribute & Attribute.LESSON_BIT:
        payload = build_lesson_play_payload(
            episode.get("course_id", 0),
            episode.get("lesson_id", 0),
            episode.get("item_id", 0),
            episode.get("section_id", 0),
        )

        return {"url": LESSON_PLAY_DETAIL_URL, "parser_type": "lesson",
                "request_type": RequestType.POST, "json_data": payload}

    if attribute & Attribute.AUDIO_BIT:
        params = {"sid": episode["sid"], "privilege": 2, "quality": 2}

        return {"url": f"https://www.bilibili.com/audio/music-service-c/web/url?{urlencode(params)}",
                "parser_type": "audio"}

    return None

def extract_info_data(response: dict, parser_type: str, url: str) -> dict:
    """
    从响应里取出 playurl 数据

    三种结构：剧集在 `result` 下，商城课程要先包装成 playurl 的 mp4 形状，其余在 `data` 下。
    音频还要补一个 `format` —— 它的接口不带，缺了后面判不出媒体类型
    """
    if parser_type == "audio":
        response["data"]["format"] = "m4a"

    if parser_type == "lesson":
        info_data = build_lesson_media_info(response.copy()["data"])

    else:
        info_data = response.copy()["result" if parser_type == "bangumi" else "data"]

    info_data["parser_type"] = parser_type
    info_data["query_url"] = url

    return info_data

def detect_media_type(info_data: dict) -> MediaType:
    """按 playurl 的结构判断媒体类型。与桌面版 `Previewer.post_process` 同一套判断"""
    if not info_data:
        return MediaType.UNKNOWN

    if "dash" in info_data:
        return MediaType.DASH

    fmt = info_data.get("format") or ""

    if fmt.startswith("mp4"):
        return MediaType.MP4

    if fmt.startswith("flv"):
        return MediaType.FLV

    if fmt.startswith("m4a"):
        return MediaType.M4A

    return MediaType.UNKNOWN

class _VideoQuality(VideoQualityBase):
    def __init__(self):
        self.video_info_map = defaultdict(lambda: defaultdict(dict))
        self.declared_quality_map = None
        self.available_quality_list = []

class _AudioQuality(AudioQualityBase):
    def __init__(self):
        self.audio_quality_info_map = defaultdict(dict)

class PreviewSession:
    """
    取一次媒体信息并算出可选档位

    **两个基类用组合而不是多继承。** 它们都有一个叫 `_get_dash_available_quality_list`
    的方法，同时继承的话按 MRO 只会留下靠前那个 —— 于是音质计算会拿到视频的档位列表，
    算出 `{None: 64}` 这种东西。这个 bug 我写出来过一次，被测试抓住了。
    """

    def __init__(self):
        self.video = _VideoQuality()
        self.audio = _AudioQuality()

    def preview(self, candidates: List[dict]) -> dict:
        """
        按顺序尝试候选项，返回第一个取得到信息的

        候选项的意义见模块说明：首选常常是没权限的视频
        """
        candidates = [episode for episode in candidates if episode]

        if not candidates:
            raise ValueError("没有可预览的剧集")

        # 投稿视频的 playurl 要 wbi 签名，密钥缺失时报错完全看不出病因
        ensure_wbi_keys()

        with _preview_lock:
            errors = []

            for index, episode in enumerate(candidates):
                try:
                    return self._preview_one(episode, from_fallback = index > 0,
                                             candidate_index = index)

                except Exception as e:
                    logger.info("预览候选 %s 失败：%s", episode.get("title", ""), e)

                    errors.append(str(e))

            raise RuntimeError(errors[0] if errors else "获取媒体信息失败")

    def preview_stream(self, episode: dict, video_quality_id: int,
                       video_codec_id: int, audio_quality_id: int) -> dict:
        """
        取一次媒体信息，顺便算出选定档位下这两路流的详情

        **要和 preview() 一样在锁里重走一遍 `_preview_one`**：档位映射表在 self 上，
        而 `info_data` / `media_type` / `bvid` / `cid` 在全局的 `PreviewerInfo` 上 ——
        两者必须描述同一个视频。不重走的话，用户切一次画质，拿到的就可能是
        上一个视频的流信息，而且完全看不出来。

        代价是每次切换档位多打一次 playurl。桌面版那边也是每次切换都重新查，
        只是它有一层缓存；这里换来的是「没有需要小心维护的跨请求状态」
        """
        ensure_wbi_keys()

        with _preview_lock:
            result = self._preview_one(episode, from_fallback = False)

            if result.get("need_parse") is False:
                # 这一类没有媒体信息可查（需要二次解析的节点）
                return {**result, "video": None, "audio": None}

            result["video"] = self._safe_stream(
                video_stream_info, self, video_quality_id, video_codec_id)

            result["audio"] = self._safe_stream(
                audio_stream_info, self, audio_quality_id)

            return result

    def _safe_stream(self, func, *args):
        """
        一路流查不到不该让整个请求失败

        画质与音质是分开查的：音频流取不到（无声视频、音轨已并进视频流）是常态，
        视频流那边偶尔也会碰上补取失败。任一路失败时把这一路给成 None，
        另一路照常返回 —— 前端据此显示「按优先级自动选择」之类的说明
        """
        try:
            return func(*args)

        except Exception as e:
            logger.info("获取流详情失败：%s", e)

            return None

    def _preview_one(self, episode: dict, from_fallback: bool,
                     candidate_index: int = 0) -> dict:
        request = build_request(episode)

        PreviewerInfo.attribute = episode.get("attribute", 0)
        PreviewerInfo.episode_title = episode.get("title", "")
        PreviewerInfo.episode_number = episode.get("number", "")
        PreviewerInfo.from_fallback = from_fallback

        if request is None:
            # 这一类不需要取媒体信息（需要二次解析的节点等）。
            # **档位也要一并清掉**：PreviewerInfo 是全局的，不清的话返回的是上一次
            # 预览那个视频的画质列表，而它与当前这一集毫无关系
            PreviewerInfo.info_data = {}
            PreviewerInfo.media_type = MediaType.UNKNOWN
            PreviewerInfo.video_quality_choice_data = {}
            PreviewerInfo.video_codec_choice_data = {}
            PreviewerInfo.audio_quality_choice_data = {}
            PreviewerInfo.bvid = ""
            PreviewerInfo.cid = 0

            return self._result(episode, from_fallback, need_parse = False,
                                candidate_index = candidate_index)

        response = SyncNetWorkRequest(
            request["url"],
            request_type = request.get("request_type", RequestType.GET),
            json_data = request.get("json_data"),
        ).run()

        if response.get("code", -1) != 0:
            raise RuntimeError(response.get("message") or "获取媒体信息失败")

        info_data = extract_info_data(response, request["parser_type"], request["url"])

        if info_data.get("is_drm", False):
            # 与桌面版一致：DRM 内容直接判定为不可下载
            raise RuntimeError("不支持下载受 DRM 保护的媒体")

        PreviewerInfo.info_data = info_data
        PreviewerInfo.media_type = detect_media_type(info_data)
        PreviewerInfo.bvid = episode.get("bvid", "")
        PreviewerInfo.cid = episode.get("cid", 0)

        # 这三步会把可选项写进 PreviewerInfo，与桌面版同一份实现
        self.video.parse_quality_info()
        self.video.parse_codec_info()
        self.audio.parse_info()

        PreviewerInfo.error_occurred = False
        PreviewerInfo.error_message = ""

        return self._result(episode, from_fallback, need_parse = True,
                            candidate_index = candidate_index)

    def _result(self, episode: dict, from_fallback: bool, need_parse: bool,
                candidate_index: int = 0) -> dict:
        media_type = PreviewerInfo.media_type

        return {
            "episode_title": episode.get("title", ""),
            "episode_number": episode.get("number", ""),
            # 首选项没权限时会自动换一个，前端要提示「信息来自另一个视频」
            "from_fallback": from_fallback,
            # 取自候选列表里的第几个。前端接着查流详情时要用同一个 episode
            "candidate_index": candidate_index,
            "media_type": media_type.name.lower() if media_type else "unknown",
            "need_parse": need_parse,
            "video_quality": dict(PreviewerInfo.video_quality_choice_data),
            "video_codec": dict(PreviewerInfo.video_codec_choice_data),
            "audio_quality": dict(PreviewerInfo.audio_quality_choice_data),
            "bvid": PreviewerInfo.bvid,
            "cid": PreviewerInfo.cid,
        }
