from ...network.request import SyncNetWorkRequest, ResponseType
from ...common._json import json_loads
from .base import ParserBase

import re

class FestivalParser(ParserBase):
    def __init__(self):
        super().__init__()
        
    def parse(self, url: str):
        self.url = url

        new_url = self.get_festival_info()

        if new_url:
            return new_url
        else:
            raise RuntimeError("无效的链接")

    def get_festival_info(self):
        request = SyncNetWorkRequest(self.url, response_type = ResponseType.TEXT, raise_for_status = self.raise_for_status)
        response: str = request.run()

        # 查找 window.__INITIAL_STATE__ = 后面的 JSON 数据
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", response, re.DOTALL)

        if match:
            json_data = match.group(1)
            
            try:
                info_data: dict = json_loads(json_data)
                
                bvid = info_data["videoInfo"]["bvid"]

                return f"https://www.bilibili.com/video/{bvid}"

            except Exception as e:
                raise RuntimeError("JSON 解码失败: " + str(e))

        else:
            raise RuntimeError("无效的链接")

        