from utils.config import Config

from utils.common.exception import GlobalException
from utils.common.map import bangumi_type_map
from utils.common.enums import StatusCode
from utils.common.model.callback import ParseCallback
from utils.common.request import RequestUtils
from utils.common.regex import Regex

from utils.parse.audio import AudioInfo
from utils.parse.episode.episode_v2 import Episode
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

        return f"season_id={resp.get('result').get('media').get('season_id')}"

    def get_bangumi_info(self, param: str):
        # 获取番组信息
        url = f"https://api.bilibili.com/pgc/view/web/season?{param}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))
        
        self.info_json: dict = resp["result"].copy()
        
        first_episode = self.info_json["episodes"][0] if self.info_json.get("episodes") else self.info_json["section"][0]["episodes"][0]

        if param.startswith("season_id"):
            self.ep_id = first_episode["id"]

        self.type_id = self.info_json["type"]

        self.parse_episodes()
    
    def get_bangumi_available_media_info(self, bvid: str, cid: str):
        params = {
            "bvid": bvid,
            "cid": cid,
            "fnver": 0,
            "fnval": 12240,
            "fourk": 1
        }

        url = f"https://api.bilibili.com/pgc/player/web/playurl?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        PreviewInfo.download_json = resp["result"].copy()

    def check_bangumi_can_play(self, param: str):
        url = f"https://api.bilibili.com/pgc/player/web/v2/playurl?{param}"

        self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

    def parse_worker(self, url: str):
        # 清除当前的番组信息
        self.clear_bangumi_info()

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

        episode: dict = Episode.Utils.get_current_episode()

        self.get_bangumi_available_media_info(episode.get("bvid"), episode.get("cid"))

        return StatusCode.Success.value
    
    @staticmethod
    def check_json(data: dict):
        status_code = data["code"]
        message = data["message"]

        if status_code != StatusCode.Success.value:
            if message != "抱歉您所在地区不可观看！":
                return

            raise GlobalException(message = message, code = status_code, json_data = data)

    def parse_episodes(self):
        Episode.Bangumi.parse_episodes(self.info_json, self.ep_id)

    def clear_bangumi_info(self):
        # 重置音质信息
        AudioInfo.clear_audio_info()

    def get_parse_type_str(self):
        return bangumi_type_map.get(self.type_id, "未知")