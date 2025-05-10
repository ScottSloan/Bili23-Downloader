import re
import json

from utils.common.enums import StatusCode
from utils.common.exception import GlobalException
from utils.tool_v2 import RequestTool

class Parser:
    def __init__(self):
        self.bilibili_url = "https://www.bilibili.com"

    def re_find_str(self, pattern: str, string: str, check: bool = True):
        result = re.findall(pattern, string)
    
        self.check_value(result) if check else 0

        return result

    def request_get(self, url: str, headers: dict) -> dict:
        req = RequestTool.request_get(url, headers)
        resp = json.loads(req.text)

        self.check_json(resp)

        return resp

    def check_value(self, value: int | str):
        if not value:
            raise GlobalException(code = StatusCode.URL.value)

    def check_json(self, data: dict):
        status_code = data["code"]

        if status_code != StatusCode.Success.value:
            raise GlobalException(message = data["message"], code = status_code)