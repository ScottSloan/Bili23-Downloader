from utils.config import Config
from utils.common.enums import ParseType, EpisodeDisplayType

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter

class Video:
    target_cid: int = 0

    @classmethod
    def parse_episodes(cls, info_json: dict):
        cls.target_cid = info_json.get("cid")
        EpisodeInfo.parser = cls

        EpisodeInfo.clear_episode_data()

        match EpisodeDisplayType(Config.Misc.episode_display_mode):
            case EpisodeDisplayType.Single:
                cls.pages_parser(info_json)

            case EpisodeDisplayType.In_Section | EpisodeDisplayType.All:
                if "ugc_season" in info_json:
                    cls.ugc_season_parser(info_json)
                else:
                    cls.pages_parser(info_json)

        Filter.episode_display_mode(reset = not (len(info_json["pages"]) > 1 or "ugc_season" in info_json) and EpisodeDisplayType(Config.Misc.episode_display_mode) == EpisodeDisplayType.In_Section)

    @classmethod
    def pages_parser(cls, info_json: dict):
        pages_cnt = len(info_json["pages"])

        for page in info_json["pages"]:
            page["cover_url"] = info_json["pic"]
            page["aid"] = info_json["aid"]
            page["bvid"] = info_json["bvid"]
            page["pubtime"] = info_json["pubdate"]
            page["title"] = info_json["title"] if pages_cnt == 1 else page["part"]

            EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info(page.copy(), info_json))

    @classmethod
    def ugc_season_parser(cls, info_json: dict):
        for section in info_json["ugc_season"]["sections"]:
            collection_title = info_json["ugc_season"]["title"]
            section_title = section["title"]

            section_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(section_title, label = "章节"))

            for episode in section["episodes"]:
                cover_url = episode["arc"]["pic"]
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

                    EpisodeInfo.add_item(section_pid, cls.get_entry_info(episode.copy(), info_json))

                else:
                    part_title = episode["title"]

                    part_pid = EpisodeInfo.add_item(section_pid, EpisodeInfo.get_node_info(part_title, episode["arc"]["duration"], label = "分节"))

                    for page in episode["pages"]:
                        page["cover_url"] = cover_url
                        page["aid"] = aid
                        page["bvid"] = bvid
                        page["pubtime"] = pubtime
                        page["section_title"] = section_title
                        page["part_title"] = part_title
                        page["collection_title"] = collection_title

                        EpisodeInfo.add_item(part_pid, cls.get_entry_info(page.copy(), info_json))

                cls.update_target_section_title(episode, section_title)

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
    
    @classmethod
    def update_target_section_title(cls, episode: dict, section_title: str):
        if episode.get("cid") == cls.target_cid:
            cls.target_section_title = section_title

    @classmethod
    def condition_single(cls, episode: dict):
        return episode.get("item_type") == "item" and episode.get("cid") == cls.target_cid
    
    @classmethod
    def condition_in_section(cls, episode: dict):
        return episode.get("item_type") == "node" and episode.get("title") == cls.target_section_title