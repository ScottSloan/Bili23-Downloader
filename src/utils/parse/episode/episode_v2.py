import random
from typing import Callable

from utils.config import Config

from utils.common.enums import EpisodeDisplayType, ParseType
from utils.common.formatter.formatter import FormatUtils

class EpisodeInfo:
    data: dict = {}
    filted_data: dict = {}

    pid_list: list = []
    root_pid: int = 0

    parser = None

    @classmethod
    def get_pid(cls):
        while True:
            pid = random.randint(1, 99999999)

            if pid not in cls.pid_list:
                cls.pid_list.append(pid)
                return pid
            
    @classmethod
    def clear_episode_data(cls, title: str = "视频"):
        cls.root_pid = cls.get_pid()

        cls.pid_list = [cls.root_pid]

        cls.data = {
            "label": title,
            "title": "",
            "pid": cls.root_pid,
            "entries": []
        }
    
    @classmethod
    def clear_filter_data(cls, title: str = "视频"):
        cls.filted_data = {
            "label": title,
            "title": "",
            "pid": cls.root_pid,
            "entries": []
        }

    @classmethod
    def add_item(cls, pid: int, entry_data: dict, target_data: dict = None):
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

        if not target_data:
            target_data = EpisodeInfo.data

        add(target_data)
        
        return entry_data.get("pid", 0)
        
    @classmethod
    def get_node_info(cls, title: str, duration: int = 0, label: str = ""):
        return {
            "label": label,
            "title": title,
            "duration": duration,
            "pid": cls.get_pid(),
            "entries": [],
            "item_type": "node"
        }

    @staticmethod
    def get_entry_info(episode: dict):
        return {
            "number": 0,
            "page": episode.get("page", 0),
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
            "link": episode.get("link"),
            "pid": 0,
            "section_title": episode.get("section_title", ""),
            "part_title": episode.get("part_title", ""),
            "collection_title": episode.get("collection_title", ""),
            "series_title": episode.get("series_title", ""),
            "area": episode.get("area", ""),
            "zone": episode.get("zone", ""),
            "subzone": episode.get("subzone", ""),
            "up_name": episode.get("up_name", ""),
            "up_mid": episode.get("up_mid", 0),
            "current_episode": episode.get("current_episode", False),
            "item_type": "item",
            "type": episode.get("type", 0)
        }

