from .tree import TreeItem, Attribute
from .list_base import ListEpisodeParserBase

class PopularEpisodeParser(ListEpisodeParserBase):
    NODE_TYPE_KEY = "WEEKLY"

    def get_episode_list(self):
        return self.info_data["list"]

    def get_node_title(self):
        return self.info_data["config"]["label"]

    def episode_data_parser(self):
        self._init_episode_data()

    def build_item_data(self, episode_data: dict):
        return {
            "aid": episode_data["aid"],
            "bvid": episode_data["bvid"],
            "cid": episode_data["cid"],
            "cover": episode_data["pic"],
            "duration": self.get_episode_duration(episode_data),
            "number": self.episode_count,
            "pubtime": episode_data["pubdate"],
            "episode_id": self.episode_id,
            "title": episode_data["title"],
            "related_titles": {
                # 每周必看没有单独的父级标题，用本期的名称充当
                "parent_title": self.get_node_title()
            },
            "url": self.build_video_url(episode_data["bvid"])
        }

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        item.set_attribute(Attribute.VIDEO_BIT | Attribute.WEEKLY_BIT)
