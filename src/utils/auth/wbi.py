import time
import requests
import urllib.parse
from hashlib import md5
from functools import reduce

from utils.config import Config
from utils.tool_v2 import RequestTool

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

class WbiUtils:
    def __init__(self):
        _params = {"foo": "114", "bar": "514", "baz": 1919180}

        img_key, sub_key = self.getWbiKeys()
        self.encWbi(_params, img_key, sub_key)

    def encWbi(self, params: dict, img_key: str, sub_key: str):
        def getMixinKey(orig: str):
            return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

        mixin_key = getMixinKey(img_key + sub_key)
        curr_time = round(time.time())
        params['wts'] = curr_time
        params = dict(sorted(params.items()))
        params = {
            k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
            for k, v 
            in params.items()
        }
        query = urllib.parse.urlencode(params)
        
        Config.Auth.wbi_key = md5((query + mixin_key).encode()).hexdigest()

    def getWbiKeys(self):
        resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers = RequestTool.get_headers(referer_url = "https://www.bilibili.com"))
        json_content = resp.json()

        img_url: str = json_content['data']['wbi_img']['img_url']
        sub_url: str = json_content['data']['wbi_img']['sub_url']

        img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]

        return img_key, sub_key
