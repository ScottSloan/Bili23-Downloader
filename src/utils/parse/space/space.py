import math
import time

from utils.config import Config
from utils.auth.wbi import WbiUtils

from utils.common.request import RequestUtils
from utils.common.enums import StatusCode, ProcessingType
from utils.common.model.callback import ParseCallback

from utils.parse.parser import Parser
from utils.parse.episode.space import Space

class SpaceParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_mid(self, url: str):
        mid = self.re_find_str(r"/([0-9]+)", url)

        return mid[0]

    def get_search_arc_info(self, mid: int, pn: int = 1):
        params = {
            "pn": pn,
            "ps": 42,
            "tid": 0,
            "order": "pubdate",
            "mid": mid,
            "index": 0,
            "keyword": "",
            "platform": "web",
            "order_avoided": "true",
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
            "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
        }

        url = f"https://api.bilibili.com/x/space/wbi/arc/search?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        vlist = resp["data"]["list"]["vlist"]

        self.info_json["episodes"].extend(vlist)

        self.total_data += len(vlist)

        return resp["data"]["page"]["count"]
    
    def get_collection_video_info(self, bvid: str):
        params = {
            "bvid": bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        info_json: dict = resp["data"]

        return info_json

    def get_uname_by_mid(self, mid: int):
        params = {
            "mid": mid,
            "token": "",
            "platform": "web",
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
            "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
        }

        url = f"https://api.bilibili.com/x/space/wbi/acc/info?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        return resp["data"]["name"]

    def get_video_available_media_info(self):
        from utils.parse.video import VideoParser

        episode: dict = self.info_json["episodes"][0]

        self.bvid = episode.get("bvid")
        cid = VideoParser.get_video_extra_info(self.bvid).get("cid")

        VideoParser.get_video_available_media_info(self.bvid, cid)

        self.parse_episodes()

    def parse_space_info(self, mid: int):
        total = self.get_search_arc_info(mid)
        total_page = self.get_total_page(total)

        self.onUpdateName("个人主页")
        self.onUpdateTitle(1, total_page, self.total_data)

        for i in range(1, total_page):
            page = i + 1

            self.get_search_arc_info(mid, page)

            self.onUpdateTitle(page, total_page, self.total_data)

        self.parse_video_info()
    
    def parse_video_info(self):
        self.video_info_dict = {}

        for entry in self.info_json.get("episodes"):
            bvid = entry.get("bvid")

            self.onUpdateName(entry["title"])
            self.onUpdateTitle(1, 1, self.total_data)

            if (season_id := entry["season_id"]) and season_id not in self.video_info_dict:
                self.video_info_dict[season_id] = self.get_collection_video_info(bvid).copy()

            else:
                self.video_info_dict[bvid] = self.get_collection_video_info(bvid).copy()

            time.sleep(0.1)

    def parse_worker(self, url: str):
        self.clear_space_info()

        self.mid = self.get_mid(url)

        time.sleep(0.5)

        self.callback.onChangeProcessingType(ProcessingType.Page)

        self.parse_space_info(self.mid)

        self.uname = self.get_uname_by_mid(self.mid)

        self.get_video_available_media_info()

        return StatusCode.Success.value
    
    def parse_episodes(self):
        parent_title = f"{self.uname}_{self.mid}"

        Space.parse_episodes(self.info_json, self.bvid, self.video_info_dict, parent_title)

    def clear_space_info(self):
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
        return math.ceil(total / 42)
    
    def get_parse_type_str(self):
        return "个人主页"