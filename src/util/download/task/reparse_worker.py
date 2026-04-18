from PySide6.QtCore import QRunnable

from util.parse.episode.bangumi import BangumiEpisodeParser
from util.parse.episode.cheese import CheeseEpisodeParser
from util.parse.episode.video import VideoEpisodeParser

from util.parse.episode.tree import EpisodeData, Attribute
from util.common.data.bangumi_type import bangumi_type_map
from util.parse.parser.base import ParserBase
from util.network import SyncNetWorkRequest
from util.common import signal_bus

class ReparseWorker(QRunnable, ParserBase):
    def __init__(self, episode_info: dict):
        super().__init__()

        self.info_data: dict = None
        self.episode_info: dict = episode_info
        self.original_episode_data: dict = None

    def run(self):
        # 提取收藏夹/个人空间的 episode_data
        self.original_episode_data = EpisodeData.get_episode_data(self.episode_info.get("episode_id"))
        
        episode_node = self.parse_episode_node_info()

        signal_bus.download.create_task.emit(episode_node.get_all_children(to_dict = True))

    def parse_episode_node_info(self):
        # 视频
        if self.episode_info.get("attribute", 0) & Attribute.VIDEO_BIT:
            episode_parser = self.parse_video_info()

        # 剧集
        elif self.episode_info.get("attribute", 0) & Attribute.BANGUMI_BIT:
            episode_parser = self.parse_bangumi_info()

        # 课程
        elif self.episode_info.get("attribute", 0) & Attribute.CHEESE_BIT:
            episode_parser = self.parse_cheese_info()

        return episode_parser.parse()
    
    def parse_video_info(self):
        bvid = self.episode_info.get("bvid")

        self.get_video_info(bvid)

        return VideoEpisodeParser(self.info_data, "USER_UPLOADS", kwargs = self.get_kwargs(bvid))

    def parse_bangumi_info(self):
        ep_id = self.episode_info.get("ep_id")

        self.get_bangumi_info(ep_id)
            
        category_name = bangumi_type_map.get(self.info_data["result"]["type"])

        return BangumiEpisodeParser(self.info_data, category_name, kwargs = self.get_kwargs(ep_id))

    def parse_cheese_info(self):
        season_id = self.episode_info.get("ep_id")

        self.get_cheese_info(season_id)

        return CheeseEpisodeParser(self.info_data, "COURSE", kwargs = self.get_kwargs(season_id))
    
    def get_kwargs(self, target_episode_info: str | int):
        return {
            "target_episode_info": target_episode_info,
            "target_episode_data_id": self.episode_info.get("episode_id"),
            "target_attribute": self.episode_info.get("attribute") & ~Attribute.NEED_PARSE_BIT
        }
    
    def get_video_info(self, bvid: str):
        params = {
            "bvid": bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_bangumi_info(self, ep_id: str):
        url = f"https://api.bilibili.com/pgc/view/web/season?ep_id={ep_id}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_cheese_info(self, season_id: int):
        url = f"https://api.bilibili.com/pugv/view/web/season/v2?season_id={season_id}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response
