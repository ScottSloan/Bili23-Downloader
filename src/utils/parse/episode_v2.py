from utils.config import Config

from utils.common.formatter import FormatUtils
from utils.common.enums import ParseType, EpisodeDisplayType

class EpisodeInfo:
    data: dict = {}
    cid_dict: dict = {}

    @classmethod
    def clear_episode_data(cls, title: str = "视频"):
        cls.data = {
            "label": title,
            "title": "",
            "pid": title,
            "entries": []
        }
        
        cls.cid_dict.clear()

    @classmethod
    def add_item(cls, pid: str, entry_data: dict):
        def add(data: list | dict):
            if isinstance(data, dict):
                if data["pid"] == pid:
                    if "entries" in data:
                        data["entries"].append(entry_data)
                else:
                    if "entries" in data:
                        add(data["entries"])

            elif isinstance(data, list):
                for entry in data:
                    add(entry)

        add(EpisodeInfo.data)

    @staticmethod
    def get_node_info(title: str, duration: int = 0, label: str = ""):
        return {
            "label": label,
            "title": title,
            "duration": duration,
            "pid": title,
            "entries": [],
            "type": "node"
        }

    @staticmethod
    def get_entry_info(episode: dict):
        return {
            "number": 0,
            "title": episode.get("title", ""),
            "cid": episode.get("cid", 0),
            "aid": episode.get("aid", 0),
            "bvid": episode.get("bvid", ""),
            "ep_id": episode.get("ep_id", 0),
            "season_id": episode.get("season_id", 0),
            "media_id": episode.get("media_id", 0),
            "pubtime": episode.get("pubtime", 0),
            "badge": episode.get("badge", ""),
            "duration": episode.get("duration", 0),
            "cover_url": episode.get("cover_url", ""),
            "pid": "",
            "section_title": episode.get("section_title", ""),
            "part_title": episode.get("part_title", ""),
            "type": "item"
        }

