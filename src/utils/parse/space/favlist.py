import math
import time

from utils.config import Config
from utils.auth.wbi import WbiUtils

from utils.common.enums import StatusCode, ProcessingType, TemplateType, ParseType
from utils.common.request import RequestUtils
from utils.common.model.callback import ParseCallback
from utils.common.formatter.file_name_v2 import FileNameFormatter
from utils.common.regex import Regex

from utils.parse.parser import Parser
from utils.parse.episode.episode_v2 import Episode
from utils.parse.episode.favlist import FavList

class FavListParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_media_id(self, url: str):
        if (match := Regex.search(r"fid=(\d+)", url)):
            fid = match[1]
        elif (match := Regex.search(r"ml(\d+)", url)):
            fid = match[1]

        return int(fid)
    
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

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        data = self.json_get(resp, "data")
        
        info = data["info"]
        medias = data["medias"]

        self.fav_title = info["title"]
        self.owner_name = info["upper"]["name"]
        self.owner_mid = info["upper"]["mid"]

        self.info_json["episodes"].extend(medias)

        self.total_data += len(medias)

        return info["media_count"]

    def get_video_info(self, bvid: str) -> dict:
        params = {
            "bvid": bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA), check = False)

        self.total_data += 1

        if data := resp.get("data"):
            data["parse_type"] = ParseType.Video.value

            return data

    def get_bangumi_info(self, season_id: int) -> dict:
        params = {
            "season_id": season_id
        }

        url = f"https://api.bilibili.com/pgc/view/web/season?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA), check = False)
        
        self.total_data += 1

        if data := resp.get("result"):
            data["parse_type"] = ParseType.Bangumi.value

            return data

    def parse_favlist_info(self, media_id: int):
        total = self.get_favlist_info(media_id)
        total_page = self.get_total_page(total)

        self.onUpdateName(self.fav_title)
        self.onUpdateTitle(1, total_page, self.total_data)

        for i in range(1, total_page):
            page = i + 1

            self.get_favlist_info(media_id, page)

            self.onUpdateTitle(page, total_page, self.total_data)

    def parse_video_info(self, video_info_to_parse: list[dict], detail_mode_callback):
        video_info_list = []

        time.sleep(0.5)

        self.change_processing_type(ProcessingType.Page)

        for entry in video_info_to_parse:
            self.onUpdateName(entry["title"])
            self.onUpdateTitle(1, 1, self.total_data)

            bvid = entry.get("bvid")

            match ParseType(entry["type"]):
                case ParseType.Video:
                    video_info_list.append(self.get_video_info(bvid))

                case ParseType.Bangumi:
                    info = self.get_bangumi_info(entry["season_id"])
                    info["target_bvid"] = bvid

                    video_info_list.append(info)

        time.sleep(0.5)

        self.change_processing_type(ProcessingType.Process)

        episode_info_list = Episode.Utils.dict_list_to_tree_item_list(FavList.parse_episodes_detail(video_info_list, self.get_parent_title()))

        detail_mode_callback(episode_info_list)

    def parse_worker(self, url: str):
        self.clear_favlist_info()

        media_id = self.get_media_id(url)

        time.sleep(0.5)

        self.change_processing_type(ProcessingType.Page)

        self.parse_favlist_info(media_id)

        self.parse_episodes()

        self.callback.onUpdateHistory(url, f"{self.owner_name} - {self.fav_title}", self.get_parse_type_str())

        return StatusCode.Success.value
    
    def parse_episodes(self):
        FavList.parse_episodes_fast(self.info_json)
    
    def clear_favlist_info(self):
        self.info_json = {
            "episodes": []
        }

        self.total_data = 0

    def onUpdateName(self, name: str):
        self.callback.onUpdateName(name)

    def onUpdateTitle(self, page: int, total_page: int, total_data: int):
        self.callback.onUpdateTitle(f"当前第 {page} 页，共 {total_page} 页，已解析 {total_data} 条数据")

        time.sleep(0.1)

    def get_total_page(self, total: int):
        return math.ceil(total / 40)
    
    def get_parse_type_str(self):
        return "收藏夹"
    
    def get_parent_title(self):
        template = FileNameFormatter.get_folder_template(TemplateType.Favlist.value)

        field_dict = {
            "up_name": FileNameFormatter.get_legal_file_name(self.owner_name),
            "up_uid": self.owner_mid,
            "favlist_name": FileNameFormatter.get_legal_file_name(self.fav_title)
        }

        return template.format(**field_dict)