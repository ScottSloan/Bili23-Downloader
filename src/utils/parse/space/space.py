import math
import time

from utils.config import Config
from utils.auth.wbi import WbiUtils

from utils.common.request import RequestUtils
from utils.common.enums import StatusCode, ProcessingType, TemplateType, ParseType
from utils.common.model.callback import ParseCallback
from utils.common.formatter.file_name_v2 import FileNameFormatter

from utils.parse.parser import Parser
from utils.parse.episode.space import Space
from utils.parse.episode.episode_v2 import Episode

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

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA), check = False)

        if resp["code"] == 0:
            vlist = resp["data"]["list"]["vlist"]

            self.info_json["episodes"].extend(vlist)

            self.total_data += len(vlist)

            return resp["data"]["page"]["count"]
        
        else:
            return "error"
    
    def get_video_info(self, bvid: str, is_avoided: bool):
        params = {
            "bvid": bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        info_json: dict = self.json_get(resp, "data")

        self.total_data += 1

        info_json["is_avoided"] = is_avoided

        return info_json

    def get_cheese_info(self, season_id: int):
        params = {
            "season_id": season_id
        }

        url = f"https://api.bilibili.com/pugv/view/web/season/v2?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        data: dict = self.json_get(resp, "data")

        self.total_data += 1

        return data

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

        data = self.json_get(resp, "data")

        return data["name"]

    def parse_space_info(self, mid: int):
        total = self.get_search_arc_info(mid)
        total_page = self.get_total_page(total)

        self.onUpdateName("个人主页")
        self.onUpdateTitle(1, total_page, self.total_data)

        for i in range(1, total_page):
            page = i + 1

            result = self.get_search_arc_info(mid, page)

            if result != "error":
                self.onUpdateTitle(page, total_page, self.total_data)
                
                time.sleep(self.get_sleep_time())
            else:
                break
    
    def parse_video_info(self, video_info_to_parse: list[dict], detail_mode_callback):
        video_info_list = {
            "sequence": [],
            "video_season": {},
            "video_bvid": {},
            "cheese_season": {}
        }

        time.sleep(0.5)

        self.change_processing_type(ProcessingType.Page)

        for entry in video_info_to_parse:
            self.onUpdateName(entry["title"])
            self.onUpdateTitle(1, 1, self.total_data)

            season_id = entry.get("season_id")
            bvid = entry.get("bvid")

            match ParseType(entry["type"]):
                case ParseType.Video:
                    if season_id and season_id in video_info_list["video_season"]:
                        continue

                    key = "video_season" if season_id else "video_bvid"
                    value = season_id if season_id else bvid
                    is_avoided = True if entry.get("template_type") == TemplateType.Video_Collection.value else False

                    video_info_list[key][value] = self.get_video_info(bvid, is_avoided)

                    video_info_list["sequence"].append({
                        "key": key,
                        "value": value
                    })

                case ParseType.Cheese:
                    video_info_list["cheese_season"][season_id] = self.get_cheese_info(season_id)

        time.sleep(0.5)

        self.change_processing_type(ProcessingType.Process)

        episode_info_list = Episode.Utils.dict_list_to_tree_item_list(Space.parse_episodes_detail(video_info_list, self.get_parent_title()))

        detail_mode_callback(episode_info_list)

    def parse_worker(self, url: str):
        self.clear_space_info()

        self.mid = self.get_mid(url)

        time.sleep(0.5)

        self.change_processing_type(ProcessingType.Page)

        self.parse_space_info(self.mid)

        self.uname = self.get_uname_by_mid(self.mid)

        self.parse_episodes()

        return StatusCode.Success.value
    
    def parse_episodes(self):
        Space.parse_episodes_fast(self.info_json)

    def clear_space_info(self):
        self.info_json = {
            "episodes": []
        }

        self.total_data = 0

    def onUpdateName(self, name: str):
        self.callback.onUpdateName(name)

    def onUpdateTitle(self, page: int, total_page: int, total_data: int):
        self.callback.onUpdateTitle(f"当前第 {page} 页，共 {total_page} 页，已解析 {total_data} 条数据")

    def get_total_page(self, total: int):
        return math.ceil(total / 42)
    
    def get_parse_type_str(self):
        return "个人主页"
    
    def get_parent_title(self):
        template = FileNameFormatter.get_folder_template(TemplateType.Space.value)

        field_dict = {
            "up_name": self.uname,
            "up_uid": self.mid,
        }

        return template.format(**field_dict)
    
    def get_sleep_time(self):
        if self.total_data < 30:
            return 0.1
        
        elif self.total_data < 50:
            return 0.2
        
        elif self.total_data < 100:
            return 0.5
        
        else:
            return 1.0