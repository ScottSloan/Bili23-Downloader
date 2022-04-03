import os
import requests

from utils.video import VideoInfo
from utils.bangumi import BangumiInfo
from utils.tools import *
from utils.config import Config

def save_cover(url: str):
    cover_request = requests.get(url, headers = get_header(), proxies = get_proxy())
    Config._info_cover = "cover.png" if url.endswith("png") else "cover.jpg"

    with open(os.path.join(Config._info_base_path, Config._info_cover), "wb") as f:
        f.write(cover_request.content)

def save_video_info():
    save_cover(VideoInfo.cover)

    page = read_file(Config._info_video_path)
    oldstr = ["{ title }", "{ desc }", "{ cover }", "{ view }", "{ like }", "{ coin }", "{ danmaku }", "{ favorite }", "{ reply }"]
    newstr = [VideoInfo.title, VideoInfo.desc, Config._info_cover, VideoInfo.view, VideoInfo.like, VideoInfo.coin, VideoInfo.danmaku, VideoInfo.favorite, VideoInfo.reply]
    page = replace_template(page, oldstr, newstr)

    save_to_file(Config._info_html, page)

def save_bangumi_info():
    save_cover(BangumiInfo.cover)

    page = read_file(Config._info_bangumi_path)
    oldstr = ["{ title }", "{ cover }", "{ desc }", "{ theme }", "{ view }", "{ coin }", "{ danmaku }", "{ favorite }", "{ newep }", "{ bvid }", "{ score }", "{ count }"]
    newstr = [BangumiInfo.title, Config._info_cover, BangumiInfo.desc, BangumiInfo.theme, BangumiInfo.view, BangumiInfo.coin, BangumiInfo.danmaku, BangumiInfo.favorite, BangumiInfo.newep, BangumiInfo.bvid, BangumiInfo.score, BangumiInfo.count]
    page = replace_template(page, oldstr, newstr)

    save_to_file(Config._info_html, page)

def read_file(path: str) -> str:
    with open(path, "r" , encoding = "utf-8") as f:
        return(f.read())

def save_to_file(path: str, text: str):
    with open(path, "w", encoding = "utf-8") as f:
        f.write(text)
        
def replace_template(string: str, oldstr: list, newstr: list) -> str:
    p_str = string
    for old, new in zip(oldstr, newstr):
        p_str = p_str.replace(old, str(new))
    return p_str