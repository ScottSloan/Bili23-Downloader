from util.common import config

from functools import reduce
from hashlib import md5
import urllib.parse
import logging
import time
import re

logger = logging.getLogger(__name__)

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

class ParserBase:
    def __init__(self):
        self.url = ""
        self.info_data = {}
        # 停止标记，用于跳转链接时停止当前解析流程
        self.stop_flag = False

        self.error_message = ""

    def find_str(self, pattern: str, url: str, check: bool = True):
        result = re.findall(pattern, url)

        if check and not result:
            raise ValueError("无效的链接")
        
        return result[0]
    
    def enc_wbi(self, params: dict):
        def getMixinKey(orig: str):
            return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, "")[:32]
                
        mixin_key = getMixinKey(config.get(config.img_key) + config.get(config.sub_key))
        curr_time = round(time.time())

        params["wts"] = curr_time
        params = dict(sorted(params.items()))
        params = {
            k : "".join(filter(lambda chr: chr not in "!'()*", str(v)))
            for k, v 
            in params.items()
        }
        
        query = urllib.parse.urlencode(params)
        wbi_sign = md5((query + mixin_key).encode()).hexdigest()
        params["w_rid"] = wbi_sign

        return urllib.parse.urlencode(params)
    
    def on_error(self, message: str):
        self.error_message = message

        logger.error(message)

    def check_response(self, response: dict):
        if self.error_message:
            raise Exception(self.error_message)
        
        if response.get("code", -1) != 0:
            raise Exception(response.get("message", "未知错误"))
    
    def get_extra_data(self) -> dict:
        return {}
    