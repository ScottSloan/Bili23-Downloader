import re
import json
import requests

from utils.config import Config
from utils.tool_v2 import RequestTool, UniversalTool, FormatTool
from utils.error import process_exception, ParseError, ErrorUtils, URLError, ErrorCallback, StatusCode
from utils.parse.audio import AudioInfo
from utils.parse.extra import ExtraInfo
from utils.parse.episode import EpisodeInfo, video_ugc_season_parser

class VideoInfo:
    url: str = ""
    aid: str = ""
    bvid: str = ""
    cid: int = 0

    title: str = ""
    cover: str = ""
    type: int = 0

    pages_list: list = []
    video_quality_id_list: list = []
    video_quality_desc_list: list = []

    info_json: dict = {}

    @staticmethod
    def clear_video_info():
        VideoInfo.url = VideoInfo.aid = VideoInfo.bvid = VideoInfo.title = VideoInfo.cover = ""
        VideoInfo.cid = VideoInfo.type = Config.Type.UNDEFINED

        VideoInfo.pages_list.clear()
        VideoInfo.video_quality_id_list.clear()
        VideoInfo.video_quality_desc_list.clear()

        VideoInfo.info_json.clear()

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

        bvid = UniversalTool.aid_to_bvid(int(aid[0]))
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
        
        req = requests.get(url, headers = RequestTool.get_headers(referer_url = VideoInfo.url, sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)

        with open("video.json", "w", encoding = "utf-8") as f:
            f.write(req.text)

        info = VideoInfo.info_json = resp["data"]

        if "redirect_url" in info:
            # 存在跳转链接
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

        self.parse_episodes()

    @process_exception
    def get_video_available_media_info(self):
        # 获取视频清晰度
        url = f"https://api.bilibili.com/x/player/playurl?bvid={VideoInfo.bvid}&cid={VideoInfo.cid}&qn=0&fnver=0&fnval=4048&fourk=1"
                
        req = requests.get(url, headers = RequestTool.get_headers(referer_url = VideoInfo.url, sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        VideoInfo.video_quality_id_list = info["accept_quality"]
        VideoInfo.video_quality_desc_list = info["accept_description"]

        AudioInfo.get_audio_quality_list(info["dash"])

        ExtraInfo.get_danmaku = Config.Extra.get_danmaku
        ExtraInfo.danmaku_type = Config.Extra.danmaku_type
        ExtraInfo.get_subtitle = Config.Extra.get_subtitle
        ExtraInfo.subtitle_type = Config.Extra.subtitle_type
        ExtraInfo.get_cover = Config.Extra.get_cover

    def parse_url(self, url: str):
        # 先检查是否为分 P 视频
        self.get_part(url)

        # 清除当前的视频信息
        self.clear_video_info()

        self.continue_to_parse = True

        match UniversalTool.re_find_string(r"av|BV", url):
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

    def check_json(self, json: dict):
        # 检查接口返回状态码
        status_code = json["code"]
        error = ErrorUtils()

        if status_code != StatusCode.CODE_0:
            # 如果请求失败，则抛出 ParseError 异常，由 process_exception 进一步处理
            raise ParseError(error.getStatusInfo(status_code), status_code)
    
    def parse_episodes(self):
        def pages_parser():
            if len(VideoInfo.pages_list) == 1:
                VideoInfo.type = Config.Type.VIDEO_TYPE_SINGLE
            else:
                VideoInfo.type = Config.Type.VIDEO_TYPE_PAGES

            for page in VideoInfo.pages_list:
                if Config.Misc.episode_display_mode == Config.Type.EPISODES_SINGLE:
                    if page["cid"] != VideoInfo.cid:
                        continue

                EpisodeInfo.cid_dict[page["cid"]] = page

                EpisodeInfo.add_item(EpisodeInfo.data, "视频", {
                    "title": page["part"],
                    "cid": page["cid"],
                    "badge": "",
                    "duration": FormatTool.format_duration(page, Config.Type.VIDEO)
                })

        EpisodeInfo.clear_episode_data()

        match Config.Misc.episode_display_mode:
            case Config.Type.EPISODES_SINGLE:
                pages_parser()

            case Config.Type.EPISODES_IN_SECTION | Config.Type.EPISODES_ALL_SECTIONS:
                if "ugc_season" in VideoInfo.info_json:
                    VideoInfo.type = Config.Type.VIDEO_TYPE_SECTIONS

                    video_ugc_season_parser(VideoInfo.info_json, VideoInfo.cid)
                else:
                    pages_parser()

    def clear_video_info(self):
        # 清除视频信息
        VideoInfo.clear_video_info()

        # 重置音质信息
        AudioInfo.clear_audio_info()

        # 重置附加内容信息
        ExtraInfo.clear_extra_info()
