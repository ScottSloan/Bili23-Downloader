from util.common import Translator

from .tree import TreeItem, EpisodeData, Attribute
from .base import EpisodeParserBase

class WatchLaterEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str):
        super().__init__()

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self):
        self.episode_data_parser()

        node = self.list_parser()

        self.update_episode_list(node)

    def list_parser(self):
        node_data = {
            "number": Translator.EPISODE_TYPE("WATCH_LATER"),
            "title": ""
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        episode_count = 0

        if self.info_data.get("list") is None:
            return root_node

        for episode in self.info_data.get("list"):
            episode_count += 1

            item_data = {
                "aid": episode["aid"],
                "badge": self.get_episode_badge(episode),
                "bvid": episode["bvid"],
                "cid": episode["cid"],
                "cover" : episode["pic"],
                "duration": self.get_episode_duration(episode),
                "ep_id": self.get_ep_id(episode),
                "episode_id": self.episode_id,
                "number": episode_count,
                "pubtime": episode["pubdate"],
                "favtime": episode["add_at"],
                "title": episode["title"],
                "url": "https://www.bilibili.com/video/" + episode["bvid"],
            }

            item = TreeItem(item_data)

            self.set_episode_attribute(episode, item)

            root_node.add_child(item)

        return root_node
            
    def episode_data_parser(self):
        self.episode_id = EpisodeData.add_episode()

    def get_episode_badge(self, episode_data: dict):
        if episode_data.get("bangumi"):
            return episode_data["pgc_label"]
        
        return ""
    
    def get_ep_id(self, episode_data: dict):
        if episode_data.get("bangumi"):
            return episode_data["bangumi"]["ep_id"]
        
        return ""

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        if episode_data.get("bangumi"):
            item.set_attribute(Attribute.BANGUMI_BIT)
        else:
            item.set_attribute(Attribute.VIDEO_BIT)

        item.set_attribute(Attribute.WATCH_LATER_BIT | Attribute.NEED_PARSE_BIT)
