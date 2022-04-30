import re
import json
import requests

from utils.config import Config
from utils.tools import *

class BangumiInfo:
    url = epid = ssid = mdid = bvid = ""
    
    title = desc = cover = newep = theme = ""

    view = coin = danmaku = favorite = score = count = quality = cid = 0

    episodes = down_episodes = quality_id = quality_desc = []

    sections = {}

class BangumiParser:
    def media_api(self, mdid: str):
        return "https://api.bilibili.com/pgc/review/user?media_id={}".format(mdid)

    def info_api(self):
        return "https://api.bilibili.com/pgc/view/web/season?{}={}".format(self.argument, self.value)

    def quality_api(self, bvid: str, cid: int) -> str:
        return "https://api.bilibili.com/pgc/player/web/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(bvid, cid)

    def get_epid(self, url: str):
        epid = re.findall(r"ep[0-9]*", url)[0][2:]
        self.set_epid(epid)

    def get_season_id(self, url: str):
        ssid = re.findall(r"ss[0-9]*", url)[0][2:]
        self.set_ssid(ssid)

    def get_media_id(self, url: str):
        mdid = re.findall(r"md[0-9]*", url)[0][2:]

        media_req = requests.get(self.media_api(mdid), headers = get_header(), proxies = get_proxy())
        media_json = json.loads(media_req.text)

        if media_json["code"] != 0:
            self.on_error(400)

        ssid = media_json["result"]["media"]["season_id"]

        self.set_ssid(ssid)

    def set_epid(self, epid: str):
        BangumiInfo.epid, BangumiInfo.url = epid, "https://www.bilibili.com/bangumi/play/ep{}".format(epid)
        self.argument, self.value = "ep_id", epid

    def set_ssid(self, ssid: str):
        BangumiInfo.ssid, BangumiInfo.url = ssid, "https://www.bilibili.com/bangumi/play/ss{}".format(ssid)
        self.argument, self.value = "season_id", ssid

    def get_bangumi_info(self):
        info_request = requests.get(self.info_api(), headers = get_header(), proxies = get_proxy())
        info_json = json.loads(info_request.text)

        if info_json["code"] != 0:
            self.on_error(400)
        
        info_result = info_json["result"]
        BangumiInfo.url = info_result["episodes"][0]["link"]
        BangumiInfo.title = info_result["title"]
        BangumiInfo.cover = info_result["cover"]
        BangumiInfo.desc = info_result["evaluate"]
        BangumiInfo.newep = info_result["new_ep"]["desc"]

        if "rating" in info_result:
            BangumiInfo.count = str(info_result["rating"]["count"])
            BangumiInfo.score = str(info_result["rating"]["score"])

        BangumiInfo.episodes = info_result["episodes"]
        BangumiInfo.sections["正片"] = BangumiInfo.episodes

        if "section" in info_result and Config.show_sections:
            info_section = info_result["section"]

            for section in info_section:
                section_title = section["title"]
                section_episodes = section["episodes"]

                for index, value in enumerate(section_episodes):
                    value["title"] = str(index + 1)

                BangumiInfo.sections[section_title] = section_episodes

        BangumiInfo.url = BangumiInfo.episodes[0]["link"]
        BangumiInfo.bvid = BangumiInfo.episodes[0]["bvid"]
        BangumiInfo.cid = BangumiInfo.episodes[0]["cid"]

        info_stat = info_result["stat"]
        BangumiInfo.view = format_data(info_stat["views"])
        BangumiInfo.coin = format_data(info_stat["coins"])
        BangumiInfo.danmaku = format_data(info_stat["danmakus"])
        BangumiInfo.favorite = format_data(info_stat["favorites"])

        type_id = info_result["type"]

        if type_id == 1:
            BangumiInfo.theme = "番剧"
        elif type_id == 2:
            BangumiInfo.theme = "电影"
        elif type_id == 3:
            BangumiInfo.theme = "纪录片"
        elif type_id == 4:
            BangumiInfo.theme = "国创"
        elif type_id == 5:
            BangumiInfo.theme = "电视剧"
        elif type_id == 7:
            BangumiInfo.theme = "综艺"

    def get_bangumi_quality(self):
        bangumi_request = requests.get(self.quality_api(BangumiInfo.bvid, BangumiInfo.cid), headers = get_header(BangumiInfo.url, cookie = Config.user_sessdata), proxies = get_proxy())
        bangumi_json = json.loads(bangumi_request.text)
        
        if bangumi_json["code"] != 0:
            self.on_error(402)

        json_data = bangumi_json["result"]

        BangumiInfo.quality_id = json_data["accept_quality"]
        BangumiInfo.quality_desc = json_data["accept_description"]

    def parse_url(self, url: str, on_error):
        self.on_error = on_error

        if "ep" in url:
            self.get_epid(url)
        elif "ss" in url:
            self.get_season_id(url)
        elif "md" in url:
            self.get_media_id(url)
        
        self.get_bangumi_info()
        self.get_bangumi_quality()