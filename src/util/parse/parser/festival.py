from util.network import SyncNetWorkRequest, ResponseType

from .base import ParserBase

import json
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
            raise Exception("无效的链接")

    def get_festival_info(self):
        request = SyncNetWorkRequest(self.url, response_type = ResponseType.TEXT)
        response: str = request.run()

        # 查找 window.__INITIAL_STATE__ = 后面的 JSON 数据
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", response, re.DOTALL)

        if match:
            json_data = match.group(1)
            
            try:
                info_data: dict = json.loads(json_data)
                
                bvid = info_data["videoInfo"]["bvid"]

                return f"https://www.bilibili.com/video/{bvid}"

            except Exception as e:
                raise Exception("JSON 解码失败: " + str(e))

        else:
            raise Exception("无效的链接")

        