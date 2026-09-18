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
                # 本期名称。每周必看的条目从不二次解析，不会有人来盖它 ——
                # 它只是「来源列表名称」而不是结构上级，所以归 source_title
                "source_title": self.get_node_title()
            },
            "url": self.build_video_url(episode_data["bvid"])
        }

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        item.set_attribute(Attribute.VIDEO_BIT | Attribute.WEEKLY_BIT)
