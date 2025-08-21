from utils.common.enums import ParseType
from utils.common.formatter.formatter import FormatUtils

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter

class Bangumi:
    target_section_title: str = ""
    target_ep_id: int = 0

    @classmethod
    def parse_episodes(cls, info_json: dict, target_ep_id: int):
        cls.target_ep_id = target_ep_id
        EpisodeInfo.parser = cls

        EpisodeInfo.clear_episode_data()

        cls.main_episodes_parser(info_json)

        if "section" in info_json:
            cls.section_parser(info_json)

        Filter.episode_display_mode()

    @classmethod
    def episodes_parser(cls, episodes: dict, pid: int, section_title: str, info_json: dict):
        for episode in episodes:
            episode["season_id"] = info_json["season_id"]
            episode["media_id"] = info_json["media_id"]
            episode["section_title"] = pid

            EpisodeInfo.add_item(pid, cls.get_entry_info(episode.copy(), info_json))

            cls.update_target_section_title(episode, section_title)

    @classmethod
    def main_episodes_parser(cls, info_json: dict):
        if info_json.get("episodes"):
            main_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info("正片", label = "章节"))

            cls.episodes_parser(info_json["episodes"], main_pid, "正片", info_json)

    @classmethod
    def section_parser(cls, info_json: dict):
        for section in info_json["section"]:
            section_title = section["title"]

            section_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(section_title, label = "章节"))

            cls.episodes_parser(section["episodes"], section_pid, section_title, info_json)

    @classmethod
    def get_entry_info(cls, episode: dict, info_json: dict):
        episode["title"] = FormatUtils.format_bangumi_title(episode, info_json.get("season_title") if info_json["type"] == 2 else None)
        episode["pubtime"] = episode.get("pub_time")
        episode["duration"] = episode.get("duration", 0) / 1000
        episode["cover_url"] = episode.get("cover")
        episode["link"] = f"https://www.bilibili.com/bangumi/play/ep{episode.get('ep_id')}"
        episode["type"] = ParseType.Bangumi.value
        episode["series_title"] = info_json.get("season_title")
        episode["area"] = area[0].get("name", "") if (area := info_json.get("areas")) else ""
        episode["up_name"] = info_json.get("up_info", {"uname": ""}).get("uname", "")
        episode["up_mid"] = info_json.get("up_info", {"mid": 0}).get("mid", 0)
        episode["current_episode"] = episode.get("ep_id") == cls.target_ep_id

        return EpisodeInfo.get_entry_info(episode)
    
    @classmethod
    def update_target_section_title(cls, episode: dict, section_title: str):
        if episode.get("ep_id") == cls.target_ep_id:
            cls.target_section_title = section_title

    @classmethod
    def condition_single(cls, episode: dict):
        return episode.get("item_type") == "item" and episode.get("ep_id") == cls.target_ep_id
    
    @classmethod
    def condition_in_section(cls, episode: dict):
        return episode.get("item_type") == "node" and episode.get("title") == cls.target_section_title