from PySide6.QtCore import QRunnable, QMetaObject, Qt, Q_ARG

from ...network.request import SyncNetWorkRequest
from ...parse.episode.tree import Attribute
from ...parse.parser.base import ParserBase

from ...common.enum import DownloadType, MediaType
from ...common.translator import Translator
from ...common._json import json_dumps
from ...common.config import config

from ..parse.video_info import VideoInfoParser
from ..parse.audio_info import AudioInfoParser
from ..task.info import TaskInfo

from urllib.parse import urlencode
import logging
import time

logger = logging.getLogger(__name__)

# 解析失败后的自动重试。批量下载几百个视频时，总会有少数任务撞上 CDN 节点抖动或接口风控，
# 原先一次失败任务就直接判死，需要用户手动重试。这里只重试一次：链接探测本身已经是
# 并发 + 节点熔断，失败节点在重试时会被降权跳过，一次重试足以穿过大部分瞬时故障，
# 再多则会长时间占着下载并发额度
PARSE_MAX_ATTEMPTS = 2
PARSE_RETRY_DELAY = 3

# playurl 接口的这些错误码属于风控或服务端临时故障，重试有意义；
# 其余错误码（无此视频、需要大会员等）无论重试多少次结果都一样
RETRYABLE_API_CODES = {-352, -412, -500, -504, -509}

class ParseAbortError(RuntimeError):
    # 明确不该重试的错误，与网络抖动区分开
    pass

class ParseWorker(QRunnable, ParserBase):
    def __init__(self, task_info: TaskInfo, parent = None, on_finished = None, stop_event = None):
        super().__init__()

        self.task_info = task_info
        self.info_data: dict = None

        self.parent = parent

        # 用户暂停 / 取消 / 删除任务时置位，重试等待期间要能及时退出
        self.stop_event = stop_event

        # 解析期间本 worker 一直持有 parent 的裸引用，结束时通知 parent 可以安全销毁
        self.on_finished = on_finished

    def run(self):
        try:
            self.run_with_retry()

        except Exception:
            # 兜底：异常抛到 QRunnable 之外会被 Qt 静默吞掉，出问题时日志里毫无线索
            logger.exception("解析流程异常退出")

        finally:
            if self.on_finished:
                try:
                    self.on_finished()

                except Exception:
                    logger.exception("通知下载器解析结束失败")

    def run_with_retry(self):
        error_message = Translator.ERROR_MESSAGES("UNKNOWN_ERROR")

        for attempt in range(1, PARSE_MAX_ATTEMPTS + 1):
            if self.is_stopped():
                return

            try:
                self.info_data = None

                self.get_info()

                download_info = self.parse_download_info()
                download_info_json = json_dumps(download_info)

                if self.is_stopped():
                    return

                QMetaObject.invokeMethod(
                    self.parent,
                    "on_parse_finished",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, download_info_json)     # 由于不支持直接传递字典，所以传递 json 字符串，在主线程再转换回来
                )

                return

            except ParseAbortError as e:
                logger.error("解析下载链接失败，该错误不可重试：%s", e)

                error_message = str(e)

                break

            except Exception as e:
                logger.warning("解析下载链接失败（第 %s/%s 次尝试）", attempt, PARSE_MAX_ATTEMPTS, exc_info = True)

                error_message = str(e)

                if attempt >= PARSE_MAX_ATTEMPTS:
                    break

                if not self.wait_before_retry():
                    return

        self.on_parse_error("{}\n\n{}".format(Translator.ERROR_MESSAGES("PARSE_FAILED"), error_message))

    def is_stopped(self) -> bool:
        return self.stop_event is not None and self.stop_event.is_set()

    def wait_before_retry(self) -> bool:
        # 分段休眠，用户暂停或取消时能及时退出，不必等满整个退避时间。
        # 返回 False 表示等待期间任务已被中止
        remaining = PARSE_RETRY_DELAY

        while remaining > 0:
            if self.is_stopped():
                return False

            interval = min(0.2, remaining)

            time.sleep(interval)

            remaining -= interval

        return True

    def get_info(self):
        attr = self.task_info.Episode.attribute

        if attr & Attribute.VIDEO_BIT:
            self.get_video_info()

        elif attr & Attribute.BANGUMI_BIT:
            self.get_bangumi_info()

        elif attr & Attribute.CHEESE_BIT:
            self.get_cheese_info()

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

    def get_audio_info(self):
        params = {
            "sid": self.task_info.Episode.sid,
            "privilege": 2,
            "quality": 2
        }

        url = f"https://www.bilibili.com/audio/music-service-c/web/url?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        response["data"]["format"] = "m4a"

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
        QMetaObject.invokeMethod(
            self.parent,
            "on_parse_error",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, error_message)
        )

    def check_response(self, response: dict):
        # 这里只负责抛出异常，错误上报统一交给 run_with_retry：
        # 原先在这里直接调用 on_parse_error，外层捕获异常后又报了一次，界面会弹两条错误提示
        code = response.get("code", -1)

        if code != 0:
            message = "{message}（错误码 {code}）".format(message = response.get("message") or "无法获取下载链接", code = code)

            if code in RETRYABLE_API_CODES:
                raise RuntimeError(message)

            raise ParseAbortError(message)
        
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
