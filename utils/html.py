import os
import sys
import requests

from utils.video import VideoInfo
from utils.bangumi import BangumiInfo
from utils.tools import *
from utils.config import Config

class HTMLUtils:
    def save_cover(self, url: str):
        cover_request = requests.get(url, headers = get_header(), proxies = get_proxy())
        self.cover = "cover.png" if url.endswith("png") else "cover.jpg"

        with open(self.get_resource_path(os.path.join("info", self.cover)), "wb") as f:
            f.write(cover_request.content)

    def save_video_info(self):
        self.save_cover(VideoInfo.cover)

        page = self.read_file(Config.res_info_video)
        oldstr = ["{ title }", "{ desc }", "{ cover }", "{ view }", "{ like }", "{ coin }", "{ danmaku }", "{ favorite }", "{ reply }"]
        newstr = [VideoInfo.title, VideoInfo.desc, self.cover, VideoInfo.view, VideoInfo.like, VideoInfo.coin, VideoInfo.danmaku, VideoInfo.favorite, VideoInfo.reply]
        page = self.replace_template(page, oldstr, newstr)

        self.save_to_file(Config.res_info, page)

    def save_bangumi_info(self):
        self.save_cover(BangumiInfo.cover)

        page = self.read_file(Config.res_info_bangumi)
        oldstr = ["{ title }", "{ cover }", "{ desc }", "{ theme }", "{ view }", "{ coin }", "{ danmaku }", "{ favorite }", "{ newep }", "{ bvid }", "{ score }", "{ count }"]
        newstr = [BangumiInfo.title, self.cover, BangumiInfo.desc, BangumiInfo.theme, BangumiInfo.view, BangumiInfo.coin, BangumiInfo.danmaku, BangumiInfo.favorite, BangumiInfo.newep, BangumiInfo.bvid, BangumiInfo.score, BangumiInfo.count]
        page = self.replace_template(page, oldstr, newstr)

        self.save_to_file(Config.res_info, page)

    def read_file(self, path: str) -> str:
        with open(path, "r" , encoding = "utf-8") as f:
            return(f.read())

    def save_to_file(self, path: str, text: str):
        with open(path, "w", encoding = "utf-8") as f:
            f.write(text)
            
    def replace_template(self, string: str, oldstr: list, newstr: list) -> str:
        p_str = string
        for old, new in zip(oldstr, newstr):
            p_str = p_str.replace(old, str(new))
        return p_str
    
    def get_resource_path(self, relative_path: str):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.getcwd(), relative_path)