import re

from utils.config import Config

class CDN:
    def get_cdn_list():
        if Config.Advanced.enable_switch_cdn:
            return Config.Advanced.cdn_list
        else:
            return [None]
        
    def replace_cdn(url: str, cdn: str):
        if cdn:
            return re.sub(r'(?<=https://)[^/]+', cdn, url)
        else:
            return url