from utils.common.enums import ParseType

from utils.parse.episode.episode_v2 import EpisodeInfo

class Popular:
    @classmethod
    def parse_episodes(cls, info_json: dict, cid: int):
        EpisodeInfo.clear_episode_data()

        section_title = info_json["config"]["label"]

        section_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(section_title, label = "章节"))

        for episode in info_json["list"]:
            episode["section_title"] = section_title
            
            EpisodeInfo.add_item(section_pid, cls.get_entry_info(episode.copy(), cid))

    @staticmethod
    def get_entry_info(episode: dict, cid: int):
        episode["pubtime"] = episode.get("pubdate")
        episode["link"] = f"https://www/bilibili.com/video/{episode.get('bvid')}"
        episode["cover_url"] = episode.get("pic")
        episode["type"] = ParseType.Video.value
        episode["current_episode"] = episode.get("cid") == cid

        return EpisodeInfo.get_entry_info(episode)