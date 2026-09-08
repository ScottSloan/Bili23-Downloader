"""
把一个下载任务解析成「有哪几路流、各自从哪儿下」

原先整段长在 `downloader/parse_worker.py` 里，而那是个 QRunnable —— 结果与界面无关的
请求、重试、组装全都绑在 Qt 的线程池与 `QMetaObject.invokeMethod` 上，服务端用不了。
按 D16 抽到这里：**不依赖 Qt，也不依赖任何事件循环**，桌面版的 worker 与 WebUI 的
下载调度器调的是同一份。

两边各写一份的表现会很难查：同一个视频在桌面版下得到，在 WebUI 上说「无法获取下载链接」，
或者两边选出了不同的画质档 —— 而两处代码单看都是对的。

## 重试

批量下载几百个视频时总有少数会撞上 CDN 抖动或接口风控。只重试一次：链接探测本身已经是
并发 + 节点熔断，失败节点在重试时会被降权跳过，一次足以穿过大部分瞬时故障；再多则会
长时间占着下载并发额度。

`stop_event` 是给「重试等待期间用户把任务暂停了」准备的 —— 不给的话那 3 秒里
按什么都没反应。被叫停时返回 None，**不是抛异常**：那不是失败。
"""

from typing import List, Optional
from urllib.parse import urlencode
import logging
import time

from ...common.enum import DownloadType, MediaType
from ...common.translator import Translator
from ...network.request import SyncNetWorkRequest, RequestType
from ...parse.episode.tree import Attribute
from ...parse.parser.base import build_video_info_url
from ...parse.parser.lesson import (
    LESSON_PLAY_DETAIL_URL, build_lesson_media_info, build_lesson_play_payload,
)

from ..task.info import TaskInfo
from ..task.options import resolve
from .audio_info import AudioInfoParser
from .video_info import VideoInfoParser

logger = logging.getLogger(__name__)

PARSE_MAX_ATTEMPTS = 2
PARSE_RETRY_DELAY = 3

# playurl 接口的这些错误码属于风控或服务端临时故障，重试有意义；
# 其余错误码（无此视频、需要大会员等）无论重试多少次结果都一样
RETRYABLE_API_CODES = {-352, -412, -500, -504, -509}

class ParseAbortError(RuntimeError):
    """明确不该重试的错误，与网络抖动区分开"""
    pass

def format_parse_error(detail: str) -> str:
    """两端显示同一句话。桌面版弹气泡、WebUI 记进状态标签，措辞不该有两种"""
    return "{title}\n\n{detail}".format(
        title = Translator.ERROR_MESSAGES("PARSE_FAILED"), detail = detail)

