from PySide6.QtCore import QObject, Slot, Signal

from ...network.request import SyncNetWorkRequest
from ...network.download_url import resolve_download_url
from ...common.enum import MediaType

from ..quality import fetch_video_streams

from .info import PreviewerInfo

import re

class QueryInfoWorker(QObject):
    success = Signal(dict, object)
    error = Signal(str)
    finished = Signal()
    # 补取一次会连带返回同一组的多个档位，整批带回去并入映射表，
    # 用户接着切到同组的其它档位时就不必再请求一次
    supplement_ready = Signal(list)

    def __init__(self, media_info: dict, supplement: tuple = None):
        super().__init__()

        self.media_info = media_info
        # 该档位的视频流不在首次响应里时，这里带着 (quality_id, codec_id)，
        # 先补取流再查文件大小，补到的流随 success 信号回到 GUI 线程并入 video_info_map
        self.supplement = supplement
        self.file_size = 0
        self.break_flag = False

    @Slot()
    def run(self):
        try:
            match MediaType(PreviewerInfo.media_type):
                case MediaType.DASH:
                    if self.supplement:
                        self.supplement_video_stream()

                    self.query_dash_file_size()

                case MediaType.MP4 | MediaType.FLV:
                    self.query_mp4_file_size()

                case MediaType.M4A:
                    # m4a 借用 dash 的查询方法，虽然实际上 m4a 只有一个质量级别，但仍然需要获取文件大小等信息
                    self.query_dash_file_size()

            if self.file_size == 0:
                raise RuntimeError("无法获取文件大小")
            
            self.success.emit(self.media_info, self.file_size)
        
        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.finished.emit()

    def supplement_video_stream(self):
        quality_id, codec_id = self.supplement

        stream_list = fetch_video_streams(PreviewerInfo.bvid, PreviewerInfo.cid, quality_id)

        matched = [entry for entry in stream_list if entry.get("id") == quality_id]

        if not matched:
            raise RuntimeError("无法获取该清晰度的视频流")

        self.supplement_ready.emit(stream_list)

        # 优先取用户选定的编码，该档位没有这个编码时退回第一个可用的
        self.media_info = next((entry for entry in matched if entry.get("codecid") == codec_id), matched[0]).copy()

    def query_dash_file_size(self):
        download_urls = self.get_download_urls(self.media_info)

        self.get_dash_file_size(download_urls)

    def query_mp4_file_size(self):
        query_url = self.get_query_url(self.media_info["id"])

        self.get_mp4_file_size(query_url)

    def get_dash_file_size(self, download_urls: list):
        result = resolve_download_url(download_urls, min_file_size = 10240)
        self.file_size = result["file_size"]

        return self.file_size

    def get_mp4_file_size(self, query_url: str):
        request = SyncNetWorkRequest(query_url)
        response = request.run()

        for durl_entry in self.get_durl_list(response):            
            self.file_size += durl_entry.get("size", 0)
            self.media_info["timelength"] += durl_entry.get("length", 0)

    def get_download_urls(self, media_info: dict):
        download_urls = []

        for key in ["baseUrl", "base_url", "backupUrl", "backup_url", "url", "backup_url"]:
            object = media_info.get(key)

            if isinstance(object, list):
                download_urls.extend(object)

            elif isinstance(object, str):
                download_urls.append(object)

        return download_urls

    def get_query_url(self, quality_id: int):
        # 按正则替换而不是匹配固定的 qn=80：预览请求的档位会变，
        # 写死字面量会在请求档位调整后悄悄失效
        query_url: str = PreviewerInfo.info_data.get("query_url")

        return re.sub(r"([?&])qn=\d+", rf"\g<1>qn={quality_id}", query_url)

    def get_durl_list(self, response: dict):
        match PreviewerInfo.info_data.get("parser_type"):
            case "video":
                return response["data"]["durl"]

            case "bangumi":
                return response["result"]["durl"]

            case "cheese":
                return response["data"]["durl"]
