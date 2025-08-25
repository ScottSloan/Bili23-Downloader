from utils.parse.episode.episode_v2 import EpisodeInfo, Filter
from utils.parse.episode.video import Video
from utils.parse.episode.bangumi import Bangumi

class FavList:
    target_bvid: str = ""
    season_dict: dict = {}

    @classmethod
    def parse_episodes(cls, info_json: dict, target_bvid: str, season_dict: dict):
        cls.target_bvid = target_bvid
        cls.season_dict = season_dict

        EpisodeInfo.clear_episode_data()

        cls.favlist_parser(info_json)

        Filter.episode_display_mode(reset = True)

    @classmethod
    def favlist_parser(cls, info_json: dict):
        for episode in info_json.get("episodes"):
            if episode.get("page") != 0:
                cls.video_parser(episode.copy())

            elif episode.get("ogv"):
                cls.bangumi_parser(episode.copy())

            else:
                EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info(episode.copy()))

    @classmethod
    def video_parser(cls, episode_info: dict):
        bvid = episode_info.get("bvid")

        video_info = cls.season_dict["video"][bvid]

        if "ugc_season" in video_info:
            Video.ugc_season_parser(video_info.copy())
        else:
            Video.pages_parser(video_info.copy())

    @classmethod
    def bangumi_parser(cls, episode_info: dict):
        season_id = episode_info["ogv"]["season_id"]
        info_json = cls.season_dict["bangumi"][season_id]

        Bangumi.parse_episodes(info_json)

    @classmethod
    def get_entry_info(cls, episode: dict):
        episode["cover_url"] = episode.get("cover")
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["up_name"] = episode["upper"]["name"]
        episode["up_mid"] = episode["upper"]["mid"]
        episode["current_episode"] = episode.get("bvid") == cls.target_bvid
        
        return EpisodeInfo.get_entry_info(episode)