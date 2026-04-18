from util.network import NetworkRequestWorker
from util.thread import AsyncTask
from util.common import config

from ...download.cover.manager import cover_manager
from .base import ParserBase

from urllib.parse import urlencode
import math

class FavoriteParser(ParserBase):
    """
    收藏夹列表、订阅合集列表、追番追剧解析相关
    """
    def __init__(self):
        super().__init__()
        
        self.success_callback = None
        self.ps = 24

    def parse_favorite_list(self):
        self.get_favorite_list()

    def parse_subscription_list(self):
        self.get_subscription_list()

    def parse_follow_list(self, pn: int = 1, type: int = 1, follow_status: int = 0):
        self.pn = pn
        self.type = type
        self.follow_status = follow_status

        self.get_follow_list()

    def get_favorite_list(self):
        url = "https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={uid}".format(uid = config.user_uid)

        worker = NetworkRequestWorker(url)
        worker.success.connect(self.on_get_favorite_list_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    def get_subscription_list(self):
        param = {
            "pn": 1,
            "ps": 50,
            "up_mid": config.user_uid,
            "platform": "web",
            "web_location": "333.1387"
        }

        url = f"https://api.bilibili.com/x/v3/fav/folder/collected/list?{urlencode(param)}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(self.on_get_subscription_list_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    def get_follow_list(self):
        params = {
            "vmid": config.user_uid,
            "type": self.type,
            "pn": self.pn,
            "ps": 24,
            "playform": "web",
            "follow_status": self.follow_status,
            "web_location": "333.1387"
        }

        url = f"https://api.bilibili.com/x/space/bangumi/follow/list?{self.enc_wbi(params)}"
        
        worker = NetworkRequestWorker(url)
        worker.success.connect(self.on_get_follow_list_success)
        worker.error.connect(self.on_error)
        
        AsyncTask.run(worker)

    def on_get_favorite_list_success(self, response: dict):
        entry_list = []

        for entry in response.get("data", {}).get("list", []):
            title = entry.get("title", "")
            mid = entry.get("mid", "")
            fid = entry.get("id", "")
            count = entry.get("media_count", 0)

            entry_list.append({
                "title": title,
                "url": "https://space.bilibili.com/{mid}/favlist?fid={fid}".format(mid = mid, fid = fid),
                "count": count,
                "cover": fid,
                "cover_id": f"__query__{fid}" if count > 0 else None
            })
        
        self.success_callback(entry_list)

    def on_get_subscription_list_success(self, response: dict):
        entry_list = []

        for entry in response.get("data", {}).get("list", []):
            title = entry.get("title", "")
            mid = entry.get("mid", "")
            id = entry.get("id", "")
            count = entry.get("media_count", 0)
            cover = entry.get("cover", "")

            entry_list.append({
                "title": title,
                "url": "https://space.bilibili.com/{mid}/lists/{id}?type=season".format(mid = mid, id = id),
                "count": count,
                "cover": cover,
                "cover_id": cover_manager.arrange_cover_id(cover)
            })

        self.success_callback(entry_list)

    def on_get_follow_list_success(self, response: dict):
        entry_list = []

        for entry in response.get("data", {}).get("list", []):
            title = entry.get("title", "")
            season_id = entry.get("season_id", "")
            season_type = entry.get("season_type_name", "")
            area = entry["areas"][0]["name"] if entry.get("areas") else ""
            new_ep = entry.get("new_ep", {}).get("index_show", "")
            progress = entry.get("progress", "")
            desc = entry.get("evaluate", "")
            cover = entry.get("cover", "")

            entry_list.append({
                "title": title,
                "url": f"https://www.bilibili.com/bangumi/play/ss{season_id}",
                "type": f"{season_type} · {area}",
                "new_ep": new_ep,
                "progress": progress,
                "desc": desc,
                "cover": cover,
                "cover_id": cover_manager.arrange_cover_id(cover)
            })
        
        self.success_callback(entry_list, self.get_extra_data(response))

    def get_extra_data(self, response: dict):
        count = response["data"]["total"]

        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / self.ps),
                "total_items": count,
                "current_page": self.pn
            }
        }