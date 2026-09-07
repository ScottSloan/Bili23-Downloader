from PySide6.QtCore import QObject, Slot

from ...common.data import audio_reorder_map, reversed_audio_quality_map
from ...common.signal_bus import signal_bus
from ...common.enum import MediaType
from ...common.config import config

from ...thread.async_ import AsyncTask

from .worker import QueryInfoWorker
from .info import PreviewerInfo
from .quality_base import AudioQualityBase

from collections import defaultdict
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class AudioInfoParser(AudioQualityBase, QObject):
    # 继承 QObject 是为了让 QueryInfoWorker 的信号能排队回 GUI 线程，原因见 VideoInfoParser
    def __init__(self):
        super().__init__()

        self.callback: Callable = None
        self.audio_quality_info_map = {}

        signal_bus.parse.query_audio_info.connect(self.query_info)

    def query_info(self, audio_quality_id: int, callback: Callable):
        self.callback = callback

        audio_info = self.get_audio_info(audio_quality_id)

        if audio_info:
            quality_id = audio_info["id"]

            if cached_info := PreviewerInfo.cache["audio"][quality_id]:
                self._invoke_callback(cached_info)

            else:
                if "size" in audio_info.keys():
                    # 如果已有文件大小无需再 HEAD 请求
                    file_size = audio_info["size"]

                    self.on_query_info_success(audio_info, file_size)
                else:
                    worker = QueryInfoWorker(audio_info)
                    worker.success.connect(self.on_query_info_success)
                    # 连到 lambda 会在查询线程里就地执行，改用本对象的方法由 Qt 排队回 GUI 线程
                    worker.error.connect(self.on_query_info_error)

                    AsyncTask.run(worker)

        else:
            self._invoke_callback(None)

    @Slot(dict, object)
    def on_query_info_success(self, media_info: dict, file_size: int):
        quality_id = media_info["id"]

        info = {
            "quality_id": quality_id,
            "file_size": file_size,
            "bitrate": media_info["bandwidth"],
            "codec": media_info["codecs"]
        }

        if quality_id not in PreviewerInfo.cache["audio"]:
            PreviewerInfo.cache["audio"][quality_id] = info.copy()

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

    def get_audio_info(self, audio_quality_id: int):
        if audio_quality_id == 30300:
            return self.get_audio_info_by_priority()

        else:
            return self.audio_quality_info_map.get(audio_quality_id, {})

    def get_audio_info_by_priority(self):
        for quality_id in config.get(config.audio_quality_priority):
            if quality_id in self.audio_quality_info_map.keys():
                return self.audio_quality_info_map.get(quality_id, {})
