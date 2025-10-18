from utils.common.enums import ParseType, TemplateType

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter
from utils.parse.episode.video import Video
from utils.parse.episode.cheese import Cheese

class Space:
    video_info_dict: dict = {}
    cheese_info_dict: dict = {}

    @classmethod
    def parse_episodes_fast(cls, info_json: dict):
        EpisodeInfo.clear_episode_data()

        for episode in info_json.get("episodes"):
            if episode.get("is_lesson_video"):
                EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info_cheese(episode.copy()))
            else:
                EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info_video(episode.copy()))

        Filter.episode_display_mode(reset = True)

    @classmethod
    def parse_episodes_detail(cls, video_info_list: dict[str, dict], parent_title: str):
        episode_info_list = []

        for entry in video_info_list["sequence"]:
            key, value = entry["key"], entry["value"]

            info_json = video_info_list[key][value]

            if key.startswith("video"):
                episode_info_list.extend(cls.video_parser(info_json, parent_title))

            else:
                episode_info_list.extend(cls.cheese_parser(info_json, parent_title))

        return episode_info_list

    @classmethod
    def video_parser(cls, info_json: dict, parent_title: str):
        episode_info_list = []
        bvid = info_json.get("bvid")

        if info_json["is_avoided"]:
            episode_info_list = Video.ugc_season_parser(info_json, parent_title)

        elif "ugc_season" in info_json:
            episode_info_list = Video.ugc_season_pages_parser(info_json, bvid, parent_title)

        else:
            episode_info_list = Video.pages_parser(info_json, parent_title)

        return episode_info_list
    
    @classmethod
    def cheese_parser(cls, info_json: dict, parent_title: str):
        return Cheese.sections_parser(info_json, parent_title)

    @classmethod
    def get_entry_info_video(cls, episode: dict):
        episode["cover_url"] = episode["pic"]
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["duration"] = cls.get_duration(episode.get("length"))
        episode["type"] = ParseType.Video.value
        episode["badge"] = cls.get_badge(episode.copy())
        episode["template_type"] = TemplateType.Video_Collection.value if episode.get("is_avoided") else TemplateType.Video_Part.value

        return EpisodeInfo.get_entry_info(episode)
    
    @classmethod
    def get_entry_info_cheese(cls, episode: dict):
        episode["cover_url"] = episode["pic"]
        episode["link"] = episode["jump_url"]
        episode["type"] = ParseType.Cheese.value
        episode["badge"] = cls.get_badge(episode.copy())

        return EpisodeInfo.get_entry_info(episode)
    
    @staticmethod
    def get_duration(length: str):
        time_parts = length.split(":")
        seconds = sum(int(part) * 60 ** i for i, part in enumerate(reversed(time_parts)))

        return seconds
    
    @staticmethod
    def get_badge(episode: dict):
        if episode.get("is_lesson_video"):
            return "课程"
        
        elif episode.get("is_union_video"):
            return "合作"
        
        elif episode.get("is_live_playback"):
            return "直播回放"
        
        elif episode.get("is_charging_arc"):
            return "充电专属"
        
        else:
            return ""