class DownloadInfoResolver:
    """
    单次解析。**不含重试**，重试在 `resolve_download_info` 里

    会就地改 `task_info`：媒体类型、合并后的容器格式，以及 `merge_video_audio` 与
    `keep_original_files` 这两个在只有一路流时必须关掉的开关
    """

    def __init__(self, task_info: TaskInfo):
        self.task_info = task_info
        self.info_data: dict = None

    def run(self) -> dict:
        self.get_info()

        return self.parse_download_info()

    # ---- 取播放地址 ----

    def get_info(self):
        attr = self.task_info.Episode.attribute

        if attr & Attribute.VIDEO_BIT:
            self.get_video_info()

        elif attr & Attribute.BANGUMI_BIT:
            self.get_bangumi_info()

        elif attr & Attribute.CHEESE_BIT:
            self.get_cheese_info()

        elif attr & Attribute.LESSON_BIT:
            self.get_lesson_info()

        elif attr & Attribute.AUDIO_BIT:
            self.get_audio_info()

        if "dash" in self.info_data.keys():
            self.task_info.Download.media_type = MediaType.DASH

        elif (self.info_data.get("format") or "").startswith("mp4"):
            self.task_info.Download.media_type = MediaType.MP4

        elif (self.info_data.get("format") or "").startswith("flv"):
            self.task_info.Download.media_type = MediaType.FLV

        elif (self.info_data.get("format") or "").startswith("m4a"):
            self.task_info.Download.media_type = MediaType.M4A

    def get_video_info(self):
        quality_id = self.task_info.Download.video_quality_id

        # 自动选择时先请求最高支持档，才能拿到账号实际可用的最高画质。
        # 少数稿件的响应只包含这一档，缺失的档位由 VideoInfoParser 在选定后按需补取
        url = build_video_info_url(
            self.task_info.Episode.bvid,
            self.task_info.Episode.cid,
            127 if quality_id == 200 else quality_id
        )

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
            "fnval": 143312,
            "fourk": 1
        }

        url = "https://api.bilibili.com/pgc/player/web/playurl?{query}".format(query = urlencode(params))

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

        url = "https://api.bilibili.com/pugv/player/web/playurl?{query}".format(query = urlencode(params))

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response.copy()["data"]

    def get_lesson_info(self):
        payload = build_lesson_play_payload(
            self.task_info.Episode.course_id,
            self.task_info.Episode.lesson_id,
            self.task_info.Episode.item_id,
            self.task_info.Episode.section_id
        )

        request = SyncNetWorkRequest(LESSON_PLAY_DETAIL_URL, RequestType.POST, json_data = payload)
        response = request.run()

        self.check_response(response)

        self.info_data = build_lesson_media_info(response.copy()["data"])

    def get_audio_info(self):
        params = {
            "sid": self.task_info.Episode.sid,
            "privilege": 2,
            "quality": 2
        }

        url = "https://www.bilibili.com/audio/music-service-c/web/url?{query}".format(query = urlencode(params))

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        response["data"]["format"] = "m4a"

        self.info_data = response.copy()["data"]

    def check_response(self, response: dict):
        # 这里只负责抛出异常，错误上报统一交给调用方：
        # 原先在这里直接报一次、外层捕获异常后又报了一次，界面会弹两条错误提示
        code = response.get("code", -1)

        if code != 0:
            message = "{message}（错误码 {code}）".format(
                message = response.get("message") or "无法获取下载链接", code = code)

            if code in RETRYABLE_API_CODES:
                raise RuntimeError(message)

            raise ParseAbortError(message)

    # ---- 组装下载清单 ----

    def parse_download_info(self) -> dict:
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

    def get_output_file_ext(self):
        has_video = self.task_info.Download.type & DownloadType.VIDEO != 0
        has_audio = self.task_info.Download.type & DownloadType.AUDIO != 0

        if not has_video or not has_audio:
            self.task_info.Download.merge_video_audio = False
            self.task_info.Download.keep_original_files = False

        if self.task_info.Download.merge_video_audio or self.task_info.Download.video_parts_count > 0:
            self.task_info.File.merge_file_ext = resolve(self.task_info, "video_container").value

    def filter_download_list(self, download_list: dict) -> dict:
        # 根据 task_info 中已有的 queue 过滤下载列表，去掉不需要下载的条目
        if not self.task_info.Download.queue:
            # 没有 queue 信息说明是首次解析，直接返回完整的下载列表
            return download_list

        return {key: entry for key, entry in download_list.items()
                if key in self.task_info.Download.queue}

def resolve_download_info(task_info: TaskInfo, stop_event = None) -> Optional[dict]:
    """
    解析一个任务的下载信息，失败自动重试一次

    - 成功：返回 `{"total_size", "download_queue", "download_list"}`
    - 被 `stop_event` 叫停：返回 `None`（那不是失败，调用方不该报错）
    - 失败：抛 `RuntimeError`，消息已经由 `format_parse_error` 拼好
    """
    def stopped() -> bool:
        return stop_event is not None and stop_event.is_set()

    error_message = Translator.ERROR_MESSAGES("UNKNOWN_ERROR")

    for attempt in range(1, PARSE_MAX_ATTEMPTS + 1):
        if stopped():
            return None

        try:
            return DownloadInfoResolver(task_info).run()

        except ParseAbortError as e:
            logger.error("解析下载链接失败，该错误不可重试：%s", e)

            error_message = str(e)

            break

        except Exception as e:
            logger.warning("解析下载链接失败（第 %s/%s 次尝试）",
                           attempt, PARSE_MAX_ATTEMPTS, exc_info = True)

            error_message = str(e)

            if attempt >= PARSE_MAX_ATTEMPTS:
                break

            if not _wait_before_retry(stop_event):
                return None

    raise RuntimeError(format_parse_error(error_message))

def _wait_before_retry(stop_event) -> bool:
    """
    分段休眠，用户暂停或取消时能及时退出，不必等满整个退避时间

    返回 False 表示等待期间任务已被中止
    """
    remaining = PARSE_RETRY_DELAY

    while remaining > 0:
        if stop_event is not None and stop_event.is_set():
            return False

        interval = min(0.2, remaining)

        time.sleep(interval)

        remaining -= interval

    return True

def stream_entries(download_info: dict) -> List[dict]:
    """按下载顺序摊平成 [{file_key, url, file_name, file_size, ...}, ...]"""
    entries = []

    for file_key in download_info.get("download_queue") or []:
        entry = (download_info.get("download_list") or {}).get(file_key)

        if isinstance(entry, dict):
            entries.append(dict(entry, file_key = file_key))

    return entries
