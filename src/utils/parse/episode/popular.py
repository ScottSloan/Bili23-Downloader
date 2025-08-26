from utils.common.enums import ParseType, TemplateType

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter

class Popular:
    target_cid: int = 0

    @classmethod
    def parse_episodes(cls, info_json: dict, target_cid: int):
        cls.target_cid = target_cid
        EpisodeInfo.clear_episode_data()

        parent_title = info_json["config"]["label"]

        parent_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(parent_title, label = "热榜"))

        for episode in info_json["list"]:
            episode["parent_title"] = parent_title
            
            EpisodeInfo.add_item(parent_pid, cls.get_entry_info(episode.copy()))

        Filter.episode_display_mode(reset = True)

    @classmethod
    def get_entry_info(cls, episode: dict):
        episode["pubtime"] = episode["pubdate"]
        episode["link"] = f"https://www/bilibili.com/video/{episode.get('bvid')}"
        episode["cover_url"] = episode["pic"]
        episode["type"] = ParseType.Video.value
        episode["zone"] = episode["tname"]
        episode["subzone"] = episode["tnamev2"]
        episode["up_name"] = episode["owner"]["name"]
        episode["up_mid"] = episode["owner"]["mid"]
        episode["template_type"] = TemplateType.Video_Normal.value

        return EpisodeInfo.get_entry_info(episode)