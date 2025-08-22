import math
import time

from utils.config import Config
from utils.auth.wbi import WbiUtils

from utils.common.enums import StatusCode, ProcessingType
from utils.common.request import RequestUtils
from utils.common.model.callback import ParseCallback

from utils.parse.parser import Parser
from utils.parse.episode.favlist import FavList

class FavListParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_media_id(self, url: str):
        fid = self.re_find_str(r"fid=(\d+)", url)

        return int(fid[0])
    
    def get_favlist_info(self, media_id: int, pn: int = 1):
        params = {
            "media_id": media_id,
            "pn": pn,
            "ps": 40,
            "keyword": "",
            "order": "mtime",
            "type": 0,
            "tid": 0,
            "platform": "web"
        }

        url = f"https://api.bilibili.com/x/v3/fav/resource/list?{self.url_encode(params)}"

        req = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))
        
        info = req["data"]["info"]
        medias = req["data"]["medias"]

        self.info_json["episodes"].extend(medias)

        self.total_data += len(medias)

        return info["media_count"], info["title"]

    def get_video_info(self, bvid: str):
        params = {
            "bvid": bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        info_json: dict = resp["data"]

        return info_json
    
    def get_bangumi_info(self, season_id: int):
        params = {
            "season_id": season_id
        }

        url = f"https://api.bilibili.com/pgc/view/web/season?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))
        
        info_json: dict = resp["result"]

        return info_json

    def get_video_available_media_info(self):
        from utils.parse.video import VideoParser

        episode: dict = self.info_json["episodes"][0]

        self.bvid = episode.get("bvid")
        cid = VideoParser.get_video_extra_info(self.bvid).get("cid")

        VideoParser.get_video_available_media_info(self.bvid, cid)

        self.parse_episodes()

    def parse_favlist_info(self, media_id: int):
        total, title = self.get_favlist_info(media_id)
        total_page = self.get_total_page(total)

        self.onUpdateName(title)
        self.onUpdateTitle(1, total_page, self.total_data)

        for i in range(1, total_page):
            page = i + 1

            self.get_favlist_info(media_id, page)

            self.onUpdateTitle(page, total_page, self.total_data)

        self.parse_video_info()

    def parse_video_info(self):
        self.season_dict = {
            "video": {},
            "bangumi": {}
        }

        for entry in self.info_json.get("episodes"):
            self.onUpdateName(entry['title'])
            self.onUpdateTitle(1, 1, self.total_data)

            if entry.get("page") != 0:
                bvid = entry.get("bvid")

                self.season_dict["video"][bvid] = self.get_video_info(bvid)
            
            elif entry.get("ogv"):
                season_id = entry["ogv"]["season_id"]

                self.season_dict["bangumi"][season_id] = self.get_bangumi_info(season_id)

            time.sleep(0.1)
    
    def parse_worker(self, url: str):
        self.clear_favlist_info()

        media_id = self.get_media_id(url)

        time.sleep(0.5)

        self.callback.onChangeProcessingType(ProcessingType.Page)

        self.parse_favlist_info(media_id)

        self.get_video_available_media_info()

        return StatusCode.Success.value
    
    def parse_episodes(self):
        FavList.parse_episodes(self.info_json, self.bvid, self.season_dict)
    
    def clear_favlist_info(self):
        self.info_json = {
            "episodes": []
        }

        self.total_data = 0

    def onUpdateName(self, name: str):
        self.callback.onUpdateName(name)

    def onUpdateTitle(self, page: int, total_page: int, total_data: int):
        self.callback.onUpdateTitle(f"当前第 {page} 页，共 {total_page} 页，已解析 {total_data} 条数据")

        time.sleep(0.3)

    def get_total_page(self, total: int):
        return math.ceil(total / 40)
    
    def get_parse_type_str(self):
        return "收藏夹"