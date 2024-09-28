import re
import json
import requests

from utils.config import Config, Audio
from utils.tools import *

class VideoInfo:
    url = aid = bvid = cid = None

    title = cover = duration = type = resolution = None

    pages = episodes = resolution_id = resolution_desc = []

    sections = {}

class VideoParser:
    def __init__(self, onError):
        self.onError = onError
    
    def get_part(self, url):
        part = re.findall(r"p=([0-9]+)", url)

        if part:
            self.part = True
            self.part_num = int(part[0])
        else:
            self.part = False
            
    def get_aid(self, url):
        aid = re.findall(r"av([0-9]+)", url)

        if not aid: self.onError(101)

        bvid = convert_to_bvid(int(aid[0]))
        self.save_bvid(bvid)

    def get_bvid(self, url):
        bvid = re.findall(r"BV\w+", url)

        if not bvid: self.onError(101)

        self.save_bvid(bvid[0])

    def get_video_info(self):
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={VideoInfo.bvid}"
        
        req = requests.get(url, headers = get_header(VideoInfo.url, cookie = Config.User.sessdata), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp, 101)

        info = resp["data"]

        VideoInfo.title = info["title"]
        VideoInfo.cover = info["pic"]
        VideoInfo.duration = info["duration"]
        VideoInfo.aid = info["aid"]
        VideoInfo.cid = info["cid"]
        VideoInfo.pages = info["pages"]

        VideoInfo.sections.clear()

        match Config.Misc.show_episodes:
            case Config.Type.EPISODES_SINGLE:
                # 解析单个视频

                if len(VideoInfo.pages) == 1:
                    # 单个视频
                    VideoInfo.type = Config.Type.VIDEO_TYPE_SINGLE
                else:
                    # 分P视频
                    VideoInfo.type = Config.Type.VIDEO_TYPE_PAGES

                    if hasattr(self, "part_num"):
                        VideoInfo.pages = [VideoInfo.pages[self.part_num - 1]]
                    else:
                        VideoInfo.pages = [VideoInfo.pages[0]]

            case Config.Type.EPISODES_IN_SECTION:
                # 解析视频所在合集

                if "ugc_season" in info:
                    # 判断是否为合集视频，若是则设置类型为合集
                    VideoInfo.type = Config.Type.VIDEO_TYPE_SECTIONS

                    info_section = info["ugc_season"]["sections"]

                    for section_entry in info_section:
                        section_title = section_entry["title"]
                        info_episodes = section_entry["episodes"]

                        for episode_entry in info_episodes:
                            if episode_entry["bvid"] == VideoInfo.bvid:
                                # 解析此部分内容
                                for index, value in enumerate(info_episodes):
                                    value["title"] = str(index + 1)
                                    break

                                VideoInfo.sections[section_title] = info_episodes
                else:
                    # 非合集视频，判断是否为分P视频
                    self.parse_pages()

            case Config.Type.EPISODES_ALL_SECTIONS:
                # 解析全部相关视频
    
                if "ugc_season" in info:
                    # 判断是否为合集视频，若是则设置类型为合集
                    VideoInfo.type = Config.Type.VIDEO_TYPE_SECTIONS

                    info_ugc_season = info["ugc_season"]
                    info_section = info_ugc_season["sections"]
                    
                    VideoInfo.title = info_ugc_season["title"]
                    
                    for section in info_section:
                        section_title = section["title"]
                        section_episodes = section["episodes"]

                        for index, value in enumerate(section_episodes):
                            value["title"] = str(index + 1)

                            VideoInfo.sections[section_title] = section_episodes
                else:
                    # 非合集视频，判断是否为分P视频
                    self.parse_pages()

    def get_video_resolution(self):
        url = f"https://api.bilibili.com/x/player/playurl?bvid={VideoInfo.bvid}&cid={VideoInfo.cid}&qn=0&fnver=0&fnval=4048&fourk=1"
                
        req = requests.get(url, headers = get_header(referer_url = VideoInfo.url, cookie = Config.User.sessdata), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp, 102)

        info = resp["data"]

        VideoInfo.resolution_id = info["accept_quality"]
        VideoInfo.resolution_desc = info["accept_description"]

        Audio.q_hires = True if info["dash"]["flac"] else False
        Audio.q_dolby = True if info["dash"]["dolby"]["audio"] else False

        # 存在无损或杜比
        if Audio.q_hires or Audio.q_dolby:
            # 如果选择下载无损或杜比
            if Config.Download.sound_quality == 30250:
                Audio.audio_quality = 30250
            else:
                Audio.audio_quality = Config.Download.sound_quality

        # 否则根据实际所选音质下载
        else:
            Audio.audio_quality = Config.Download.sound_quality

        # 重置仅下载音频标识符
        Audio.audio_only = False

    def parse_url(self, url):
        self.get_part(url)

        if "av" in url:
            self.get_aid(url)
        else:
            self.get_bvid(url)

        self.get_video_info()

        self.get_video_resolution()

    def save_bvid(self, bvid):
        VideoInfo.bvid, VideoInfo.url = bvid, f"https://www.bilibili.com/video/{bvid}"

    def check_json(self, json, err_code):
        if json["code"] != 0:
            self.onError(err_code)

    def parse_pages(self):
        # 判断是否为分P视频
        if len(VideoInfo.pages) == 1:
            # 单个视频
            VideoInfo.type = Config.Type.VIDEO_TYPE_SINGLE
        else:
            # 分P视频
            VideoInfo.type = Config.Type.VIDEO_TYPE_PAGES