import re
import json
import urllib.parse

from utils.common.enums import StatusCode
from utils.common.exception import GlobalException
from utils.common.request import RequestUtils

class Parser:
    bilibili_url = "https://www.bilibili.com"

    def __init__(self):
        self.json_data: dict = None
        self.is_drm: bool = False

    def re_find_str(self, pattern: str, string: str, check: bool = True):
        result = re.findall(pattern, string)
    
        self.check_value(result) if check else 0

        return result

    @classmethod
    def request_get(cls, url: str, headers: dict) -> dict:
        req = RequestUtils.request_get(url, headers)

        req.raise_for_status()

        resp = json.loads(req.text)

        cls.check_json(resp)

        cls.json_data = resp.copy()

        return resp
    
    def request_post(self, url: str, headers: dict, raw_json: dict):
        req = RequestUtils.request_post(url, headers, json = raw_json)

        req.raise_for_status()

        resp = json.loads(req.text)

        self.check_json(resp)

        return resp

    def aid_to_bvid(self, aid: int):
        XOR_CODE = 23442827791579
        MAX_AID = 1 << 51
        ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
        ENCODE_MAP = 8, 7, 0, 5, 1, 3, 2, 4, 6

        bvid = [""] * 9
        tmp = (MAX_AID | aid) ^ XOR_CODE

        for i in range(len(ENCODE_MAP)):
            bvid[ENCODE_MAP[i]] = ALPHABET[tmp % len(ALPHABET)]
            tmp //= len(ALPHABET)

        return "BV1" + "".join(bvid)

    def check_value(self, value: int | str):
        if not value:
            raise GlobalException(code = StatusCode.URL.value)

    @staticmethod
    def check_json(data: dict):
        status_code = data["code"]

        if status_code != StatusCode.Success.value:
            raise GlobalException(message = data["message"], code = status_code, json_data = data)
        
    def parse_url(self, url: str):
        try:
            return self.parse_worker(url)
        
        except KeyError as e:
            raise GlobalException(callback = self.callback.onError, json_data = self.json_data) from e

        except Exception as e:
            raise GlobalException(callback = self.callback.onError) from e

    @staticmethod
    def dumps_json(file_name: str, json_file: dict):
        with open(file_name, "w", encoding = "utf-8") as f:
            f.write(json.dumps(json_file, ensure_ascii = False))

    def parse_worker(self, url: str):
        pass
    
    @staticmethod
    def url_encode(params: dict):
        return urllib.parse.urlencode(params)
    
    def get_parse_type_str(self):
        pass

    def is_interactive_video(self):
        return False
    
    def is_in_section_option_enable(self):
        return True

    def check_drm_protection(self, data: dict):
        if data.get("drm_type"):
            raise GlobalException(code = StatusCode.DRM.value)
        
        if data.get("is_drm"):
            self.is_drm = True