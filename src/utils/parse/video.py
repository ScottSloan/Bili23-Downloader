import re
import json

from utils.config import Config
from utils.tool_v2 import RequestTool, UniversalTool, FormatTool
from utils.parse.audio import AudioInfo
from utils.parse.extra import ExtraInfo
from utils.parse.episode import EpisodeInfo, video_ugc_season_parser
from utils.auth.wbi import WbiUtils
from utils.common.enums import ParseType, VideoType, EpisodeDisplayType, StatusCode, StreamType
from utils.common.exception import GlobalException
from utils.common.data_type import ParseCallback

class VideoInfo:
    url: str = ""
    aid: str = ""
    bvid: str = ""
    cid: int = 0

    title: str = ""
    cover: str = ""
    views: str = ""
    danmakus: str = ""
    pubtime: str = ""
    desc: str = ""
    tag_list: list = []
    type: int = 0

    stream_type: int = 0

    pages_list: list = []
    video_quality_id_list: list = []
    video_quality_desc_list: list = []

    info_json: dict = {}

    @staticmethod
    def clear_video_info():
        VideoInfo.url = VideoInfo.aid = VideoInfo.bvid = VideoInfo.title = VideoInfo.cover = VideoInfo.desc = VideoInfo.views = VideoInfo.danmakus = VideoInfo.pubtime = ""
        VideoInfo.cid = VideoInfo.type = VideoInfo.stream_type = 0

        VideoInfo.tag_list.clear()
        VideoInfo.pages_list.clear()
        VideoInfo.video_quality_id_list.clear()
        VideoInfo.video_quality_desc_list.clear()

        VideoInfo.info_json.clear()

class VideoParser:
    def __init__(self, callback: ParseCallback):
        self.callback = callback
    
    def get_part(self, url: str):
        part = re.findall(r"p=([0-9]+)", url)

        if part:
            self.part = True
            self.part_num = int(part[0])
        else:
            self.part = False

    def get_aid(self, url: str):
        aid = re.findall(r"av([0-9]+)", url)

        if not aid:
            raise Exception(StatusCode.URL.value)

        bvid = UniversalTool.aid_to_bvid(int(aid[0]))
        self.set_bvid(bvid)

    def get_bvid(self, url: str):
        bvid = re.findall(r"BV\w+", url)

        if not bvid:
            raise Exception(StatusCode.URL.value)

        self.set_bvid(bvid[0])

    def get_video_info(self):
        # 获取视频信息
        params = {
            "bvid": VideoInfo.bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{WbiUtils.encWbi(params)}"
        
        req = RequestTool.request_get(url, headers = RequestTool.get_headers(referer_url = VideoInfo.url, sessdata = Config.User.sessdata))
        resp = json.loads(req.text)

        self.check_json(resp)

        info = VideoInfo.info_json = resp["data"]

        if "redirect_url" in info:
            raise GlobalException(StatusCode.Redirect.value, callback = self.callback.redirect_callback, url = info["redirect_url"])

        VideoInfo.title = info["title"]
        VideoInfo.cover = info["pic"]
        VideoInfo.aid = info["aid"]
        VideoInfo.pages_list = info["pages"]

        VideoInfo.desc = info["desc"]
        VideoInfo.views = FormatTool.format_data_count(info["stat"]["view"])
        VideoInfo.danmakus = FormatTool.format_data_count(info["stat"]["danmaku"])
        VideoInfo.pubtime = UniversalTool.get_time_str_from_timestamp(info["pubdate"])

        # 当解析单个视频时，取 pages 中的 cid，使得清晰度和音质识别更加准确
        if Config.Misc.episode_display_mode == EpisodeDisplayType.Single.value:
            if hasattr(self, "part_num"):
                VideoInfo.cid = VideoInfo.pages_list[self.part_num - 1]["cid"]
            else:
                VideoInfo.cid = info["pages"][0]["cid"]
        else:
            VideoInfo.cid = info["cid"]

        self.get_video_tag()

        self.parse_episodes()

    def get_video_tag(self):
        url = f"https://api.bilibili.com/x/tag/archive/tags?bvid={VideoInfo.bvid}"
        
        req = RequestTool.request_get(url, headers = RequestTool.get_headers(referer_url = VideoInfo.url, sessdata = Config.User.sessdata))
        resp = json.loads(req.text)

        VideoInfo.tag_list = [entry["tag_name"] for entry in resp["data"]]

    def get_video_available_media_info(self):
        # 获取视频清晰度
        params = {
            "bvid": VideoInfo.bvid,
            "cid": VideoInfo.cid,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1
        }

        url = f"https://api.bilibili.com/x/player/wbi/playurl?{WbiUtils.encWbi(params)}"
        
        req = RequestTool.request_get(url, headers = RequestTool.get_headers(referer_url = VideoInfo.url, sessdata = Config.User.sessdata))
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        if "dash" in info:
            AudioInfo.get_audio_quality_list(info["dash"])

            VideoInfo.stream_type = StreamType.Dash.value
        else:
            AudioInfo.get_audio_quality_list({})

            VideoInfo.stream_type = StreamType.Flv.value

        VideoInfo.video_quality_id_list = info["accept_quality"]
        VideoInfo.video_quality_desc_list = info["accept_description"]

        ExtraInfo.get_danmaku = Config.Extra.get_danmaku
        ExtraInfo.danmaku_type = Config.Extra.danmaku_type
        ExtraInfo.get_subtitle = Config.Extra.get_subtitle
        ExtraInfo.subtitle_type = Config.Extra.subtitle_type
        ExtraInfo.get_cover = Config.Extra.get_cover

    def parse_url(self, url: str):
        def worker():
            # 先检查是否为分 P 视频
            self.get_part(url)

            # 清除当前的视频信息
            self.clear_video_info()

            match UniversalTool.re_find_string(r"av|BV", url):
                case "av":
                    self.get_aid(url)

                case "BV":
                    self.get_bvid(url)

            self.get_video_info()
            
            self.get_video_available_media_info()

            return StatusCode.Success.value
        
        try:
            return worker()
        
        except GlobalException as e:
            raise e

        except Exception as e:
            raise GlobalException(e, callback = self.callback.error_callback) from e

    def set_bvid(self, bvid: str):
        VideoInfo.bvid, VideoInfo.url = bvid, f"https://www.bilibili.com/video/{bvid}"

    def check_json(self, json: dict):
        # 检查接口返回状态码
        status_code = json["code"]

        if status_code != StatusCode.Success.value:
            raise Exception(status_code)
    
    def parse_episodes(self):
        def pages_parser():
            if len(VideoInfo.pages_list) == 1:
                VideoInfo.type = VideoType.Single
            else:
                VideoInfo.type = VideoType.Part

            for page in VideoInfo.pages_list:
                if Config.Misc.episode_display_mode == EpisodeDisplayType.Single.value:
                    if page["cid"] != VideoInfo.cid:
                        continue

                EpisodeInfo.cid_dict[page["cid"]] = page

                EpisodeInfo.add_item(EpisodeInfo.data, "视频", {
                    "title": page["part"] if VideoInfo.type == VideoType.Part else VideoInfo.title,
                    "cid": page["cid"],
                    "badge": "",
                    "duration": FormatTool.format_duration(page, ParseType.Video)
                })

        EpisodeInfo.clear_episode_data()

        match EpisodeDisplayType(Config.Misc.episode_display_mode):
            case EpisodeDisplayType.Single:
                pages_parser()

            case EpisodeDisplayType.In_Section | EpisodeDisplayType.All:
                if "ugc_season" in VideoInfo.info_json:
                    VideoInfo.type = VideoType.Collection

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
