from utils.common.enums import ParseType

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter
from utils.parse.episode.video import Video
from utils.parse.episode.bangumi import Bangumi

class FavList:
    parent_title: str = ""
    season_dict: dict = {}

    @classmethod
    def parse_episodes(cls, info_json: dict, season_dict: dict, parent_title: str = ""):
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

        Filter.episode_display_mode(reset = True)

    @classmethod
    def parse_episodes_fast(cls, info_json: dict):
        EpisodeInfo.clear_episode_data()

        for episode in info_json.get("episodes"):
            if episode.get("page") != 0:
                EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info_video(episode.copy()))

            elif episode.get("ogv"):
                EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info_bangumi(episode.copy()))

        Filter.episode_display_mode(reset = True)

    @classmethod
    def parse_episodes_detail(cls, video_info_list: list[dict]):
        episode_info_list = []

        for entry in video_info_list:
            if entry:
                match ParseType(entry["parse_type"]):
                    case ParseType.Video:
                        episode_info_list.extend(cls.video_parser(entry))

                    case ParseType.Bangumi:
                        episode_info_list.extend(cls.bangumi_parser(entry))

        return episode_info_list

    @classmethod
    def video_parser(cls, info_json: dict):
        episode_info_list = []
        bvid = info_json.get("bvid")

        if "ugc_season" in info_json:
            episode_info_list = Video.ugc_season_pages_parser(info_json, bvid)
            
        else:
            episode_info_list = Video.pages_parser(info_json, detail_mode = True)

        return episode_info_list

    @classmethod
    def bangumi_parser(cls, info_json: dict):
        return Bangumi.episodes_single_parser(info_json)

    @classmethod
    def get_entry_info_video(cls, episode: dict):
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["type"] = ParseType.Video.value

        return EpisodeInfo.get_entry_info(episode)

    @classmethod
    def get_entry_info_bangumi(cls, episode: dict):
        episode["title"] = "{} - {}".format(episode["title"], episode["intro"])
        episode["badge"] = episode["ogv"]["type_name"]
        episode["season_id"] = episode["ogv"]["season_id"]
        episode["link"] = f"https://www.bilibili.com/bangumi/play/ss{episode.get('season_id')}"
        episode["type"] = ParseType.Bangumi.value

        return EpisodeInfo.get_entry_info(episode)
