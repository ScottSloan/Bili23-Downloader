from ...common.translator import Translator

from .tree import TreeItem, Attribute
from .base import EpisodeParserBase

class HistoryEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str):
        super().__init__()

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self, update_episode_list = True):
        self._init_episode_data()

        node = self.list_parser()

        if update_episode_list:
            self.update_episode_list(node)

        return node

    def list_parser(self):
        node_data = {
            "number": Translator.EPISODE_TYPE("HISTORY"),
            "title": ""
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        if self.info_data.get("list") is None:
            return root_node

        for episode in self.info_data.get("list"):
            self.episode_count += 1

            item_data = {
                "badge": self.get_episode_badge(episode),
                "bvid": episode["history"]["bvid"],
                "cid": episode["history"]["cid"],
                "cover" : episode["cover"],
                "duration": self.get_episode_duration(episode),
                "ep_id": episode["history"]["epid"],
                "episode_id": self.episode_id,
                "number": self.episode_count,
                "viewtime": episode["view_at"],
                "title": self.get_episode_title(episode),
                "url": "https://www.bilibili.com/video/" + episode["history"]["bvid"],
                "expired": episode["duration"] == 0
            }

            item = TreeItem(item_data)

            self.set_episode_attribute(episode, item)

            root_node.add_child(item)

        return root_node

    def get_episode_badge(self, episode_data: dict):
        if episode_data.get("duration") == 0:            
            return Translator.TIP_MESSAGES("EXPIRED")
        else:
            return episode_data["badge"]
        
    def get_episode_title(self, episode_data: dict):
        if episode_data["history"]["business"] == "pgc":
            return "{} - {}".format(episode_data["title"], episode_data["long_title"])
        else:
            return episode_data["title"]
        
    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        match episode_data["history"]["business"]:
            case "archive":
                item.set_attribute(Attribute.VIDEO_BIT)

            case "pgc":
                item.set_attribute(Attribute.BANGUMI_BIT)

            case "cheese":
                item.set_attribute(Attribute.CHEESE_BIT)

        item.set_attribute(Attribute.HISTORY_BIT | Attribute.NEED_PARSE_BIT)

    def get_node_title(self):
        return ""