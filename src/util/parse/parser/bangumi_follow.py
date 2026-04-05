from util.network.request import NetworkRequestWorker
from util.download.cover.manager import cover_manager
from util.parse.parser.base import ParserBase
from util.thread import AsyncTask
from util.common import config

import math

class BangumiFollowParser(ParserBase):
    def __init__(self):
        super().__init__()
        
        self.success_callback = None
        self.ps = 24

    def parse(self, pn: int = 1, type: int = 1, follow_status: int = 0):
        self.pn = pn
        self.type = type
        self.follow_status = follow_status

        self.get_follow_list()

    def get_follow_list(self):
        params = {
            "vmid": config.user_uid,
            "type": self.type,
            "pn": self.pn,
            "ps": 24,
            "playform": 1,
            "follow_status": self.follow_status,
            "web_location": "333.1387"
        }

        url = f"https://api.bilibili.com/x/space/bangumi/follow/list?{self.enc_wbi(params)}"
        
        worker = NetworkRequestWorker(url)
        worker.success.connect(self.on_success)
        worker.error.connect(self.on_error)
        
        AsyncTask.run(worker)

    def on_success(self, response: dict):
        entry_list = []

        for entry in response.get("data", {}).get("list", []):
            title = entry.get("title", "")
            season_id = entry.get("season_id", "")
            season_type = entry.get("season_type_name", "")
            area = entry.get("areas", "")[0]["name"]
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