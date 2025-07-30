from utils.config import Config

from utils.common.exception import GlobalException
from utils.common.map import live_status_map
from utils.common.enums import StatusCode, LiveQualityID
from utils.common.data_type import ParseCallback
from utils.common.request import RequestUtils

from utils.parse.parser import Parser

class LiveInfo:
    cover_url: str = ""

    room_id: int = 0

    up_name: str = ""
    title: str = ""

    status: int = 0
    status_str: str = ""

    m3u8_link: str = ""

    live_quality_id_list: list = []
    live_quality_desc_list: list = []

    @classmethod
    def clear_live_info(cls):
        cls.cover_url = ""

        cls.room_id = 0

        cls.up_name = ""
        cls.title = ""

        cls.status = 0
        cls.status_str = ""

        cls.live_quality_id_list.clear()
        cls.live_quality_desc_list.clear()

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

        LiveInfo.status = info["live_status"]
        LiveInfo.status_str = live_status_map[LiveInfo.status]

    def get_live_available_media_info(self):
        params = {
            "room_id": LiveInfo.room_id,
            "protocol": 0,
            "format": 0,
            "codec": "0,1"
        }

        url = f"https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        info = resp["data"]

        #LiveInfo.live_quality_id_list = [entry["qn"] for entry in quality_description]
        #LiveInfo.live_quality_desc_list = [entry["desc"] for entry in quality_description]

    def get_live_stream(self, qn: int):
        if qn == LiveQualityID._Auto.value:
            qn = max(LiveInfo.live_quality_id_list)

        url = f"https://api.live.bilibili.com/room/v1/Room/playUrl?cid={LiveInfo.room_id}&platform=h5&qn={qn}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        info = resp["data"]

        LiveInfo.m3u8_link = info["durl"][0]["url"]

    def parse_worker(self, url: str):
        LiveInfo.clear_live_info()

        self.get_room_id(url)

        self.get_live_room_info()

        #self.get_live_available_media_info()

        return StatusCode.Success.value
