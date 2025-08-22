from utils.common.enums import ParseType
from utils.common.formatter.formatter import FormatUtils

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter

class FavList:
    target_bvid: str = ""
    season_dict: dict = {}

    @classmethod
    def parse_episodes(cls, info_json: dict, target_bvid: str, season_dict: dict):
        cls.target_bvid = target_bvid
        cls.season_dict = season_dict

        EpisodeInfo.clear_episode_data()

        cls.favlist_parser(info_json)

        Filter.episode_display_mode(reset = True)

    @classmethod
    def favlist_parser(cls, info_json: dict):
        for episode in info_json.get("episodes"):
            if episode.get("page") != 0:
                cls.video_parser(episode.copy())

            elif episode.get("ogv"):
                cls.bangumi_parser(episode.copy())

            else:
                EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info(episode.copy()))

    @classmethod
    def video_parser(cls, episode_info: dict):
        bvid = episode_info.get("bvid")
        title = episode_info.get("title")

        video_info = cls.season_dict["video"][bvid]

        if "ugc_season" in video_info:
            cls.video_ugc_season_collection_parser(video_info.copy())
        else:
            cls.video_pages_parser(video_info.copy(), title)

    @classmethod
    def video_pages_parser(cls, video_info: dict, part_title: str):
        pages_cnt = len(video_info["pages"])

        if pages_cnt > 1:
            page_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(part_title, label = "分P"))
        else:
            page_pid = EpisodeInfo.root_pid

        for page in video_info["pages"]:
            page["cover_url"] = video_info["pic"]
            page["aid"] = video_info["aid"]
            page["bvid"] = video_info["bvid"]
            page["pubtime"] = video_info["pubdate"]
            page["title"] = video_info["title"] if pages_cnt == 1 else page["part"]
            page["part_title"] = part_title if pages_cnt > 1 else ""

            EpisodeInfo.add_item(page_pid, cls.get_pages_entry_info(page.copy(), video_info))

    @classmethod
    def video_ugc_season_collection_parser(cls, season_info: dict):
        collection_title = season_info["ugc_season"]["title"]

        collection_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(collection_title, label = "合集"))

        for section in season_info["ugc_season"]["sections"]:
            section_title = section["title"]

            section_pid = EpisodeInfo.add_item(collection_pid, EpisodeInfo.get_node_info(section_title, label = "章节"))

            for episode in section.get("episodes"):
                cover_url = episode["arc"]["pic"]
                aid = episode["aid"]
                bvid = episode["bvid"]
                pubtime = episode["arc"]["pubdate"]

                if len(episode.get("pages")) == 1:
                    episode["page"] = episode["page"]["page"] if isinstance(episode["page"], dict) else episode["page"]
                    episode["cover_url"] = cover_url
                    episode["aid"] = aid
                    episode["bvid"] = bvid
                    episode["pubtime"] = pubtime
                    episode["section_title"] = section_title
                    episode["collection_title"] = collection_title

                    EpisodeInfo.add_item(section_pid, cls.get_ugc_entry_info(episode.copy(), season_info.copy()))
                else:
                    part_title = episode["title"]

                    page_pid = EpisodeInfo.add_item(section_pid, EpisodeInfo.get_node_info(part_title, episode["arc"]["duration"], label = "分节"))

                    for page in episode["pages"]:
                        page["cover_url"] = cover_url
                        page["aid"] = aid
                        page["bvid"] = bvid
                        page["pubtime"] = pubtime
                        page["section_title"] = section_title
                        page["part_title"] = part_title
                        page["collection_title"] = collection_title

                        EpisodeInfo.add_item(page_pid, cls.get_ugc_entry_info(page.copy(), season_info.copy()))

    @classmethod
    def bangumi_parser(cls, episode_info: dict):
        season_id = episode_info["ogv"]["season_id"]
        type_name = episode_info["ogv"]["type_name"]

        info_json = cls.season_dict["bangumi"][season_id]

        series_title = info_json["title"]

        bangumi_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(series_title, label = type_name))

        if info_json.get("episodes"):
            main_pid = EpisodeInfo.add_item(bangumi_pid, EpisodeInfo.get_node_info("正片", label = "章节"))

            cls.bangumi_episodes_parser(info_json["episodes"], main_pid, "正片", info_json)

        if "section" in info_json:
            cls.bangumi_section_parser(info_json, bangumi_pid)

    @classmethod
    def bangumi_episodes_parser(cls, episodes: list, pid: str, section_title: str, info_json: dict):
        for episode in episodes:
            episode["season_id"] = info_json["season_id"]
            episode["media_id"] = info_json["media_id"]
            episode["section_title"] = section_title

            EpisodeInfo.add_item(pid, cls.get_bangumi_entry_info(episode.copy(), info_json))

    @classmethod
    def bangumi_section_parser(cls, info_json: dict, pid: str):
        for section in info_json["section"]:
            section_title = section["title"]

            section_pid = EpisodeInfo.add_item(pid, EpisodeInfo.get_node_info(section_title, label = "章节"))

            cls.bangumi_episodes_parser(section["episodes"], section_pid, section_title, info_json)

    @classmethod
    def get_entry_info(cls, episode: dict):
        episode["cover_url"] = episode.get("cover")
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["up_name"] = episode["upper"]["name"]
        episode["up_mid"] = episode["upper"]["mid"]
        episode["current_episode"] = episode.get("bvid") == cls.target_bvid
        
        return EpisodeInfo.get_entry_info(episode)
    
    @classmethod
    def get_pages_entry_info(cls, episode: dict, info_json: dict):
        episode["title"] = episode.get("title", episode.get("part", ""))
        episode["duration"] = cls.get_duration(episode)
        episode["link"] = cls.get_link(episode)
        episode["type"] = ParseType.Video.value
        episode["zone"] = info_json.get("tname", "")
        episode["subzone"] = info_json.get("tname_v2", "")
        episode["up_name"] = info_json.get("owner", {"name": ""}).get("name", "")
        episode["up_mid"] = info_json.get("owner", {"mid": 0}).get("mid", 0)

        return EpisodeInfo.get_entry_info(episode)
    
    @classmethod
    def get_ugc_entry_info(cls, episode: dict, info_json: dict):
        episode["title"] = episode.get("title", episode.get("part", ""))
        episode["duration"] = cls.get_duration(episode)
        episode["link"] = cls.get_link(episode)
        episode["type"] = ParseType.Video.value
        episode["zone"] = info_json.get("tname", "")
        episode["subzone"] = info_json.get("tname_v2", "")
        episode["up_name"] = info_json.get("owner", {"name": ""}).get("name", "")
        episode["up_mid"] = info_json.get("owner", {"mid": 0}).get("mid", 0)

        return EpisodeInfo.get_entry_info(episode)
    
    @classmethod
    def get_bangumi_entry_info(cls, episode: dict, info_json: dict):
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

        return EpisodeInfo.get_entry_info(episode)

    @staticmethod
    def get_duration(episode: dict):
        if "duration" in episode:
            return episode["duration"]
        
        elif "arc" in episode:
            return episode["arc"]["duration"]
        
        else:
            return 0
        
    @staticmethod
    def get_link(episode: dict):
        page = episode.get("page", 0)

        if page > 1:
            return f"https://www.bilibili.com/video/{episode.get('bvid')}?p={episode.get('page')}"
        else:
            return f"https://www.bilibili.com/video/{episode.get('bvid')}"