from .tree import TreeItem, Attribute
from .list_base import ListEpisodeParserBase

class ListEpisodeParser(ListEpisodeParserBase):
    NODE_TYPE_KEY = "COLLECTION_LIST"

    def get_episode_list(self):
        return self.info_data["archives"]

    def get_node_title(self):
        if "title" in self.info_data["meta"]:
            return self.info_data["meta"]["title"]

        else:
            return self.info_data["meta"]["name"]

    def episode_data_parser(self):
        # 创建 episode_id
        if self.episode_id:
            return

        episode_data = self._init_episode_data()

        episode_data["collection_title"] = self.get_node_title()

    def build_item_data(self, episode_data: dict):
        return {
            "aid": episode_data["aid"],
            "bvid": episode_data["bvid"],
            "cover" : episode_data["pic"],
            "duration": self.get_episode_duration(episode_data),
            "number": self.episode_count,
            "pubtime": episode_data["pubdate"],
            "episode_id": self.episode_id,
            "title": episode_data["title"],
            "url": self.build_video_url(episode_data["bvid"])
        }

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        item.set_attribute(
            Attribute.COLLECTION_LIST_BIT | Attribute.COLLECTION_BIT
            | Attribute.VIDEO_BIT | Attribute.NEED_PARSE_BIT
        )
