from utils.config import Config

from utils.common.exception import GlobalException
from utils.common.map import bangumi_type_map
from utils.common.enums import StatusCode
from utils.common.model.callback import ParseCallback
from utils.common.request import RequestUtils
from utils.common.regex import Regex

from utils.parse.episode.episode_v2 import Episode
from utils.parse.episode.bangumi import Bangumi
from utils.parse.parser import Parser
from utils.parse.preview import PreviewInfo

class BangumiParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback
    
    def get_epid(self, url: str):
        epid = self.re_find_str(r"ep([0-9]+)", url)

        self.ep_id = int(epid[0])

        return f"ep_id={epid[0]}"

    def get_season_id(self, url: str):
        season_id = self.re_find_str(r"ss([0-9]+)", url)

        return f"season_id={season_id[0]}"

    def get_mid(self, url: str):
        mid = self.re_find_str(r"md([0-9]*)", url)

        params = {
            "media_id": mid[0]
        }

        url = f"https://api.bilibili.com/pgc/review/user?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        data = self.json_get(resp, "result")

        season_id = data["media"]["season_id"]

        return f"season_id={season_id}"

    def get_bangumi_info(self, param: str):
        # 获取番组信息
        url = f"https://api.bilibili.com/pgc/view/web/season?{param}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))
        
        info_json: dict = self.json_get(resp, "result")

        self.info_json = self.get_sections(info_json)
        
        first_episode = self.get_first_episode(self.info_json)

        if param.startswith("season_id"):
            self.ep_id = first_episode["id"]

        self.type_id = self.info_json["type"]

        self.parse_episodes()
    
    @classmethod
    def get_bangumi_available_media_info(cls, bvid: str, cid: str):
        params = {
            "bvid": bvid,
            "cid": cid,
            "fnver": 0,
            "fnval": 12240,
            "fourk": 1
        }

        url = f"https://api.bilibili.com/pgc/player/web/playurl?{cls.url_encode(params)}"

        resp = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = cls.bilibili_url, sessdata = Config.User.SESSDATA))

        data = cls.json_get(resp, "result")

        cls.check_drm_protection(data)

        PreviewInfo.download_json = data

    @classmethod
    def get_bangumi_extra_info(cls, ep_id: int):
        params = {
            "ep_id": ep_id
        }

        url = f"https://api.bilibili.com/pgc/view/web/season?{cls.url_encode(params)}"

        resp = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = cls.bilibili_url, sessdata = Config.User.SESSDATA))

        data: dict = cls.json_get(resp, "result")

        data = cls.get_sections(data)

        first_episode = cls.get_first_episode(data)

        return {
            "bvid": first_episode.get("bvid"),
            "cid": first_episode.get("cid")
        }
    
    @classmethod
    def get_bangumi_season_info(cls, media_id: int):
        url = f"https://www.bilibili.com/bangumi/media/md{media_id}"

        req = RequestUtils.request_get(url)
        req.encoding = "utf-8"

        poster_match = Regex.search(r"<meta property=\"og:image\" content=\"(.*?)\">", req.text)
        description_match = Regex.search(r"\"evaluate\":\"([^\"]+)\"", req.text)
        actors_match = Regex.search(r"\"actors\":\"([^\"]+)\"", req.text)
        tags_match = Regex.findall(r"class=\"media-tag\">(.*?)</span>", req.text)
        pubdate_match = Regex.search(r"\"pub_date\":\"(.*?)\"", req.text)

        return {
            "poster_url": poster_match.group(1) if poster_match else "",
            "description": description_match.group(1) if description_match else "",
            "actors": actors_match.group(1) if actors_match else "",
            "tags": tags_match,
            "pubdate": pubdate_match.group(1) if pubdate_match else ""
        }

    def check_bangumi_can_play(self, param: str):
        url = f"https://api.bilibili.com/pgc/player/web/v2/playurl?{param}"

        self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

    def parse_worker(self, url: str):        
        match Regex.find_string(r"ep|ss|md", url):
            case "ep":
                param = self.get_epid(url)

            case "ss":
                param = self.get_season_id(url)

            case "md":
                param = self.get_mid(url)

        # 先检查视频是否存在区域限制
        self.check_bangumi_can_play(param)

        self.get_bangumi_info(param)

        episode: dict = Episode.Utils.get_first_episode()
        
        if episode:
            self.get_bangumi_available_media_info(episode.get("bvid"), episode.get("cid"))

        return StatusCode.Success.value
    
    def check_json(data: dict):
        status_code = data["code"]
        message = data["message"]

        if status_code != StatusCode.Success.value:
            raise GlobalException(message = message, code = status_code, json_data = data, parse_url = Parser.url)

    def parse_episodes(self):
        Bangumi.parse_episodes(self.info_json, self.ep_id)

    def get_parse_type_str(self):
        return bangumi_type_map.get(self.type_id, "未知")
    
    @staticmethod
    def get_sections(info_json: dict):
        info_json["sections"] = [
            {
                "episodes": info_json.get("episodes")
            }
        ]

        if section := info_json.get("section"):
            info_json["sections"].extend(section)

        return info_json
    
    @staticmethod
    def get_first_episode(info_json: dict):
        for section in info_json.get("sections"):
            for episode in section.get("episodes"):
                return episode
