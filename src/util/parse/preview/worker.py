from PySide6.QtCore import QObject, Slot, Signal

from util.network import RequestType, ResponseType, SyncNetWorkRequest
from util.parse.preview.info import PreviewerInfo
from util.common.enum import MediaType
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

                case MediaType.MP4 | MediaType.FLV:
                    self.query_mp4_file_size()

            if self.file_size == 0:
                raise Exception("无法获取文件大小")
            
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
        download_urls = CDN.get_url_list(download_urls)

        for url in download_urls:
            try:
                request = SyncNetWorkRequest(url, request_type = RequestType.HEAD, response_type = ResponseType.HEADERS, raise_for_status = True)
                response = request.run()
            except:
                # 请求失败，继续尝试下一个链接
                continue
            
            content_length = response.get("Content-Length")
            content_type = response.get("Content-Type")

            if content_type is None or "text" in content_type:
                # 链接不可用
                continue
            
            if content_length is None or not str(content_length).isdigit():
                # 无法获取有效的文件大小
                continue

            self.file_size = int(content_length)

            if self.file_size <= 10240:
                # 如果文件极小（例如某些 CDN 拦截时返回的 1KB 左右错误文本），视为无效链接跳过
                continue

            break

        return int(content_length)

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
        query_url: str = PreviewerInfo.info_data.get("query_url")
        query_url = query_url.replace("qn=80", f"qn={quality_id}")

        return query_url

    def get_durl_list(self, response: dict):
        match PreviewerInfo.info_data.get("parser_type"):
            case "video":
                return response["data"]["durl"]

            case "bangumi":
                return response["result"]["durl"]

            case "cheese":
                return response["data"]["durl"]
            