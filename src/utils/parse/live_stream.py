from utils.config import Config

from utils.common.model.data_type import LiveRoomInfo
from utils.common.request import RequestUtils

from utils.parse.parser import Parser

class LiveStream(Parser):
    def __init__(self, room_info: LiveRoomInfo):
        self.room_info = room_info

    def get_live_stream_url(self):
        params = {
            "room_id": self.room_info.room_id,
            "protocol": 0,
            "format": 0,
            "codec": "0,1",
            "qn": self.room_info.quality
        }

        url = f"https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?{self.url_encode(params)}"

        data = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        stream_info = data["data"]["playurl_info"]["playurl"]["stream"][0]["format"][0]["codec"]

        for entry in stream_info:
            if entry["current_qn"] == self.room_info.quality and entry["codec_name"] == self.room_info.codec:
                for url_entry in entry["url_info"]:
                    return url_entry["host"] + entry["base_url"] + url_entry["extra"]
                
    def get_recorder_info(self):
        return {
            "referer_url": self.bilibili_url,
            "stream_url": self.get_live_stream_url()
        }