class Episode:
    class Video:
        target_section_title: str = ""

        @classmethod
        def parse_episodes(cls, info_json: dict, target_cid: int):
            match EpisodeDisplayType(Config.Misc.episode_display_mode):
                case EpisodeDisplayType.Single:
                    cls.pages_parser(info_json, target_cid)

                case EpisodeDisplayType.In_Section | EpisodeDisplayType.All:
                    if "ugc_season" in info_json:
                        cls.ugc_season_parser(info_json, target_cid)
                    else:
                        cls.pages_parser(info_json, target_cid)

        @classmethod
        def pages_parser(cls, info_json: dict, target_cid: int):
            for page in info_json["pages"]:
                if Config.Misc.episode_display_mode == EpisodeDisplayType.Single.value:
                    if page["cid"] != target_cid:
                        continue

                page["cover_url"] = info_json["pic"]
                page["aid"] = info_json["aid"]
                page["bvid"] = info_json["bvid"]
                page["pubtime"] = info_json["pubdate"]

                EpisodeInfo.add_item("视频", cls.get_entry_info(page.copy(), info_json["is_upower_exclusive"]))

        @classmethod
        def ugc_season_parser(cls, info_json: dict, target_cid: int):
            is_upower_exclusive = info_json["is_upower_exclusive"]

            for section in info_json["ugc_season"]["sections"]:
                section_title = section["title"]

                EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info(section_title, label = "章节"))

                for episode in section["episodes"]:
                    cover_url = episode["arc"]["pic"]
                    cid = episode["cid"]
                    aid = episode["aid"]
                    bvid = episode["bvid"]
                    pubtime = episode["arc"]["pubdate"]

                    if len(episode["pages"]) == 1:
                        episode["cover_url"] = cover_url
                        episode["aid"] = aid
                        episode["bvid"] = bvid
                        episode["pubtime"] = pubtime
                        episode["section_title"] = section_title

                        EpisodeInfo.add_item(section_title, cls.get_entry_info(episode.copy(), is_upower_exclusive))

                    else:
                        part_title = episode["title"]

                        EpisodeInfo.add_item(section_title, EpisodeInfo.get_node_info(part_title, episode["arc"]["duration"], label = "分节"))

                        for page in episode["pages"]:
                            page["cover_url"] = cover_url
                            page["aid"] = aid
                            page["bvid"] = bvid
                            page["pubtime"] = pubtime
                            page["section_title"] = section_title
                            page["part_title"] = part_title

                            EpisodeInfo.add_item(part_title, cls.get_entry_info(page.copy(), is_upower_exclusive))

                    if cid == target_cid:
                        cls.target_chapter_ttile = section_title

            if Config.Misc.episode_display_mode == EpisodeDisplayType.In_Section.value:
                cls.display_episodes_in_section(cls.target_chapter_ttile)
        
        @classmethod
        def display_episodes_in_section(cls, section_title: list):
            for section in EpisodeInfo.data.get("entries"):
                if section.get("pid") == section_title:
                    EpisodeInfo.clear_episode_data()

                    EpisodeInfo.add_item("视频", section)

                    break

        @staticmethod
        def get_entry_info(episode: dict, is_upower_exclusive: bool = False):
            episode["title"] = episode["title"] if "title" in episode else episode["part"]
            episode["badge"] = "充电专属" if is_upower_exclusive else ""
            episode["duration"] = episode["duration"] if "duration" in episode else episode["arc"]["duration"]

            return EpisodeInfo.get_entry_info(episode)

    class Bangumi:
        target_section_title: str = ""

        @classmethod
        def parse_episodes(cls, info_json: dict, ep_id: int):
            cls.main_episodes_parser(info_json, ep_id)

            if "section" in info_json:
                cls.section_parser(info_json, ep_id)

            match EpisodeDisplayType(Config.Misc.episode_display_mode):
                case EpisodeDisplayType.Single:
                    cls.display_episodes_in_single(cls.target_section_title, ep_id)

                case EpisodeDisplayType.In_Section:
                    cls.display_episodes_in_section(cls.target_section_title)
        
        @classmethod
        def episodes_parser(cls, episodes: dict, pid: str, ep_id: int, info_json: dict):
            for episode in episodes:
                episode["season_id"] = info_json["season_id"]
                episode["media_id"] = info_json["media_id"]
                episode["section_title"] = pid

                EpisodeInfo.add_item(pid, cls.get_entry_info(episode.copy()))

                if episode["ep_id"] == ep_id:
                    cls.target_section_title = pid

        @classmethod
        def main_episodes_parser(cls, info_json: dict, ep_id: int):
            EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info("正片", label = "章节"))

            cls.episodes_parser(info_json["episodes"], "正片", ep_id, info_json)

        @classmethod
        def section_parser(cls, info_json: dict, ep_id: int):
            for section in info_json["section"]:
                section_title = section["title"]

                EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info(section_title, label = "章节"))

                cls.episodes_parser(section["episodes"], section_title, ep_id, info_json)

        @classmethod
        def display_episodes_in_section(cls, section_title: str):
            for section in EpisodeInfo.data.get("entries"):
                if section.get("pid") == section_title:
                    EpisodeInfo.clear_episode_data()

                    EpisodeInfo.add_item("视频", section)

                    break
        
        @classmethod
        def display_episodes_in_single(cls, section_title: str, ep_id: int):
            for section in EpisodeInfo.data.get("entries"):
                if section.get("pid") == section_title:
                    for episode in section.get("entries"):
                        if episode.get("ep_id") == ep_id:
                            EpisodeInfo.clear_episode_data()

                            EpisodeInfo.add_item("视频", episode)

                            break

        @staticmethod
        def get_entry_info(episode: dict):
            episode["title"] = episode["show_title"]
            episode["pubtime"] = episode["pub_time"]
            episode["duration"] = episode["duration"] / 1000
            episode["cover_url"] = episode["cover"]

            return EpisodeInfo.get_entry_info(episode)

    class Cheese:
        pass