from utils.config import Config
from utils.auth.wbi import WbiUtils
from utils.tool_v2 import UniversalTool

from utils.parse.parser import Parser
from utils.parse.audio import AudioInfo
from utils.parse.episode_v2 import Episode, EpisodeInfo
from utils.parse.interact_video import InteractVideoInfo, InteractVideoParser

from utils.common.enums import ParseType, VideoType, EpisodeDisplayType, StatusCode, StreamType
from utils.common.exception import GlobalException
from utils.common.data_type import ParseCallback
from utils.common.request import RequestUtils
from utils.common.formatter import FormatUtils

class VideoInfo:
    url: str = ""
    aid: str = ""
    bvid: str = ""
    cid: int = 0

    title: str = ""
    cover: str = ""
    views: str = ""
    danmakus: str = ""
    desc: str = ""
    tag_list: list = []
    type: int = 0

    stream_type: int = 0

    is_interactive: bool = False

    pages_list: list = []
    video_quality_id_list: list = []
    video_quality_desc_list: list = []

    pubtime: int = 0
    tname: str = ""
    subtname: str = ""
    up_name: str = ""
    up_mid: int = 0

    info_json: dict = {}
    download_json: dict = {}

    @classmethod
    def clear_video_info(cls):
        cls.url = ""
        cls.bvid = ""
        cls.aid = 0
        cls.bvid = ""
        cls.title = ""
        cls.cover = ""
        cls.desc = ""
        cls.views = 0
        cls.danmakus = 0
        cls.cid = 0
        cls.type = 0
        cls.stream_type = 0
        cls.pubtime = 0
        cls.tname = ""
        cls.subtname = ""
        cls.up_name = ""
        cls.up_mid = 0

        cls.is_interactive = False

        cls.tag_list.clear()
        cls.pages_list.clear()
        cls.video_quality_id_list.clear()
        cls.video_quality_desc_list.clear()

        cls.info_json.clear()
        cls.download_json.clear()

class VideoParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback
    
    def get_part(self, url: str):
        part = self.re_find_str(r"p=([0-9]+)", url, check = False)

        if part:
            self.part = True
            self.part_num = int(part[0])
        else:
            self.part = False

    def get_aid(self, url: str):
        aid = self.re_find_str(r"av([0-9]+)", url)

        bvid = self.aid_to_bvid(int(aid[0]))
        self.set_bvid(bvid)

    def get_bvid(self, url: str):
        bvid = self.re_find_str(r"BV\w+", url)

        self.set_bvid(bvid[0])

    def get_video_info(self):
        # 获取视频信息
        params = {
            "bvid": VideoInfo.bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = VideoInfo.url, sessdata = Config.User.SESSDATA))

        info = resp["data"]

        if "redirect_url" in info:
            raise GlobalException(code = StatusCode.Redirect.value, callback = self.callback.onBangumi, args = (info["redirect_url"], ))

        VideoInfo.title = info["title"]
        VideoInfo.cover = info["pic"]
        VideoInfo.aid = info["aid"]
        VideoInfo.pages_list = info["pages"]

        VideoInfo.desc = info["desc"]
        VideoInfo.views = FormatUtils.format_data_quantity(info["stat"]["view"])
        VideoInfo.danmakus = FormatUtils.format_data_quantity(info["stat"]["danmaku"])

        VideoInfo.pubtime = info["pubdate"]
        VideoInfo.tname = info["tname"]
        VideoInfo.subtname = info["tname_v2"]
        VideoInfo.up_name = info["owner"]["name"]
        VideoInfo.up_mid = info["owner"]["mid"]

        VideoInfo.is_interactive = "stein_guide_cid" in info

        # 当解析单个视频时，取 pages 中的 cid，使得清晰度和音质识别更加准确
        if Config.Misc.episode_display_mode == EpisodeDisplayType.Single.value:
            if hasattr(self, "part_num"):
                VideoInfo.cid = VideoInfo.pages_list[self.part_num - 1]["cid"]
            else:
                VideoInfo.cid = info["pages"][0]["cid"]
        else:
            VideoInfo.cid = info["cid"]

        VideoInfo.info_json = info.copy()

        # 判断是否为互动视频
        if VideoInfo.is_interactive:
            self.interact_video_parser = InteractVideoParser(self.callback.onUpdateInteractVideo)

            InteractVideoInfo.aid = VideoInfo.aid
            InteractVideoInfo.cid = VideoInfo.cid
            InteractVideoInfo.bvid = VideoInfo.bvid
            InteractVideoInfo.url = VideoInfo.url
            InteractVideoInfo.title = VideoInfo.title

            self.interact_video_parser.get_video_interactive_graph_version()

            self.callback.onInteractVideo()

        self.parse_episodes()

    def get_video_tag(self):
        url = f"https://api.bilibili.com/x/tag/archive/tags?bvid={VideoInfo.bvid}"
        
        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = VideoInfo.url, sessdata = Config.User.SESSDATA))

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
        
        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = VideoInfo.url, sessdata = Config.User.SESSDATA))

        info = VideoInfo.download_json = resp["data"]

        if "dash" in info:
            AudioInfo.get_audio_quality_list(info["dash"])

            VideoInfo.stream_type = StreamType.Dash.value
            
        elif "durl" in info:
            AudioInfo.get_audio_quality_list({})

            VideoInfo.stream_type = StreamType.Flv.value

        VideoInfo.video_quality_id_list = info["accept_quality"]
        VideoInfo.video_quality_desc_list = info["accept_description"]

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
        
        except Exception as e:
            raise GlobalException(callback = self.callback.onError) from e

    def set_bvid(self, bvid: str):
        VideoInfo.bvid, VideoInfo.url = bvid, f"https://www.bilibili.com/video/{bvid}"

    def parse_episodes(self):
        def interact_video_parser():
            def get_page():
                return {
                    "part": node.title,
                    "cid": node.cid
                }

            VideoInfo.info_json["pages"].clear()

            self.interact_video_parser.parse_interactive_video_episodes()

            for node in InteractVideoInfo.node_list:
                VideoInfo.info_json["pages"].append(get_page())

        if VideoInfo.is_interactive:
            interact_video_parser()
            
        Episode.Video.parse_episodes(VideoInfo.info_json, VideoInfo.cid)

    def clear_video_info(self):
        # 清除视频信息
        VideoInfo.clear_video_info()
        InteractVideoInfo.clear_video_info()

        # 重置音质信息
        AudioInfo.clear_audio_info()
