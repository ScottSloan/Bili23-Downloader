from utils.config import Config

from utils.common.enums import ParseType, EpisodeDisplayType

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter

class List:
    target_bvid: str = ""

    @classmethod
    def parse_episodes(cls, info_json: dict, target_bvid: str):
        cls.target_bvid = target_bvid
        EpisodeInfo.parser = cls

        EpisodeInfo.clear_episode_data()

        for section_title, entry in info_json["archives"].items():
            section_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(section_title, label = "合集"))

            for episode in entry["episodes"]:
                episode["collection_title"] = section_title
                
                EpisodeInfo.add_item(section_pid, cls.get_entry_info(episode.copy()))

        if EpisodeDisplayType(Config.Misc.episode_display_mode) == EpisodeDisplayType.In_Section:
            Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

        Filter.episode_display_mode()

    @classmethod
    def get_entry_info(cls, episode: dict):
        episode["pubtime"] = episode["pubdate"]
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["cover_url"] = episode.get("pic")
        episode["type"] = ParseType.Video.value
        episode["current_episode"] = episode.get("bvid") == cls.target_bvid

        return EpisodeInfo.get_entry_info(episode)
    
    @classmethod
    def condition_single(cls, episode: dict):
        return episode.get("item_type") == "item" and episode.get("bvid") == cls.target_bvid
