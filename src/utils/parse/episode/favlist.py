from utils.config import Config
from utils.common.enums import EpisodeDisplayType

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter
from utils.parse.episode.video import Video
from utils.parse.episode.bangumi import Bangumi

class FavList:
    target_bvid: str = ""
    parent_title: str = ""
    season_dict: dict = {}

    @classmethod
    def parse_episodes(cls, info_json: dict, season_dict: dict, parent_title: str):
        cls.season_dict = season_dict
        cls.parent_title = parent_title
        Video.parent_title = parent_title
        Bangumi.parent_title = parent_title

        EpisodeInfo.clear_episode_data()

        for episode in info_json.get("episodes"):
            if episode.get("page") != 0:
                cls.video_parser(episode.copy())

            elif episode.get("ogv"):
                cls.bangumi_parser(episode.copy())

            else:
                EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info(episode.copy()))

        Filter.episode_display_mode(reset = True)

    @classmethod
    def video_parser(cls, episode_info: dict):
        bvid = episode_info.get("bvid")

        if info_json := cls.season_dict["video"][bvid]:
            if "ugc_season" in info_json:
                Video.ugc_season_pages_parser({}, info_json, bvid)
                
            else:
                Video.pages_parser(info_json)

    @classmethod
    def bangumi_parser(cls, episode_info: dict):
        season_id = episode_info["ogv"]["season_id"]

        if info_json := cls.season_dict["bangumi"][season_id]:
            Bangumi.episodes_single_parser(info_json, episode_info["bvid"])

    @classmethod
    def get_entry_info(cls, episode: dict):
        episode["cover_url"] = episode.get("cover")
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["up_name"] = episode["upper"]["name"]
        episode["up_mid"] = episode["upper"]["mid"]
        
        return EpisodeInfo.get_entry_info(episode)