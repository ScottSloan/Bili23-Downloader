from typing import List
from urllib.parse import urlparse, urlunparse

from utils.config import Config
from utils.common.request import RequestUtils

class CDN:
    bilibili_url = "https://www.bilibili.com/"

    @staticmethod
    def replace_host(url: str, cdn_host: str):
        parsed_url = urlparse(url)._replace(netloc = cdn_host)

        return urlunparse(parsed_url)
    
    @staticmethod
    def get_cdn_host_list():
        if Config.Advanced.enable_switch_cdn:
            return Config.Advanced.cdn_list

    @classmethod
    def get_file_size(cls, url_list: List[str]):
        for download_url in url_list:
            if cdn_host_list := cls.get_cdn_host_list():
                for cdn_host in cdn_host_list:
                    new_url = CDN.replace_host(download_url, cdn_host)

                    file_size = cls.request_head(new_url)

                    if file_size:
                        return (new_url, file_size)
            else:
                file_size = cls.request_head(download_url)

                if file_size:
                    return (download_url, file_size)
                
        # 未通过 CDN 获取到有效文件大小，尝试不使用 CDN 直连获取
        if Config.Advanced.enable_switch_cdn:
            for download_url in url_list:
                file_size = cls.request_head(download_url)

                if file_size:
                    return (download_url, file_size)
                
    @classmethod
    def get_file_size_ex(cls, url_list: List[str]):
        for download_url in url_list:
            file_size = cls.request_head(download_url)

            if file_size:
                return (download_url, file_size)
            
        return cls.get_file_size(url_list)

    @staticmethod
    def request_head(url: str):
        try:
            req = RequestUtils.request_head(url, headers = RequestUtils.get_headers(referer_url = CDN.bilibili_url))
        except Exception:
            return 0

        if req.status_code not in (200, 206):
            # 非成功状态码视为无效
            return 0
        
        length = req.headers.get("Content-Length", 0)

        if int(length) < 1024:
            # 小于 1KB 的文件大小视为无效
            return 0

        return int(length)