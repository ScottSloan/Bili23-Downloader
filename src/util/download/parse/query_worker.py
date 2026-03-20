from util.network.request import NetworkRequestWorker, RequestType, ResponseType
from util.thread import SyncTask
from util.network.cdn import CDN

class QueryWorker:
    def __init__(self, media_info: dict):
        self.media_info = media_info

        self.file_size = 0
        self.break_flag = False

    def query_url(self):
        download_urls = self.get_download_urls(self.media_info)

        return self.get_file_size(download_urls)

    def get_file_size(self, download_urls: list):
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
            # 发起 HEAD 请求获取文件大小， raise_for_status 设置为 False，避免因某些 CDN 链接返回 403/404 而导致异常
            worker = NetworkRequestWorker(url, request_type = RequestType.HEAD, response_type = ResponseType.HEADERS, raise_for_status = False)
            worker.success.connect(on_success)

            SyncTask.run(worker)

            if self.break_flag:
                return {
                    "url": url,
                    "file_size": self.file_size
                }

    def get_download_urls(self, media_info: dict):
        download_urls = []

        for key in ["baseUrl", "base_url", "backupUrl", "backup_url", "url", "backup_url"]:
            object = media_info.get(key)

            if isinstance(object, list):
                download_urls.extend(object)

            elif isinstance(object, str):
                download_urls.append(object)

        return download_urls
