import re

from utils.config import Config
from utils.common.enums import CDNMode
from utils.common.map import cdn_map

class CDN:
    def get_cdn_list():
        if Config.Advanced.enable_custom_cdn:
            match CDNMode(Config.Advanced.custom_cdn_mode):
                case CDNMode.Auto:
                    return [entry["cdn"] for entry in cdn_map]
                
                case CDNMode.Custom:
                    return [Config.Advanced.custom_cdn]
        else:
            return [None]
        
    def replace_cdn(url: str, cdn: str):
        if cdn:
            return re.sub(r'(?<=https://)[^/]+', cdn, url)
        else:
            return url