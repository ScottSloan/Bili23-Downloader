from utils.config import Config

from utils.common.request import RequestUtils

from utils.parse.parser import Parser

class OGVParser(Parser):
    def __init__(self):
        super().__init__()

    def get_bangumi_available_media_info(self):
        url = f"https://api.bilibili.com/ogv/player/playview?csrf={Config.User.bili_jct}"

        raw_json = {
            "scene": "normal",
            "video_index": {
                "bvid": "BV1V6pazREaX",
                "cid": None,
                "ogv_season_id": 46244
            },
            "video_param": {
                "qn": 112
            },
            "player_param": {
                "fnver": 0,
                "fnval": 4048,
                "drm_tech_type": 2
            },
            "exp_info": {
                "ogv_half_pay": True
            }
        }

        resp = self.request_post(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA), raw_json = raw_json)

        print(resp)
