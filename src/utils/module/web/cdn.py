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
                
    @classmethod
    def get_file_size_ex(cls, url_list: List[str]):
        for download_url in url_list:
            file_size = cls.request_head(download_url)

            if file_size:
                return (download_url, file_size)
            
        return cls.get_file_size(url_list)

    @staticmethod
    def request_head(url: str):
        req = RequestUtils.request_head(url, headers = RequestUtils.get_headers(referer_url = CDN.bilibili_url))

        return int(req.headers.get("Content-Length", 0))