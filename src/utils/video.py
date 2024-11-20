import re
import json
import requests
from typing import List, Dict

from utils.config import Config, Audio
from utils.tools import get_header, get_auth, get_proxy, convert_to_bvid, find_str
from utils.error import process_exception, ParseError, ErrorUtils, URLError, ErrorCallback, StatusCode

class VideoInfo:
    url: str = ""
    aid: str = ""
    bvid: str = ""
    cid: int = 0

    title: str = ""
    cover: str = ""
    type: int = 0

    pages_list: List = []
    episodes_list: List = []
    video_quality_id_list: List = []
    video_quality_desc_list: List = []

    sections: Dict = {}

class VideoParser:
    def __init__(self):
        self.continue_to_parse = True
    
    def get_part(self, url: str):
        part = re.findall(r"p=([0-9]+)", url)

        if part:
            self.part = True
            self.part_num = int(part[0])
        else:
            self.part = False

    @process_exception
    def get_aid(self, url: str):
        aid = re.findall(r"av([0-9]+)", url)

        if not aid:
            raise URLError()

        bvid = convert_to_bvid(int(aid[0]))
        self.set_bvid(bvid)

    @process_exception
    def get_bvid(self, url: str):
        bvid = re.findall(r"BV\w+", url)

        if not bvid:
            raise URLError()

        self.set_bvid(bvid[0])

    @process_exception
    def get_video_info(self):
        # 获取视频信息
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={VideoInfo.bvid}"
        
        req = requests.get(url, headers = get_header(referer_url = VideoInfo.url, cookie = Config.User.sessdata), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        if "redirect_url" in info:
            # 存在跳转链接，重新跳转解析，抛出异常仅为停止线程
            ErrorCallback.onRedirect(info["redirect_url"])
            self.continue_to_parse = False

            return

        VideoInfo.title = info["title"]
        VideoInfo.cover = info["pic"]
        VideoInfo.aid = info["aid"]
        VideoInfo.pages_list = info["pages"]

        # 当解析单个视频时，取 pages 中的 cid，使得清晰度和音质识别更加准确
        if Config.Misc.episode_display_mode == Config.Type.EPISODES_SINGLE:
            if hasattr(self, "part_num"):
                VideoInfo.cid = VideoInfo.pages_list[self.part_num - 1]["cid"]
            else:
                VideoInfo.cid = info["pages"][0]["cid"]
        else:
            VideoInfo.cid = info["cid"]

        match Config.Misc.episode_display_mode:
            case Config.Type.EPISODES_SINGLE:
                # 解析单个视频
                self.parse_pages()

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

    @process_exception
    def get_video_available_media_info(self):
        # 获取视频清晰度
        url = f"https://api.bilibili.com/x/player/playurl?bvid={VideoInfo.bvid}&cid={VideoInfo.cid}&qn=0&fnver=0&fnval=4048&fourk=1"
                
        req = requests.get(url, headers = get_header(referer_url = VideoInfo.url, cookie = Config.User.sessdata), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        VideoInfo.video_quality_id_list = info["accept_quality"]
        VideoInfo.video_quality_desc_list = info["accept_description"]

        with open("video.json", "w", encoding = "utf-8") as f:
            f.write(req.text)

        # 检测无损或杜比是否存在
        if "flac" in info["dash"]:
            if info["dash"]["flac"]:
                Audio.q_hires = True

        if "dolby" in info["dash"]:
            if "audio" in info["dash"]["dolby"]:
                if info["dash"]["dolby"]["audio"]:
                    Audio.q_dolby = True

        # 检测 192k, 132k, 64k 音质是否存在
        if "audio" in info["dash"]:
            if info["dash"]["audio"]:
                for entry in info["dash"]["audio"]:
                    match entry["id"]:
                        case 30280:
                            Audio.q_192k = True

                        case 30232:
                            Audio.q_132k = True

                        case 30216:
                            Audio.q_64k = True

            Audio.audio_quality_id = Config.Download.audio_quality_id

    def parse_url(self, url: str):
        # 先检查是否为分 P 视频
        self.get_part(url)

        # 清除当前的视频信息
        self.clear_video_info()

        self.continue_to_parse = True

        match find_str(r"av|BV", url):
            case "av":
                self.get_aid(url)

            case "BV":
                self.get_bvid(url)

        self.get_video_info()

        if self.continue_to_parse:
            self.get_video_available_media_info()

        return self.continue_to_parse

    def set_bvid(self, bvid: str):
        VideoInfo.bvid, VideoInfo.url = bvid, f"https://www.bilibili.com/video/{bvid}"

    def check_json(self, json: Dict):
        # 检查接口返回状态码
        status_code = json["code"]
        error = ErrorUtils()

        if status_code != StatusCode.CODE_0:
            # 如果请求失败，则抛出 ParseError 异常，由 process_exception 进一步处理
            raise ParseError(error.getStatusInfo(status_code), status_code)

    def parse_pages(self):
        # 判断是否为分P视频
        if len(VideoInfo.pages_list) == 1:
            # 单个视频
            VideoInfo.type = Config.Type.VIDEO_TYPE_SINGLE

        else:
            # 分P视频
            VideoInfo.type = Config.Type.VIDEO_TYPE_PAGES

        if Config.Misc.episode_display_mode == Config.Type.EPISODES_SINGLE:
            if hasattr(self, "part_num"):
                VideoInfo.pages_list = [VideoInfo.pages_list[self.part_num - 1]]
            else:
                VideoInfo.pages_list = [VideoInfo.pages_list[0]]
            
    def clear_video_info(self):
        # 清除当前的视频信息
        VideoInfo.url = VideoInfo.aid = VideoInfo.bvid = VideoInfo.title = VideoInfo.cover = ""
        VideoInfo.cid = VideoInfo.type = 0

        VideoInfo.pages_list.clear()
        VideoInfo.episodes_list.clear()
        VideoInfo.video_quality_id_list.clear()
        VideoInfo.video_quality_desc_list.clear()

        VideoInfo.sections.clear()

        # 重置音质信息
        Audio.q_hires = Audio.q_dolby = Audio.q_192k = Audio.q_132k = Audio.q_64k = Audio.audio_only = False
        Audio.audio_quality_id = 0