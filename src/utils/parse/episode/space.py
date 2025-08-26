from utils.common.enums import ParseType, TemplateType

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter
from utils.parse.episode.video import Video
from utils.parse.episode.cheese import Cheese

class Space:
    parent_title: str = ""
    video_info_dict: dict = {}
    cheese_info_dict: dict = {}

    @classmethod
    def parse_episodes(cls, info_json: dict, bvid: str, video_info_dict: dict, cheese_info_dict: dict, parent_title: str):
        cls.parent_title = parent_title
        Video.parent_title = parent_title

        EpisodeInfo.clear_episode_data()

        cls.video_info_dict = video_info_dict.copy()
        cls.cheese_info_dict = cheese_info_dict.copy()

        for episode in info_json.get("episodes"):
            bvid = episode.get("bvid")

            if (season_id := episode.get("season_id")):
                if episode.get("is_lesson_video"):
                    season_info = cls.cheese_info_dict.get(season_id)

                    Cheese.parse_episodes(season_info, parent_title = parent_title)
                else:
                    season_info = cls.video_info_dict.get(season_id)

                    if episode.get("is_avoided"):
                        Video.ugc_season_parser(season_info.copy())
                    else:
                        cls.ugc_season_pages_parser(season_info.copy(), bvid)
            else:
                Video.pages_parser(cls.video_info_dict.get(bvid).copy())

        Filter.episode_display_mode(reset = True)

    @classmethod
    def ugc_season_pages_parser(cls, season_info: dict, target_bvid: str):
        for section in season_info["ugc_season"]["sections"]:
            for episode in section.get("episodes"):
                if (bvid := episode.get("bvid")) == target_bvid:
                    cover_url = episode["arc"]["pic"]
                    aid = episode["aid"]
                    bvid = episode["bvid"]
                    pubtime = episode["arc"]["pubdate"]

                    if len(episode.get("pages")) == 1:
                        episode["cover_url"] = cover_url
                        episode["aid"] = aid
                        episode["bvid"] = bvid
                        episode["pubtime"] = pubtime

                        EpisodeInfo.add_item(EpisodeInfo.root_pid, cls.get_ugc_entry_info(episode.copy(), season_info, multiple = False))
                    else:
                        part_title = episode["arc"]["title"]

                        page_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(part_title, episode["arc"]["duration"], label = "合集"))

                        for page in episode.get("pages"):
                            page["cover_url"] = cover_url
                            page["bvid"] = bvid
                            page["aid"] = aid
                            page["collection_title"] = part_title

                            EpisodeInfo.add_item(page_pid, cls.get_ugc_entry_info(page.copy(), season_info, multiple = True))

    @classmethod
    def get_ugc_entry_info(cls, episode: dict, info_json: dict, multiple: bool):
        episode["title"] = episode.get("title", episode.get("part", ""))
        episode["duration"] = cls.get_duration(episode)
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["type"] = ParseType.Video.value
        episode["zone"] = info_json.get("tname", "")
        episode["subzone"] = info_json.get("tname_v2", "")
        episode["up_name"] = info_json.get("owner", {"name": ""}).get("name", "")
        episode["up_mid"] = info_json.get("owner", {"mid": 0}).get("mid", 0)
        episode["template_type"] = TemplateType.Video_Collection.value if multiple else TemplateType.Video_Normal.value
        episode["parent_title"] = cls.parent_title

        return EpisodeInfo.get_entry_info(episode)
    
    @staticmethod
    def get_duration(episode: dict):
        if "duration" in episode:
            return episode["duration"]
        
        elif "arc" in episode:
            return episode["arc"]["duration"]
        
        else:
            return 0