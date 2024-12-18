from utils.config import Config
from utils.tool_v2 import FormatTool

class EpisodeInfo:
    data: dict = {}
    cid_dict: dict = {}

    @staticmethod
    def clear_episode_data():
        EpisodeInfo.data = {
            "title": "视频",
            "entries": []
        }
        
        EpisodeInfo.cid_dict.clear()

    @staticmethod
    def add_item(data: list | dict, parent: str, entry_data: dict):
        if isinstance(data, dict):
            if data["title"] == parent:
                data["entries"].append(entry_data)
            else:
                if "entries" in data:
                    EpisodeInfo.add_item(data["entries"], parent, entry_data)

        elif isinstance(data, list):
            for entry in data:
                EpisodeInfo.add_item(entry, parent, entry_data)

def video_ugc_season_parser(info_json: dict, cid: int):
    def episode_display_in_section():
        if Config.Misc.episode_display_mode == Config.Type.EPISODES_IN_SECTION:
            EpisodeInfo.clear_episode_data()

            for episode in _in_section:
                EpisodeInfo.add_item(EpisodeInfo.data, "视频", _get_entry(episode))

    def _get_entry(episode: dict):
        def _get_title(episode: dict):
            if "title" in episode:
                if Config.Misc.show_episode_full_name:
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
            "duration": FormatTool.format_duration(episode, Config.Type.VIDEO)
        }

    def _get_node(title: str, duration: str = ""):
        return {
            "title": title,
            "duration": duration,
            "entries": []
        }

    for section in info_json["ugc_season"]["sections"]:
        EpisodeInfo.add_item(EpisodeInfo.data, "视频", _get_node(section["title"]))

        for episode in section["episodes"]:
            if len(episode["pages"]) == 1:
                EpisodeInfo.add_item(EpisodeInfo.data, section["title"], _get_entry(episode))

                if episode["cid"] == cid:
                    _in_section = section["episodes"]
            else:
                EpisodeInfo.add_item(EpisodeInfo.data, section["title"], _get_node(episode["title"], FormatTool.format_duration(episode, Config.Type.VIDEO)))

                for page in episode["pages"]:
                    EpisodeInfo.add_item(EpisodeInfo.data, episode["title"], _get_entry(page))

                    if episode["cid"] == cid:
                        _in_section = episode["pages"]
            
    episode_display_in_section()

def bangumi_episodes_parser(info_json: dict, ep_id: int):
    def bangumi_main_episodes_parser(info_json: dict, ep_id: int):
        EpisodeInfo.add_item(EpisodeInfo.data, "视频", {
            "title": "正片",
            "entries": []
        })

        for episode in info_json["episodes"]:
            EpisodeInfo.add_item(EpisodeInfo.data, "正片", _get_entry(episode))

            if not _check(episode, info_json["episodes"]):
                return False

        return True

    def bangumi_sections_parser(info_json: dict, ep_id: int):
        for section in info_json["section"]:
            EpisodeInfo.add_item(EpisodeInfo.data, "视频", {
                "title": section["title"],
                "entries": []
            })

            for episode in section["episodes"]:
                EpisodeInfo.add_item(EpisodeInfo.data, section["title"], _get_entry(episode))

                _check(episode, section["episodes"])
    
    def episode_display_in_section(_in_section: list):
        if _in_section:
            EpisodeInfo.clear_episode_data()

            for episode in _in_section:
                EpisodeInfo.add_item(EpisodeInfo.data, "视频", _get_entry(episode))

    def _check(episode: dict, episodes_list: list):
        if Config.Misc.episode_display_mode != Config.Type.EPISODES_ALL_SECTIONS and episode["ep_id"] == ep_id:
            match Config.Misc.episode_display_mode:
                case Config.Type.EPISODES_SINGLE:
                    episode_display_in_section([episode])

                case Config.Type.EPISODES_IN_SECTION:
                    episode_display_in_section(episodes_list)

            return False
        
        return True
    
    def _get_entry(episode: dict):
        EpisodeInfo.cid_dict[episode["cid"]] = episode

        return {
            "title": FormatTool.format_bangumi_title(episode),
            "cid": episode["cid"],
            "ep_id": episode["ep_id"],
            "badge": episode["badge"],
            "duration": FormatTool.format_duration(episode, Config.Type.BANGUMI)
        }

    if bangumi_main_episodes_parser(info_json, ep_id):
        bangumi_sections_parser(info_json, ep_id)
