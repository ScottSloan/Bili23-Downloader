from utils.config import Config
from utils.auth.wbi import WbiUtils

from utils.parse.parser import Parser
from utils.parse.episode.video import Video
from utils.parse.interact_video import InteractVideoParser
from utils.parse.preview import PreviewInfo

from utils.common.enums import StatusCode, EpisodeDisplayType
from utils.common.exception import GlobalException
from utils.common.model.callback import ParseCallback
from utils.common.request import RequestUtils
from utils.common.regex import Regex

class VideoParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback
    
    def get_page(self, url: str):
        page = self.re_find_str(r"p=([0-9]+)", url, check = False)

        self.page = bool(page)
        self.page_num = int(page[0]) if page else None

    def get_aid(self, url: str):
        aid = self.re_find_str(r"av([0-9]+)", url)

        return self.aid_to_bvid(int(aid[0]))

    def get_bvid(self, url: str):
        bvid = self.re_find_str(r"BV\w+", url)

        return bvid[0]

    def get_video_info(self, bvid: str):
        # 获取视频信息
        params = {
            "bvid": bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        self.info_json: dict = resp["data"]

        if "redirect_url" in self.info_json:
            raise GlobalException(code = StatusCode.Redirect.value, callback = self.callback.onJump, args = (self.info_json["redirect_url"], ))

        self.is_interactive = "stein_guide_cid" in self.info_json

        # 判断是否为互动视频
        if self.is_interactive:
            self.parse_interact_video()
            
        if self.page:
            for page in self.info_json.get("pages"):
                if page.get("page") == self.page_num:
                    self.info_json["cid"] = page.get("cid")

        self.parse_episodes()

    @classmethod
    def get_video_available_media_info(cls, bvid: str, cid: int):
        # 获取视频清晰度
        params = {
            "bvid": bvid,
            "cid": cid,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1,
        }

        url = f"https://api.bilibili.com/x/player/wbi/playurl?{WbiUtils.encWbi(params)}"
        
        resp = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = cls.bilibili_url, sessdata = Config.User.SESSDATA))

        PreviewInfo.download_json = resp["data"].copy()

    @classmethod
    def get_video_extra_info(cls, bvid: str):
        params = {
            "bvid": bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{WbiUtils.encWbi(params)}"

        resp = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = cls.bilibili_url, sessdata = Config.User.SESSDATA))

        return {
            "cid": resp["data"]["cid"],
            "up_name": resp["data"]["owner"]["name"],
            "up_mid": resp["data"]["owner"]["mid"]
        }

    def parse_worker(self, url: str):
        self.get_page(url)

        match Regex.find_string(r"av|BV", url):
            case "av":
                self.bvid = self.get_aid(url)

            case "BV":
                self.bvid = self.get_bvid(url)

        self.get_video_info(self.bvid)

        self.get_video_available_media_info(self.info_json.get("bvid"), self.info_json.get("cid"))

        return StatusCode.Success.value

    def parse_episodes(self):
        Video.parse_episodes(self.info_json)

    def parse_interact_video(self):
        Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

        self.interact_video_parser = InteractVideoParser(self.callback)
        self.interact_video_parser.get_video_interactive_graph_version(self.info_json)

        self.info_json["node_list"] = self.interact_video_parser.parse_interactive_video_episodes()

    def get_parse_type_str(self):
        if self.is_interactive:
            return "互动视频"
        else:
            return "投稿视频"
    
    def get_interact_title(self):
        return self.info_json.get("title")
    
    def is_in_section_option_enable(self):
        return "ugc_season" in self.info_json

    def is_interactive_video(self):
        return self.is_interactive