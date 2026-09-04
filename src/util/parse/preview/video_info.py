from PySide6.QtCore import QObject, Slot

from ...common.data import reversed_video_quality_map
from ...common.signal_bus import signal_bus
from ...common.enum import MediaType
from ...common.config import config

from ...thread.async_ import AsyncTask

from ..quality import parse_declared_quality_map, merge_video_streams

from .worker import QueryInfoWorker
from .info import PreviewerInfo

from collections import defaultdict
from typing import Callable

class VideoInfoParser(QObject):
    # 继承 QObject 是为了让 QueryInfoWorker 的信号能排队回 GUI 线程：
    # callback 指向下载选项对话框的控件方法，在查询线程里直连调用等于在子线程操作 QWidget
    def __init__(self):
        super().__init__()

        self.callback: Callable = None
        self.video_info_map = {}
        # support_formats 声明的「画质 -> 编码」，缺失时为 None，表示只能以 dash.video 为准
        self.declared_quality_map = None
        self.available_quality_list = []

        signal_bus.parse.query_video_info.connect(self.query_info)

    def _get_dash_available_quality_list(self):
        for entry in PreviewerInfo.info_data["dash"]["video"].copy():
            self.video_info_map[entry["id"]][entry["codecid"]] = entry.copy()

        # 画质列表以 support_formats 的声明为准，而不是响应里实际给到的流：
        # 少数稿件一次请求拿不全所有档位，据 dash.video 建列表会漏掉可选画质，原因见 quality.py。
        # 只对普通视频这么做：番剧、课程同样带 support_formats，但它们的流要走各自的接口取，
        # 缺档时按普通视频的 playurl 去补只会拿到对不上的结果
        if PreviewerInfo.info_data.get("parser_type") == "video":
            self.declared_quality_map = parse_declared_quality_map(PreviewerInfo.info_data)

        if self.declared_quality_map:
            return list(self.declared_quality_map.keys())

        return sorted(self.video_info_map.keys(), reverse = True)
    
    def _get_mp4_available_quality_list(self):
        accept_quality_list = PreviewerInfo.info_data["accept_quality"].copy()
        
        for quality_id in accept_quality_list.copy():
            self.video_info_map[quality_id][7] = {
                "id": quality_id,
                "codecid": 7,
                "frame_rate": 0,
                "bandwidth": 0,
                "timelength": 0
            }

        return accept_quality_list

    def get_available_quality_list(self):
        match PreviewerInfo.media_type:
            case MediaType.DASH:
                return self._get_dash_available_quality_list()
            
            case MediaType.MP4 | MediaType.FLV:
                return self._get_mp4_available_quality_list()
            
            case MediaType.UNKNOWN | MediaType.M4A:
                return []

    def get_available_codec_list(self, video_quality_id: int):
        codec_list = list(self.video_info_map[video_quality_id].keys())

        if codec_list:
            return codec_list

        # 该档位的流尚未取到，用 support_formats 声明的编码顶上，实测两者始终一致
        return (self.declared_quality_map or {}).get(video_quality_id, [])

    def parse_quality_info(self):
        self.video_info_map = defaultdict(lambda: defaultdict(dict))
        self.declared_quality_map = None

        initial_data = {
            "auto": 200
        }

        self.available_quality_list = self.get_available_quality_list()

        for quality_id in self.available_quality_list.copy():
            quality_str = reversed_video_quality_map.get(quality_id)

            initial_data[quality_str] = quality_id
        
        PreviewerInfo.video_quality_choice_data = initial_data.copy()

    def parse_codec_info(self):
        initial_data = {
            "auto": 20,
            "AVC/H.264": 7,
            "HEVC/H.265": 12,
            "AV1": 13
        }

        PreviewerInfo.video_codec_choice_data = initial_data.copy()

    def query_info(self, video_quality_id: int, video_codec_id: int, callback: Callable):
        self.callback = callback

        quality_id, codec_id = self.resolve_target(video_quality_id, video_codec_id)

        if quality_id is None:
            self._invoke_callback(None)
            return

        if cached_info := PreviewerInfo.cache["video"][quality_id][codec_id]:
            self._invoke_callback(cached_info)
            return

        video_info = self.video_info_map[quality_id][codec_id]

        if video_info and "size" in video_info.keys():
            # 如果已有文件大小无需再 HEAD 请求
            self.on_query_info_success(video_info, video_info["size"])
            return

        # 该档位的流不在首次响应里，交给 worker 在子线程补取后再查文件大小
        supplement = None if video_info else (quality_id, codec_id)

        worker = QueryInfoWorker(video_info, supplement)
        worker.success.connect(self.on_query_info_success)
        worker.supplement_ready.connect(self.on_supplement_ready)
        # 连到 lambda 会在查询线程里就地执行，改用本对象的方法由 Qt 排队回 GUI 线程
        worker.error.connect(self.on_query_info_error)

        AsyncTask.run(worker)

    @Slot(list)
    def on_supplement_ready(self, stream_list: list):
        merge_video_streams(self.video_info_map, stream_list)

    @Slot(dict, object)
    def on_query_info_success(self, media_info: dict, file_size: int):
        quality_id = media_info["id"]
        codec_id = media_info["codecid"]

        merge_video_streams(self.video_info_map, [media_info])

        info = {
            "quality_id": quality_id,
            "frame_rate": media_info["frame_rate"],
            "bitrate": media_info["bandwidth"],
            "file_size": file_size,
            "codec_id": codec_id,
            "is_full_video": self.check_is_full_video(media_info)
        }

        PreviewerInfo.cache["video"][quality_id][codec_id] = info.copy()

        self._invoke_callback(info)

    @Slot(str)
    def on_query_info_error(self, error: str):
        self._invoke_callback(None)

    def _invoke_callback(self, info: dict):
        if not self.callback:
            return

        try:
            self.callback(info)

        except RuntimeError:
            # 回调指向下载选项对话框的控件，排队执行时对话框可能已经关闭，C++ 对象已销毁
            pass

    def resolve_target(self, video_quality_id: int, video_codec_id: int):
        # 只定位最终的画质与编码，对应的流可能还没取到，由调用方负责按需补取
        if not self.available_quality_list:
            return None, None

        if video_quality_id == 200:
            video_quality_id = self.get_video_quality_id_by_priority()

        elif video_quality_id not in self.available_quality_list:
            video_quality_id = self.available_quality_list[0]

        available_codec_list = self.get_available_codec_list(video_quality_id)

        if not available_codec_list:
            return None, None

        if video_codec_id == 20 or video_codec_id not in available_codec_list:
            video_codec_id = self.get_video_codec_id_by_priority(video_quality_id)

        return video_quality_id, video_codec_id

    def get_video_quality_id_by_priority(self):
        # 以声明的档位为准，缺流的档位同样参与优先级匹配，否则会错选成更高的画质
        for quality_id in config.get(config.video_quality_priority):
            if quality_id in self.available_quality_list:
                return quality_id

        return self.available_quality_list[0]

    def get_video_codec_id_by_priority(self, video_quality_id: int):
        available_codec_list = self.get_available_codec_list(video_quality_id)

        for codec_id in config.get(config.video_codec_priority):
            if codec_id in available_codec_list:
                return codec_id

        return available_codec_list[0]

    def check_is_full_video(self, media_info: dict):
        match PreviewerInfo.media_type:
            case MediaType.DASH:
                # dash 格式视频一定是完整的
                return True

            case MediaType.MP4 | MediaType.FLV:
                # 只需要检查 mp4 和 flv 格式
                return PreviewerInfo.info_data["timelength"] == media_info["timelength"]
