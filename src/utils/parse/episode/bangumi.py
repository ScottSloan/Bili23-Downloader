from utils.common.enums import ParseType, TemplateType
from utils.common.formatter.formatter import FormatUtils
from utils.common.map import bangumi_type_map
from utils.common.regex import Regex

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter

class Bangumi:
    target_section_title: str = ""
    target_ep_id: int = 0
    parent_title: str = ""

    @classmethod
    def parse_episodes(cls, info_json: dict, target_ep_id: int = None, parent_title: str = ""):
        cls.target_ep_id = target_ep_id
        cls.parent_title = parent_title
        EpisodeInfo.parser = cls

        if not parent_title:
            EpisodeInfo.clear_episode_data()

        bangumi_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(info_json.get("title"), label = bangumi_type_map.get(info_json.get("type"))))

        if info_json.get("episodes"):
            main_pid = EpisodeInfo.add_item(bangumi_pid, EpisodeInfo.get_node_info("正片", label = "章节"))

            cls.episodes_parser(info_json["episodes"], main_pid, "正片", info_json)

        if "section" in info_json:
            cls.section_parser(info_json, bangumi_pid)

        if not parent_title:
            Filter.episode_display_mode()

    @classmethod
    def episodes_parser(cls, episodes: list, pid: int, section_title: str, info_json: dict):
        for episode in episodes:
            episode["season_id"] = info_json["season_id"]
            episode["media_id"] = info_json["media_id"]
            episode["section_title"] = section_title

            EpisodeInfo.add_item(pid, cls.get_entry_info(episode.copy(), info_json, section_title))

            cls.update_target_section_title(episode, section_title)

    @classmethod
    def section_parser(cls, info_json: dict, pid: str):
        for section in info_json["section"]:
            section_title = section["title"]

            section_pid = EpisodeInfo.add_item(pid, EpisodeInfo.get_node_info(section_title, label = "章节"))

            cls.episodes_parser(section["episodes"], section_pid, section_title, info_json)

    @classmethod
    def get_entry_info(cls, episode: dict, info_json: dict, section_title: str):
        episode["episode_num"] = int(episode.get("title")) if (episode_num := episode.get("title")) and episode_num.isnumeric() else 0
        episode["title"] = FormatUtils.format_bangumi_title(episode, info_json.get("season_title"), section_title, info_json["type"] == 2)
        episode["bvid"] = cls.get_bvid(episode.copy())
        episode["pubtime"] = episode.get("pub_time")
        episode["duration"] = episode.get("duration", 0) / 1000
        episode["cover_url"] = episode.get("cover")
        episode["link"] = cls.get_link(episode.copy())
        episode["type"] = ParseType.Bangumi.value
        episode["series_title"] = info_json.get("season_title")
        episode["area"] = area[0].get("name", "") if (area := info_json.get("areas")) else ""
        episode["up_name"] = info_json.get("up_info", {"uname": ""}).get("uname", "")
        episode["up_mid"] = info_json.get("up_info", {"mid": 0}).get("mid", 0)
        episode["bangumi_type"] = bangumi_type_map.get(info_json.get("type"))
        episode["template_type"] = TemplateType.Bangumi.value if episode.get("ep_id") else TemplateType.Video_Normal.value
        episode["parent_title"] = cls.parent_title

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
    
    @staticmethod
    def get_bvid(episode: dict):
        if (bvid := episode.get("bvid")):
            return bvid
        else:
            if match := Regex.search(r"(BV\w+)", episode.get("link")):
                return match[1]
            else:
                return ""

    @staticmethod
    def get_link(episode: dict):
        if (ep_id := episode.get("ep_id")):
            return f"https://www.bilibili.com/bangumi/play/ep{ep_id}"
        else:
            return episode.get("link")
        