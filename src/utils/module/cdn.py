import re

from utils.config import Config
from utils.common.map import cdn_map

class CDN:
    def get_cdn_list():
        if Config.Advanced.enable_switch_cdn:
            return [entry["cdn"] for entry in cdn_map]
        else:
            return [None]
        
    def replace_cdn(url: str, cdn: str):
        if cdn:
            return re.sub(r'(?<=https://)[^/]+', cdn, url)
        else:
            return url