class Episode:
    class Video:
        target_section_title: str = ""
        target_chapter_ttile: str = ""

        @classmethod
        def parse_episodes(cls, info_json: dict):
            EpisodeInfo.clear_episode_data()

            target_cid = info_json.get("cid")

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
            pages_cnt = len(info_json["pages"])

            for page in info_json["pages"]:
                if Episode.Utils.is_single_mode():
                    if page["cid"] != target_cid:
                        continue

                page["cover_url"] = info_json["pic"]
                page["aid"] = info_json["aid"]
                page["bvid"] = info_json["bvid"]
                page["pubtime"] = info_json["pubdate"]
                page["title"] = info_json["title"] if pages_cnt == 1 else page["part"]

                EpisodeInfo.add_item("视频", cls.get_entry_info(page.copy(), info_json))

        @classmethod
        def ugc_season_parser(cls, info_json: dict, target_cid: int = None):
            for section in info_json["ugc_season"]["sections"]:
                collection_title = info_json["ugc_season"]["title"]
                section_title = section["title"]

                EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info(section_title, label = "章节"))

                for episode in section["episodes"]:
                    cover_url = episode["arc"]["pic"]
                    cid = episode["cid"]
                    aid = episode["aid"]
                    bvid = episode["bvid"]
                    pubtime = episode["arc"]["pubdate"]

                    if len(episode["pages"]) == 1:
                        episode["page"] = episode["page"]["page"] if isinstance(episode["page"], dict) else episode["page"]
                        episode["cover_url"] = cover_url
                        episode["aid"] = aid
                        episode["bvid"] = bvid
                        episode["pubtime"] = pubtime
                        episode["section_title"] = section_title
                        episode["collection_title"] = collection_title

                        EpisodeInfo.add_item(section_title, cls.get_entry_info(episode.copy(), info_json))

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
                            page["collection_title"] = collection_title

                            EpisodeInfo.add_item(part_title, cls.get_entry_info(page.copy(), info_json))

                    if cid and cid == target_cid:
                        cls.target_chapter_ttile = section_title

            if Config.Misc.episode_display_mode == EpisodeDisplayType.In_Section.value and cid:
                Episode.Utils.display_episodes_in_section(cls.target_chapter_ttile)
        
        @staticmethod
        def get_entry_info(episode: dict, info_json: dict):
            def get_duration():
                if "duration" in episode:
                    return episode["duration"]
                
                elif "arc" in episode:
                    return episode["arc"]["duration"]
                
                else:
                    return 0

            def get_link():
                page = episode.get("page", 0)

                if page > 1:
                    return f"https://www.bilibili.com/video/{episode.get('bvid')}?p={episode.get('page')}"
                else:
                    return f"https://www.bilibili.com/video/{episode.get('bvid')}"
            
            episode["title"] = episode.get("title", episode.get("part", ""))
            episode["badge"] = "充电专属" if info_json.get("is_upower_exclusive", "") else ""
            episode["duration"] = get_duration()
            episode["link"] = get_link()
            episode["type"] = ParseType.Video.value
            episode["zone"] = info_json.get("tname", "")
            episode["subzone"] = info_json.get("tname_v2", "")
            episode["up_name"] = info_json.get("owner", {"name": ""}).get("name", "")
            episode["up_mid"] = info_json.get("owner", {"mid": 0}).get("mid", 0)
            episode["current_episode"] = info_json.get("cid") == episode.get("cid")

            return EpisodeInfo.get_entry_info(episode)

    class Bangumi:
        target_section_title: str = ""

        @classmethod
        def parse_episodes(cls, info_json: dict, ep_id: int):
            EpisodeInfo.clear_episode_data()

            cls.main_episodes_parser(info_json, ep_id)

            if "section" in info_json:
                cls.section_parser(info_json, ep_id)

            match EpisodeDisplayType(Config.Misc.episode_display_mode):
                case EpisodeDisplayType.Single:
                    Episode.Utils.display_episodes_in_single(cls.target_section_title, ep_id)

                case EpisodeDisplayType.In_Section:
                    Episode.Utils.display_episodes_in_section(cls.target_section_title)
        
        @classmethod
        def episodes_parser(cls, episodes: dict, pid: str, ep_id: int, info_json: dict):
            for episode in episodes:
                episode["season_id"] = info_json["season_id"]
                episode["media_id"] = info_json["media_id"]
                episode["section_title"] = pid

                EpisodeInfo.add_item(pid, cls.get_entry_info(episode.copy(), info_json, ep_id))

                if episode["ep_id"] == ep_id:
                    cls.target_section_title = pid

        @classmethod
        def main_episodes_parser(cls, info_json: dict, ep_id: int):
            if info_json.get("episodes"):
                EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info("正片", label = "章节"))

                cls.episodes_parser(info_json["episodes"], "正片", ep_id, info_json)

        @classmethod
        def section_parser(cls, info_json: dict, ep_id: int):
            for section in info_json["section"]:
                section_title = section["title"]

                EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info(section_title, label = "章节"))

                cls.episodes_parser(section["episodes"], section_title, ep_id, info_json)

        @staticmethod
        def get_entry_info(episode: dict, info_json: dict, ep_id: int):
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
            episode["current_episode"] = episode.get("ep_id") == ep_id

            return EpisodeInfo.get_entry_info(episode)

    class FavList:
        @classmethod
        def parse_episodes(cls, info_json: dict, bvid: str):
            EpisodeInfo.clear_episode_data()

            for episode in info_json.get("episodes"):
                EpisodeInfo.add_item("视频", cls.get_entry_info(episode.copy(), bvid))

        def get_entry_info(episode: dict, bvid: str):
            episode["cover_url"] = episode.get("cover")
            episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
            episode["up_name"] = episode["upper"]["name"]
            episode["up_mid"] = episode["upper"]["mid"]
            episode["current_episode"] = episode.get("bvid") == bvid
            
            return EpisodeInfo.get_entry_info(episode)

    class Utils:
        @staticmethod
        def display_episodes_in_section(section_title: str):
            for section in EpisodeInfo.data.get("entries"):
                if section.get("pid") == section_title:
                    EpisodeInfo.clear_episode_data()

                    EpisodeInfo.add_item("视频", section)

                    break

        @staticmethod
        def display_episodes_in_single(section_title: str, ep_id: int):
            for section in EpisodeInfo.data.get("entries"):
                if section.get("pid") == section_title:
                    for episode in section.get("entries"):
                        if episode.get("ep_id") == ep_id:
                            EpisodeInfo.clear_episode_data()

                            EpisodeInfo.add_item("视频", episode)

                            break
        
        @staticmethod
        def is_single_mode():
            return Config.Misc.episode_display_mode == EpisodeDisplayType.Single.value
        
        @staticmethod
        def get_current_episode():
            def get_episode(data: dict | list):
                if isinstance(data, dict):
                    if "entries" not in data:
                        if data.get("current_episode"):
                            return data
                    else:
                        for value in data["entries"]:
                            if episode := get_episode(value):
                                return episode

                elif isinstance(data, list):
                    for entry in data:
                        if episode := get_episode(entry):
                            return episode

            return get_episode(EpisodeInfo.data)
        
class Filter:
    @staticmethod
    def travarsal_episode(condition: Callable):
        def traveral(data: list | dict):
            if isinstance(data, dict):
                r = condition(data)

                if r:
                    return data
                
                if "entries" in data:
                    rtn = traveral(data.get("entries"))

                    if rtn:
                        return rtn

            elif isinstance(data, list):
                for entry in data:
                    rtn = traveral(entry)
                    if rtn:
                        return rtn
        
        return traveral(EpisodeInfo.data.copy())

    @classmethod
    def episode_display_mode(cls):
        EpisodeInfo.clear_filter_data()

        match EpisodeDisplayType(Config.Misc.episode_display_mode):
            case EpisodeDisplayType.Single:
                episode = cls.travarsal_episode(EpisodeInfo.parser.condition_single)

            case EpisodeDisplayType.In_Section:
                episode = cls.travarsal_episode(EpisodeInfo.parser.condition_in_section)

            case EpisodeDisplayType.All:
                EpisodeInfo.filted_data = EpisodeInfo.data.copy()
                return
            
        EpisodeInfo.add_item(EpisodeInfo.root_pid, episode, target_data = EpisodeInfo.filted_data)