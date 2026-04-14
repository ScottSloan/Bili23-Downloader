from util.network.request import RequestType, ResponseType, SyncNetWorkRequest
from util.network.cdn import CDN

class QueryWorker:
    def __init__(self, media_info: dict):
        self.media_info = media_info

        self.file_size = 0
        self.break_flag = False

    def query_dash_url(self):
        download_urls = self.get_download_urls(self.media_info)

        return self.get_file_size(download_urls)
    
    def query_mp4_url(self):
        url_list = []

        for index, url_entry in enumerate(self.media_info["url_entry_list"]):
            download_urls = self.get_download_urls(url_entry)

            url_list.append({
                **self.get_file_size(download_urls),
                "index": index
            })

        return url_list

    def get_file_size(self, download_urls: list):
        download_urls = CDN.get_url_list(download_urls)

        for url in download_urls:                
            # 发起 HEAD 请求获取文件大小

            try:
                request = SyncNetWorkRequest(url, request_type = RequestType.HEAD, response_type = ResponseType.HEADERS, raise_for_status = True)
                response = request.run()
            except:
                # 请求失败，继续尝试下一个链接 (例如 403, 404 等会被精确捕捉)
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

            return {
                "url": url,
                "file_size": self.file_size
            }
        
        raise Exception("无法获取有效的下载链接")

    def get_download_urls(self, media_info: dict):
        download_urls = []

        for key in ["baseUrl", "base_url", "backupUrl", "backup_url", "url", "backup_url"]:
            object = media_info.get(key)

            if isinstance(object, list):
                download_urls.extend(object)

            elif isinstance(object, str):
                download_urls.append(object)

        return download_urls
