from utils.common.enums import ParseType
from utils.common.formatter.formatter import FormatUtils

from utils.parse.episode.episode_v2 import EpisodeInfo

class Space:
    season_dict: dict = {}

    @classmethod
    def parse_episodes(cls, info_json: dict, bvid: str, season_dict: dict):
        EpisodeInfo.clear_episode_data()

        cls.season_dict = season_dict.copy()

        for episode in info_json.get("episodes"):
            if (season_id := episode.get("season_id")):
                if episode.get("is_avoided"):
                    cls.ugc_season_collection_parser(episode.copy(), season_id)
                else:
                    cls.ugc_season_parser(episode.copy(), episode.get("bvid"), season_id)
            else:
                EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_entry_info(episode.copy(), bvid))

    @classmethod
    def ugc_season_parser(cls, info_json: dict, target_bvid: str, season_id: int):
        season_info = cls.season_dict.get(season_id)

        for section in season_info["ugc_season"]["sections"]:
            for episode in section.get("episodes"):
                if (bvid := episode.get("bvid")) == target_bvid:
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

                        EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_ugc_entry_info(episode.copy(), info_json))
                    else:
                        part_title = episode["arc"]["title"]

                        page_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(part_title, episode["arc"]["duration"], label = "合集"))

                        for page in episode.get("pages"):
                            page["cover_url"] = cover_url
                            page["bvid"] = bvid
                            page["aid"] = aid
                            page["collection_title"] = part_title

                            EpisodeInfo.add_item(page_pid, cls.get_ugc_entry_info(page.copy(), info_json))

    @classmethod
    def ugc_season_collection_parser(cls, info_json: dict, season_id: int):
        season_info = cls.season_dict.get(season_id)

        collection_title = info_json["meta"]["title"]

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

                    EpisodeInfo.add_item(section_pid, cls.get_ugc_entry_info(episode.copy(), info_json))
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

                        EpisodeInfo.add_item(page_pid, cls.get_ugc_entry_info(page.copy(), info_json))

    @staticmethod
    def get_entry_info(episode: dict, bvid: str):
        episode["cover_url"] = episode.get("pic")
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["duration"] = FormatUtils.format_str_duration(episode.get("length"))
        episode["up_name"] = episode.get("author")
        episode["up_mid"] = episode.get("mid")
        episode["pubtime"] = episode.get("created")
        episode["type"] = ParseType.Video.value
        episode["current_episode"] = episode.get("bvid") == bvid

        return EpisodeInfo.get_entry_info(episode)

    @staticmethod
    def get_ugc_entry_info(episode: dict, info_json: dict):
        def get_duration():
            if "duration" in episode:
                return episode["duration"]
            
            elif "arc" in episode:
                return episode["arc"]["duration"]
            
            else:
                return 0
        
        episode["title"] = episode.get("title", episode.get("part", ""))
        episode["duration"] = get_duration()
        episode["type"] = ParseType.Video.value
        episode["up_name"] = info_json.get("author")
        episode["up_mid"] = info_json.get("mid")
        #episode["current_episode"] = info_json.get("aid") == episode.get("aid")

        return EpisodeInfo.get_entry_info(episode)