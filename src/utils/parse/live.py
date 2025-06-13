from utils.config import Config

from utils.common.exception import GlobalException
from utils.common.map import live_status_map
from utils.common.enums import StatusCode, LiveQualityID
from utils.common.data_type import ParseCallback
from utils.common.request import RequestUtils
from utils.common.file_name_v2 import FileNameFormatter

from utils.parse.episode import EpisodeInfo, EpisodeUtils
from utils.parse.parser import Parser

class LiveInfo:
    title: str = ""

    room_id: int = 0
    short_id: int = 0

    status: int = 0
    status_str: str = ""

    m3u8_link: str = ""

    live_quality_id_list: list = []
    live_quality_desc_list: list = []

    @classmethod
    def clear_live_info(cls):
        cls.title = ""

        cls.room_id = 0
        cls.short_id = 0

        cls.status = 0
        cls.status_str = ""

        cls.live_quality_id_list.clear()
        cls.live_quality_desc_list.clear()

class LiveParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_short_id(self, url: str):
        short_id = self.re_find_str(r"live.bilibili.com/([0-9]+)", url)

        LiveInfo.short_id = short_id[0]

    def get_live_room_info(self):
        # 获取直播间信息
        url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={LiveInfo.short_id}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        info = resp["data"]

        LiveInfo.title = FileNameFormatter.get_legal_file_name(info["title"])
        LiveInfo.room_id = info["room_id"]

        LiveInfo.status = info["live_status"]
        LiveInfo.status_str = live_status_map[LiveInfo.status]

        EpisodeInfo.clear_episode_data("直播")

        EpisodeUtils.live_episode_parser(LiveInfo.title, LiveInfo.status_str)

    def get_live_available_media_info(self):
        url = f"https://api.live.bilibili.com/room/v1/Room/playUrl?cid={LiveInfo.room_id}&platform=h5"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        info = resp["data"]

        quality_description = info["quality_description"]

        LiveInfo.live_quality_id_list = [entry["qn"] for entry in quality_description]
        LiveInfo.live_quality_desc_list = [entry["desc"] for entry in quality_description]

    def get_live_stream(self, qn: int):
        if qn == LiveQualityID._Auto.value:
            qn = max(LiveInfo.live_quality_id_list)

        url = f"https://api.live.bilibili.com/room/v1/Room/playUrl?cid={LiveInfo.room_id}&platform=h5&qn={qn}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        info = resp["data"]

        LiveInfo.m3u8_link = info["durl"][0]["url"]

    def parse_url(self, url: str):
        def worker():
            LiveInfo.clear_live_info()

            self.get_short_id(url)

            self.get_live_room_info()

            self.get_live_available_media_info()

            return StatusCode.Success.value
        
        try:
            return worker()

        except Exception as e:
            raise GlobalException(callback = self.callback.onError) from e
