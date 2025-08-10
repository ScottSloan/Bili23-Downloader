from utils.config import Config

from utils.common.enums import StatusCode
from utils.common.model.data_type import LiveRoomInfo
from utils.common.model.callback import ParseCallback
from utils.common.request import RequestUtils

from utils.parse.parser import Parser

class LiveInfo:
    cover_url: str = ""

    room_id: int = 0

    up_name: str = ""
    title: str = ""

    parent_area: str = ""
    area: str = ""

    status: int = 0

    @classmethod
    def clear_live_info(cls):
        cls.cover_url = ""

        cls.room_id = 0

        cls.up_name = ""
        cls.title = ""

        cls.parent_area = ""
        cls.area = ""

        cls.status = 0

class LiveParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_room_id(self, url: str):
        room_id = self.re_find_str(r"live.bilibili.com/([0-9]+)", url)

        LiveInfo.room_id = room_id[0]

    def get_live_room_info(self):
        # 获取直播间信息
        params = {
            "req_biz": "web_room_componet",
            "room_ids": LiveInfo.room_id
        }

        url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        info = resp["data"]["by_room_ids"][LiveInfo.room_id]

        LiveInfo.cover_url = info["cover"]

        LiveInfo.up_name = info["uname"]
        LiveInfo.title = info["title"]

        LiveInfo.parent_area = info["parent_area_name"]
        LiveInfo.area = info["area_name"]

        LiveInfo.status = info["live_status"]

    @classmethod
    def get_live_stream_info(cls, room_id):
        params = {
            "room_id": room_id,
            "protocol": 0,
            "format": 0,
            "codec": "0,1"
        }

        url = f"https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?{cls.url_encode(params)}"

        data = cls.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        return data["data"]["playurl_info"]["playurl"]

    def parse_worker(self, url: str):
        LiveInfo.clear_live_info()

        self.get_room_id(url)

        self.get_live_room_info()

        return StatusCode.Success.value

    def get_live_info(self):
        info = LiveRoomInfo()

        info.cover_url = LiveInfo.cover_url
        info.room_id = LiveInfo.room_id
        info.up_name = LiveInfo.up_name
        info.title = LiveInfo.title
        info.parent_area = LiveInfo.parent_area
        info.area = LiveInfo.area

        info.live_status = LiveInfo.status

        return info