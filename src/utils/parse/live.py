from utils.config import Config

from utils.common.enums import StatusCode
from utils.common.model.live_room_info import LiveRoomInfo
from utils.common.model.callback import ParseCallback
from utils.common.request import RequestUtils

from utils.parse.parser import Parser

class LiveParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_room_id(self, url: str):
        room_id = self.re_find_str(r"live.bilibili.com/([0-9]+)", url)

        return int(room_id[0])

    def get_live_room_info(self, room_id: int):
        # 获取直播间信息
        params = {
            "req_biz": "web_room_componet",
            "room_ids": room_id
        }

        url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        data: dict = self.json_get(resp, "data")["by_room_ids"]

        if json_data := data.get(room_id):
            self.info_json: dict = json_data

        elif json_data := data.get(str(room_id)):
            self.info_json: dict = json_data

    @classmethod
    def get_live_stream_info(cls, room_id: int):
        params = {
            "room_id": room_id,
            "protocol": 0,
            "format": 0,
            "codec": "0,1"
        }

        url = f"https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?{cls.url_encode(params)}"

        resp = cls.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        data = cls.json_get(resp, "data")

        return data["playurl_info"]["playurl"]

    def parse_worker(self, url: str):
        self.room_id = self.get_room_id(url)

        self.get_live_room_info(self.room_id)

        return StatusCode.Success.value

    def get_live_info(self):
        info = LiveRoomInfo()

        info.cover_url = self.info_json.get("cover")
        info.room_id = self.room_id
        info.up_name = self.info_json.get("uname")
        info.title = self.info_json.get("title")
        info.parent_area = self.info_json.get("parent_area_name")
        info.area = self.info_json.get("area_name")

        info.live_status = self.info_json.get("live_status")

        return info
    
    def get_parse_type_str(self):
        return "直播"