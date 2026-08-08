from ...network.request import SyncNetWorkRequest
from ...download.task.info import TaskInfo

from .base import AdditionalParserBase

class PlayerInfoParser(AdditionalParserBase):
    # web 播放器信息接口，字幕（subtitle.subtitles）与章节（view_points）共用同一份数据
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def get_data(self):
        params = {
            "cid": self.task_info.Episode.cid,
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
            "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
        }

        if self.task_info.Episode.bvid:
            params["bvid"] = self.task_info.Episode.bvid
        else:
            # 课程等条目没有 bvid，改用 aid 请求
            params["aid"] = self.task_info.Episode.aid

        url = f"https://api.bilibili.com/x/player/wbi/v2?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        return response.get("data", {})
