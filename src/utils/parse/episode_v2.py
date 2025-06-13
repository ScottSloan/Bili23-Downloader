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

class Episode:
    class Video:
        @classmethod
        def parse_episodes(cls, info_json: dict, target_cid: int):
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

                EpisodeInfo.add_item("视频", cls.get_entry_info(page))

        @classmethod
        def ugc_season_parser(cls, info_json: dict, target_cid: int):
            is_upower_exclusive = info_json["is_upower_exclusive"]
            target_chapter_ttile = ""

            for section in info_json["ugc_season"]["sections"]:
                chapter_title = section["title"]

                EpisodeInfo.add_item("视频", cls.get_node_info(chapter_title, label = "章节"))

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
                        episode["chapter_title"] = chapter_title

                        EpisodeInfo.add_item(chapter_title, cls.get_entry_info(episode, is_upower_exclusive))

                    else:
                        part_title = episode["title"]

                        EpisodeInfo.add_item(chapter_title, cls.get_node_info(part_title, FormatUtils.format_episode_duration(episode, ParseType.Video), label = "分节"))

                        for page in episode["pages"]:
                            page["cover_url"] = cover_url
                            page["aid"] = aid
                            page["bvid"] = bvid
                            page["pubtime"] = pubtime
                            page["chapter_title"] = chapter_title
                            page["part_title"] = part_title

                            EpisodeInfo.add_item(part_title, cls.get_entry_info(page, is_upower_exclusive))

                    if cid == target_cid:
                        target_chapter_ttile = chapter_title

            if Config.Misc.episode_display_mode == EpisodeDisplayType.In_Section.value:
                cls.display_episodes_in_section(target_chapter_ttile)
        
        @classmethod
        def display_episodes_in_section(cls, chapter_title: list):
            for episode in EpisodeInfo.data.get("entries"):
                if episode.get("pid") == chapter_title:
                    EpisodeInfo.clear_episode_data()

                    EpisodeInfo.add_item("视频", episode)

                    break

        @staticmethod
        def get_node_info(title: str, duration: str = "", label: str = ""):
            return {
                "label": label,
                "title": title,
                "duration": duration,
                "pid": title,
                "entries": [],
                "type": "node"
            }
        
        @staticmethod
        def get_entry_info(episode: dict, is_upower_exclusive: bool = False):
            return {
                "number": 0,
                "title": episode.get("title", episode.get("part")),
                "cid": episode.get("cid", 0),
                "aid": episode.get("aid", 0),
                "bvid": episode.get("aid", ""),
                "pubtime": episode.get("pubtime", 0),
                "badge": "充电专属" if is_upower_exclusive else "",
                "duration": episode.get("duration", episode.get("arc", {"duration": 0}).get("duration", 0)),
                "cover_url": episode.get("cover_url", ""),
                "pid": "",
                "chapter_title": episode.get("chapter_title", ""),
                "part_title": episode.get("part_title", ""),
                "type": "item"
            }

    class Bangumi:
        pass

    class Cheese:
        pass