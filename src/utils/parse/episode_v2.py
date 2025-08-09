from utils.config import Config

from utils.common.enums import EpisodeDisplayType, ParseType
from utils.common.map import cheese_status_map
from utils.common.formatter.formatter import FormatUtils

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
            "pid": "",
            "section_title": episode.get("section_title", ""),
            "part_title": episode.get("part_title", ""),
            "collection_title": episode.get("collection_title", ""),
            "item_type": "item",
            "type": episode.get("type", 0)
        }

class Episode:
    class Video:
        target_section_title: str = ""

        @classmethod
        def parse_episodes(cls, info_json: dict, target_cid: int):
            EpisodeInfo.clear_episode_data()

            match Episode.Utils.get_episode_display_type():
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
                if Config.Misc.episode_display_mode == EpisodeDisplayType.Single.value:
                    if page["cid"] != target_cid:
                        continue

                page["cover_url"] = info_json["pic"]
                page["aid"] = info_json["aid"]
                page["bvid"] = info_json["bvid"]
                page["pubtime"] = info_json["pubdate"]
                page["title"] = info_json["title"] if pages_cnt == 1 else page["part"]

                EpisodeInfo.add_item("视频", cls.get_entry_info(page.copy(), info_json["is_upower_exclusive"]))

        @classmethod
        def ugc_season_parser(cls, info_json: dict, target_cid: int):
            is_upower_exclusive = info_json["is_upower_exclusive"]

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
                            page["collection_title"] = collection_title

                            EpisodeInfo.add_item(part_title, cls.get_entry_info(page.copy(), is_upower_exclusive))

                    if cid == target_cid:
                        cls.target_chapter_ttile = section_title

            if Config.Misc.episode_display_mode == EpisodeDisplayType.In_Section.value:
                Episode.Utils.display_episodes_in_section(cls.target_chapter_ttile)
        
        @staticmethod
        def get_entry_info(episode: dict, is_upower_exclusive: bool = False):
            def get_duration():
                if "duration" in episode:
                    return episode["duration"]
                
                elif "arc" in episode:
                    return episode["arc"]["duration"]
                
                else:
                    return 0

            episode["title"] = episode["title"] if "title" in episode else episode["part"]
            episode["badge"] = "充电专属" if is_upower_exclusive else ""
            episode["duration"] = get_duration()
            episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}?p={episode.get('page')}" if episode.get("page", 0) > 1 else f"https://www.bilibili.com/video/{episode.get('bvid')}"
            episode["type"] = ParseType.Video.value

            return EpisodeInfo.get_entry_info(episode)

    class Bangumi:
        target_section_title: str = ""

        @classmethod
        def parse_episodes(cls, info_json: dict, ep_id: int):
            EpisodeInfo.clear_episode_data()

            cls.main_episodes_parser(info_json, ep_id)

            if "section" in info_json:
                cls.section_parser(info_json, ep_id)

            match Episode.Utils.get_episode_display_type():
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

                EpisodeInfo.add_item(pid, cls.get_entry_info(episode.copy()))

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
        def get_entry_info(episode: dict):
            episode["title"] = FormatUtils.format_bangumi_title(episode)
            episode["pubtime"] = episode.get("pub_time")
            episode["duration"] = episode.get("duration", 0) / 1000
            episode["cover_url"] = episode.get("cover")
            episode["link"] = f"https://www.bilibili.com/bangumi/play/ep{episode.get('ep_id')}"
            episode["type"] = ParseType.Bangumi.value

            return EpisodeInfo.get_entry_info(episode)

    class Cheese:
        target_section_title: str = ""

        @classmethod
        def parse_episodes(cls, info_json: dict, ep_id: int):
            EpisodeInfo.clear_episode_data()
    
            cls.sections_parser(info_json, ep_id)

            match Episode.Utils.get_episode_display_type():
                case EpisodeDisplayType.Single:
                    Episode.Utils.display_episodes_in_single(cls.target_section_title, ep_id)

                case EpisodeDisplayType.In_Section:
                    Episode.Utils.display_episodes_in_section(cls.target_section_title)
        
        @classmethod
        def sections_parser(cls, info_json: dict, ep_id: int):
            for section in info_json["sections"]:
                section_title = section["title"]

                EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info(section_title, label = "章节"))

                for episode in section["episodes"]:
                    episode["section_title"] = section_title
                    episode["season_id"] = info_json["season_id"]

                    EpisodeInfo.add_item(section_title, cls.get_entry_info(episode.copy()))

                    if episode["id"] == ep_id:
                        cls.target_section_title = section_title

        @staticmethod
        def get_entry_info(episode: dict):
            def get_badge():
                if "label" in episode:
                    return episode["label"]
                else:
                    if episode["status"] != 1:
                        return cheese_status_map.get(episode.get("status"))
                    else:
                        return ""

            episode["pubtime"] = episode.get("release_date")
            episode["ep_id"] = episode.get("id")
            episode["badge"] = get_badge()
            episode["cover_url"] = episode.get("cover")
            episode["link"] = f"https://www.bilibili.com/cheese/play/ep{episode.get('id')}"
            episode["type"] = ParseType.Cheese.value

            return EpisodeInfo.get_entry_info(episode)
    
    class Popular:
        @classmethod
        def parse_episodes(cls, info_json: dict):
            EpisodeInfo.clear_episode_data()

            section_title = info_json["config"]["label"]

            EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info(section_title, label = "章节"))

            for episode in info_json["list"]:
                episode["section_title"] = section_title
                
                EpisodeInfo.add_item(section_title, cls.get_entry_info(episode.copy()))
            
        @staticmethod
        def get_entry_info(episode: dict):
            episode["pubtime"] = episode.get("pubdate")
            episode["link"] = f"https://www/bilibili.com/video/{episode.get('bvid')}"
            episode["cover_url"] = episode.get("pic")
            episode["type"] = ParseType.Video.value

            return EpisodeInfo.get_entry_info(episode)

    class List:
        @classmethod
        def parse_episodes(cls, info_json: dict):
            EpisodeInfo.clear_episode_data()

            for section_title, entry in info_json["archives"].items():
                EpisodeInfo.add_item("视频", EpisodeInfo.get_node_info(section_title, label = "章节"))

                for episode  in entry["episodes"]:
                    episode["section_title"] = section_title
                    episode["collection_title"] = section_title
                    
                    EpisodeInfo.add_item(section_title, cls.get_entry_info(episode.copy()))
        
        @staticmethod
        def get_entry_info(episode: dict):
            episode["pubtime"] = episode["pubdate"]
            episode["link"] = f"https://www/bilibili.com/video/{episode.get('bvid')}"
            episode["cover_url"] = episode.get("pic")
            episode["type"] = ParseType.Video.value

            return EpisodeInfo.get_entry_info(episode)

    class Utils:
        @staticmethod
        def get_episode_display_type():
            from utils.parse.video import VideoInfo

            mode = Config.Misc.episode_display_mode

            if VideoInfo.is_interactive:
                mode = EpisodeDisplayType.In_Section.value

            return EpisodeDisplayType(mode)
        
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