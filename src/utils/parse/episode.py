from utils.config import Config

from utils.common.enums import ParseType, EpisodeDisplayType, VideoType
from utils.common.map import cheese_status_map
from utils.common.formatter import FormatUtils

class EpisodeInfo:
    data: dict = {}
    cid_dict: dict = {}

    @classmethod
    def clear_episode_data(cls, title: str = "视频"):
        cls.data = {
            "title": title,
            "entries": []
        }
        
        cls.cid_dict.clear()

    @classmethod
    def add_item(cls, data: list | dict, parent: str, entry_data: dict):
        if isinstance(data, dict):
            if data["title"] == parent:
                if "entries" in data:
                    data["entries"].append(entry_data)
            else:
                if "entries" in data:
                    cls.add_item(data["entries"], parent, entry_data)

        elif isinstance(data, list):
            for entry in data:
                cls.add_item(entry, parent, entry_data)

class EpisodeManager:
    def video_ugc_season_parser(info_json: dict, cid: int):
        def episode_display_in_section():
            if Config.Misc.episode_display_mode == EpisodeDisplayType.In_Section.value:
                EpisodeInfo.clear_episode_data()

                for episode in _in_section:
                    EpisodeInfo.add_item(EpisodeInfo.data, "视频", get_entry(episode))

        def get_entry(episode: dict):
            def get_title(episode: dict):
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

            def get_badge():
                if VideoInfo.is_upower_exclusive:
                    return "充电专属"
                else:
                    return ""

            EpisodeInfo.cid_dict[episode["cid"]] = episode

            return {
                "title": get_title(episode),
                "cid": episode["cid"],
                "badge": get_badge(),
                "duration": FormatUtils.format_episode_duration(episode, ParseType.Video)
            }

        def get_node(title: str, duration: str = ""):
            return {
                "title": title,
                "duration": duration,
                "entries": []
            }
        
        from utils.parse.video import VideoInfo
        
        EpisodeInfo.data["collection_title"] = info_json["ugc_season"]["title"]

        for section in info_json["ugc_season"]["sections"]:
            EpisodeInfo.add_item(EpisodeInfo.data, "视频", get_node(section["title"]))

            for episode in section["episodes"]:
                if len(episode["pages"]) == 1:
                    EpisodeInfo.add_item(EpisodeInfo.data, section["title"], get_entry(episode))

                    if episode["cid"] == cid:
                        _in_section = section["episodes"]
                else:
                    EpisodeInfo.add_item(EpisodeInfo.data, section["title"], get_node(episode["title"], FormatUtils.format_episode_duration(episode, ParseType.Video)))

                    for page in episode["pages"]:
                        page["cover_url"] = episode["arc"]["pic"]
                        page["aid"] = episode["aid"]
                        page["bvid"] = episode["bvid"]
                        page["pubtime"] = episode["arc"]["pubdate"]

                        EpisodeInfo.add_item(EpisodeInfo.data, episode["title"], get_entry(page))

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
                "title": FormatUtils.format_bangumi_title(episode, main_episode),
                "cid": episode["cid"],
                "ep_id": episode["ep_id"],
                "badge": episode["badge"],
                "duration": FormatUtils.format_episode_duration(episode, ParseType.Bangumi)
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
                "duration": FormatUtils.format_episode_duration(episode, ParseType.Video)
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

    def get_episode_url(cid: int, parse_type: ParseType):
        episode_info = EpisodeInfo.cid_dict.get(cid)

        match parse_type:
            case ParseType.Video:
                def video():
                    from utils.parse.video import VideoInfo

                    match VideoInfo.type:
                        case VideoType.Single:
                            return VideoInfo.url

                        case VideoType.Part:
                            return f"{VideoInfo.url}?p={episode_info['page']}"

                        case VideoType.Collection:
                            return f"https://www.bilibili.com/video/{episode_info['bvid']}"

                return video()
            
            case ParseType.Bangumi:
                return f"https://www.bilibili.com/bangumi/play/ep{episode_info['ep_id']}"
        
            case ParseType.Live:
                from utils.parse.live import LiveInfo

                return f"https://live.bilibili.com/{LiveInfo.room_id}"
            
            case ParseType.Cheese:
                return f"https://www.bilibili.com/cheese/play/ep{episode_info['id']}"
