from utils.config import Config
from utils.tool_v2 import FormatTool
from utils.common.enums import ParseType, EpisodeDisplayType
from utils.common.map import cheese_status_map

class EpisodeInfo:
    data: dict = {}
    cid_dict: dict = {}

    @staticmethod
    def clear_episode_data(title: str = "视频"):
        EpisodeInfo.data = {
            "title": title,
            "entries": []
        }
        
        EpisodeInfo.cid_dict.clear()

    @staticmethod
    def add_item(data: list | dict, parent: str, entry_data: dict):
        if isinstance(data, dict):
            if data["title"] == parent:
                if "entries" in data:
                    data["entries"].append(entry_data)
            else:
                if "entries" in data:
                    EpisodeInfo.add_item(data["entries"], parent, entry_data)

        elif isinstance(data, list):
            for entry in data:
                EpisodeInfo.add_item(entry, parent, entry_data)

def video_ugc_season_parser(info_json: dict, cid: int):
    def episode_display_in_section():
        if Config.Misc.episode_display_mode == EpisodeDisplayType.In_Section.value:
            EpisodeInfo.clear_episode_data()

            for episode in _in_section:
                EpisodeInfo.add_item(EpisodeInfo.data, "视频", _get_entry(episode))

    def _get_entry(episode: dict):
        def _get_title(episode: dict):
            if "title" in episode:
                if Config.Misc.show_episode_full_name:
                    return episode["title"]
                else:
                    if episode["page"]["part"]:
                        return episode["page"]["part"]
                    else:
                        return episode["title"]
            else:
                return episode["part"]

        EpisodeInfo.cid_dict[episode["cid"]] = episode

        return {
            "title": _get_title(episode),
            "cid": episode["cid"],
            "badge": "",
            "duration": FormatTool.format_duration(episode, ParseType.Video)
        }

    def _get_node(title: str, duration: str = ""):
        return {
            "title": title,
            "duration": duration,
            "entries": []
        }
    
    EpisodeInfo.data["collection_title"] = info_json["ugc_season"]["title"]

    for section in info_json["ugc_season"]["sections"]:
        EpisodeInfo.add_item(EpisodeInfo.data, "视频", _get_node(section["title"]))

        for episode in section["episodes"]:
            if len(episode["pages"]) == 1:
                EpisodeInfo.add_item(EpisodeInfo.data, section["title"], _get_entry(episode))

                if episode["cid"] == cid:
                    _in_section = section["episodes"]
            else:
                EpisodeInfo.add_item(EpisodeInfo.data, section["title"], _get_node(episode["title"], FormatTool.format_duration(episode, ParseType.Video)))

                for page in episode["pages"]:
                    page["cover_url"] = episode["arc"]["pic"]
                    page["aid"] = episode["aid"]
                    page["bvid"] = episode["bvid"]

                    EpisodeInfo.add_item(EpisodeInfo.data, episode["title"], _get_entry(page))

                    if episode["cid"] == cid:
                        _in_section = episode["pages"]
            
    episode_display_in_section()

def bangumi_episodes_parser(info_json: dict, ep_id: int):
    def bangumi_main_episodes_parser(info_json: dict):
        EpisodeInfo.add_item(EpisodeInfo.data, "视频", {
            "title": "正片",
            "entries": []
        })

        for episode in info_json["episodes"]:
            EpisodeInfo.add_item(EpisodeInfo.data, "正片", _get_entry(episode, main_episode = True))

            if not _check(episode, info_json["episodes"], main_episode = True):
                return False

        return True

    def bangumi_sections_parser(info_json: dict):
        if "section" in info_json:
            for section in info_json["section"]:
                EpisodeInfo.add_item(EpisodeInfo.data, "视频", {
                    "title": section["title"],
                    "entries": []
                })

                for episode in section["episodes"]:
                    EpisodeInfo.add_item(EpisodeInfo.data, section["title"], _get_entry(episode))

                    _check(episode, section["episodes"])
    
    def episode_display_in_section(_in_section: list, main_episode: bool = False):
        if _in_section:
            EpisodeInfo.clear_episode_data()

            for episode in _in_section:
                EpisodeInfo.add_item(EpisodeInfo.data, "视频", _get_entry(episode, main_episode))

    def _check(episode: dict, episodes_list: list, main_episode: bool = False):
        if Config.Misc.episode_display_mode != EpisodeDisplayType.All.value and episode["ep_id"] == ep_id:
            match EpisodeDisplayType(Config.Misc.episode_display_mode):
                case EpisodeDisplayType.Single:
                    episode_display_in_section([episode], main_episode)

                case EpisodeDisplayType.In_Section:
                    episode_display_in_section(episodes_list, main_episode)

            return False
        
        return True
    
    def _get_entry(episode: dict, main_episode: bool = False):
        EpisodeInfo.cid_dict[episode["cid"]] = episode

        return {
            "title": FormatTool.format_bangumi_title(episode, main_episode),
            "cid": episode["cid"],
            "ep_id": episode["ep_id"],
            "badge": episode["badge"],
            "duration": FormatTool.format_duration(episode, ParseType.Bangumi)
        }

    if bangumi_main_episodes_parser(info_json):
        bangumi_sections_parser(info_json)

def live_episode_parser(title: str, status: str):
    EpisodeInfo.add_item(EpisodeInfo.data, "直播", {
        "title": title,
        "badge": status,
        "duration": "--:--",
        "cid": 0
    })

def cheese_episode_parser(info_json: dict, ep_id: int):
    def _get_entry(episode: dict):
        return {
            "title": episode["title"],
            "cid": episode["cid"],
            "badge": _get_label(episode),
            "duration": FormatTool.format_duration(episode, ParseType.Video)
        }
    
    def _get_label(episode: dict):
        if "label" in episode:
            return episode["label"]
        else:
            if episode["status"] != 1:
                return cheese_status_map.get(episode.get("status"))
            else:
                return ""
    
    for episode in info_json["episodes"]:
        if Config.Misc.episode_display_mode == EpisodeDisplayType.Single.value:
            if ep_id != episode["id"]:
                continue

        EpisodeInfo.cid_dict[episode["cid"]] = episode

        EpisodeInfo.add_item(EpisodeInfo.data, "视频", _get_entry(episode))
