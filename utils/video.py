import re
import json
import requests
from utils.config import Config

from utils.tools import *
from utils.error import ProcessError

class VideoInfo:
    url = bvid = cid = ""

    title = desc = cover = ""

    view = like = coin = danmaku = favorite = reply = quality = duration = 0

    pages = episodes = down_pages = quality_id = quality_desc = []

    multiple = collection = False

class VideoParser:
    def aid_api(self, aid: str) -> str:
        return "https://api.bilibili.com/x/web-interface/archive/stat?aid={}".format(aid)

    def info_api(self) -> str:
        return "https://api.bilibili.com/x/web-interface/view?bvid={}".format(VideoInfo.bvid)

    def quality_api(self, cid: int) -> str:
        return "https://api.bilibili.com/x/player/playurl?bvid={}&cid={}&qn=0&fnver=0&fnval=4048&fourk=1".format(VideoInfo.bvid, cid)

    def get_aid(self, url: str):
        aid = re.findall(r"av[0-9]*", url)[0][2:]
        aid_request = requests.get(self.aid_api(aid), headers = get_header(), proxies = get_proxy())
        aid_json = json.loads(aid_request.text)

        if aid_json["code"] != 0:
            self.on_error(400)

        bvid = aid_json["data"]["bvid"]
        self.set_bvid(bvid)

    def get_bvid(self, url: str):
        bvid = re.findall(r"BV\w*", url)[0]
        self.set_bvid(bvid)

    def set_bvid(self, bvid: str):
        VideoInfo.bvid, VideoInfo.url = bvid, "https://www.bilibili.com/video/" + bvid

    def get_video_info(self):
        info_request = requests.get(self.info_api(), headers = get_header(VideoInfo.url, cookie = Config.cookie_sessdata), proxies = get_proxy())
        info_json = json.loads(info_request.text)

        if info_json["code"] != 0:
            self.on_error(400)

        info_data = info_json["data"]

        if "redirect_url" in info_data:
            self.on_redirect(info_data["redirect_url"])
            raise ProcessError("Bangumi type detect")
        
        VideoInfo.title = info_data["title"]
        VideoInfo.desc = info_data["desc"] if info_data["desc"] != "-" else "暂无简介"
        VideoInfo.cover = info_data["pic"]
        VideoInfo.duration = info_data["duration"]
        VideoInfo.pages = info_data["pages"]

        if "ugc_season" in info_data:
            VideoInfo.collection = True

            info_ugc_season = info_data["ugc_season"]
            VideoInfo.title = info_ugc_season["title"]

            VideoInfo.episodes = info_ugc_season["sections"][0]["episodes"]

        VideoInfo.cid = info_data["cid"]

        info_stat = info_data["stat"]
        VideoInfo.view = format_data(info_stat["view"])
        VideoInfo.like = format_data(info_stat["like"])
        VideoInfo.coin = format_data(info_stat["coin"])
        VideoInfo.danmaku = format_data(info_stat["danmaku"])
        VideoInfo.favorite = format_data(info_stat["favorite"])
        VideoInfo.reply = format_data(info_stat["reply"])
        
    def get_video_quality(self):
        video_request = requests.get(self.quality_api(VideoInfo.cid), headers = get_header(VideoInfo.url, Config.cookie_sessdata), proxies = get_proxy())
        video_json = json.loads(video_request.text)

        if video_json["code"] != 0:
            self.on_error(402)

        json_data = video_json["data"]

        VideoInfo.quality_id = json_data["accept_quality"]
        VideoInfo.quality_desc = json_data["accept_description"]

    def parse_url(self, url: str, on_redirect, on_error):
        self.on_redirect, self.on_error = on_redirect, on_error

        if "av" in url:
            self.get_aid(url)
        elif "BV" in url:
            self.get_bvid(url)
        
        self.get_video_info()
        self.get_video_quality()

    def get_full_url(self, bvid: str):
        return "https://www.bilibili.com/video/" + bvid
