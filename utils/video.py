import re
import requests
import json

from .tools import *
from .config import Config
from .api import API

class VideoInfo:
    url = bvid = title = cover = type = ""

    aid = cid = quality = duration = 0

    pages = down_pages = episodes = quality_id = quality_desc = []
    
    sections = {}

class VideoParser:
    def __init__(self, onError, onRedirect):
        self.onError = onError
        self.onRedirect = onRedirect

    def get_aid(self, url):
        try:
            VideoInfo.aid = re.findall(r"av([0-9]*)", url)[0]
        except:
            self.onError(400)
            return
        
        url = API.Video.aid_url_api(VideoInfo.aid)

        aid_request = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        aid_json = json.loads(aid_request.text)

        if self.check_json(aid_json): return

        bvid = aid_json["data"]["bvid"]
        self.set_bvid(bvid)

    def get_bvid(self, url):
        bvid = re.findall(r"BV\w*", url)[0]
        self.set_bvid(bvid)

    def set_bvid(self, bvid):
        VideoInfo.bvid, VideoInfo.url = bvid, API.URL.bvid_url_api(bvid)

    def get_video_info(self):
        url = API.Video.info_api(VideoInfo.bvid)
        
        info_request = requests.get(url, headers = get_header(VideoInfo.url, cookie = Config.user_sessdata), proxies = get_proxy(), auth = get_auth())
        info_json = json.loads(info_request.text)

        if self.check_json(info_json): return

        info_data = info_json["data"]

        if "redirect_url" in info_data:
            self.onRedirect(info_data["redirect_url"])
            return
        
        VideoInfo.title = info_data["title"]
        VideoInfo.cover = info_data["pic"]
        VideoInfo.duration = info_data["duration"]
        VideoInfo.aid = info_data["aid"]
        VideoInfo.cid = info_data["cid"]
        VideoInfo.pages = info_data["pages"]

        VideoInfo.type = "pages" if len(VideoInfo.pages) > 1 else "video"
        
        if "ugc_season" in info_data:
            VideoInfo.type = "collection"

            info_ugc_season = info_data["ugc_season"]
            info_section = info_ugc_season["sections"]
            
            VideoInfo.title = info_ugc_season["title"]

            VideoInfo.episodes = info_section[0]["episodes"]
            VideoInfo.sections["正片"] = VideoInfo.episodes
            
            if Config.show_sections:
                for section in info_section:
                    section_title = section["title"]
                    section_episodes = section["episodes"]

                    for index, value in enumerate(section_episodes):
                        value["title"] = str(index + 1)

                        VideoInfo.sections[section_title] = section_episodes

    def get_video_quality(self):
        url = API.Video.download_api(VideoInfo.bvid, VideoInfo.cid)
                
        video_request = requests.get(url, headers = get_header(cookie = Config.user_sessdata), proxies = get_proxy(), auth = get_auth())
        video_json = json.loads(video_request.text)

        if self.check_json(video_json): return

        json_data = video_json["data"]

        VideoInfo.quality_id = json_data["accept_quality"]
        VideoInfo.quality_desc = json_data["accept_description"]

    def parse_url(self, url):
        if "av" in url:
            self.get_aid(url)
        else:
            self.get_bvid(url)
        
        self.get_video_info()
        self.get_video_quality()
    
    def check_json(self, json):
        if json["code"] != 0:
            self.onError(400)
            return True
