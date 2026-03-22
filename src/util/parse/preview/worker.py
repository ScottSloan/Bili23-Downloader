from PySide6.QtCore import QObject, Slot, Signal

from util.network.request import NetworkRequestWorker, RequestType, ResponseType
from util.parse.preview.info import PreviewerInfo
from util.common.enum import MediaType
from util.thread import SyncTask
from util.network import CDN

class QueryInfoWorker(QObject):
    success = Signal(dict, object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, media_info: dict):
        super().__init__()

        self.media_info = media_info
        self.file_size = 0
        self.break_flag = False

    @Slot()
    def run(self):
        try:
            match MediaType(PreviewerInfo.media_type):
                case MediaType.DASH:
                    self.query_dash_file_size()

                case MediaType.MP4:
                    self.query_mp4_file_size()

            self.success.emit(self.media_info, self.file_size)
        
        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.finished.emit()

    def query_dash_file_size(self):
        download_urls = self.get_download_urls(self.media_info)

        self.get_dash_file_size(download_urls)

    def query_mp4_file_size(self):
        query_url = self.get_query_url(self.media_info["id"])

        self.get_mp4_file_size(query_url)

    def get_dash_file_size(self, download_urls: list):
        def on_success(response: dict):
            content_length = response.get("Content-Length")
            content_type = response.get("Content-Type")

            if content_type is None or "text" in content_type:
                # 链接不可用
                return
            
            if content_length is None or content_length == "0":
                # 无法获取文件大小
                return

            self.break_flag = True

            self.file_size = int(content_length)

        download_urls = CDN.get_url_list(download_urls)

        for url in download_urls:
            worker = NetworkRequestWorker(url, request_type = RequestType.HEAD, response_type = ResponseType.HEADERS, raise_for_status = False)
            worker.success.connect(on_success)

            SyncTask.run(worker)

            if self.break_flag:
                break

    def get_mp4_file_size(self, query_url: str):
        def on_success(response: dict):
            durl = self.get_durl(response)

            self.file_size = durl.get("size", 0)
            self.media_info["timelength"] = durl.get("length", 0)

        worker = NetworkRequestWorker(query_url)
        worker.success.connect(on_success)

        SyncTask.run(worker)

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
        query_url: str = PreviewerInfo.info_data.get("query_url")
        query_url = query_url.replace("qn=80", f"qn={quality_id}")

        return query_url

    def get_durl(self, response: dict):
        match PreviewerInfo.info_data.get("parser_type"):
            case "video":
                return response["data"]["durl"][0]

            case "bangumi":
                return response["result"]["durl"][0]

            case "cheese":
                return response["data"]["durl"][0]
            