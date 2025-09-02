from utils.common.enums import ParseType, TemplateType

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

        Filter.episode_display_mode(reset = True)

    @classmethod
    def get_entry_info(cls, episode: dict):
        episode["pubtime"] = episode["pubdate"]
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["cover_url"] = episode.get("pic")
        episode["type"] = ParseType.Video.value
        episode["template_type"] = TemplateType.Video_Collection.value

        return EpisodeInfo.get_entry_info(episode)
    
    @classmethod
    def condition_single(cls, episode: dict):
        return episode.get("item_type") == "item" and episode.get("bvid") == cls.target_bvid
