from ...common.translator import Translator

from .tree import TreeItem, Attribute
from .base import EpisodeParserBase

class SpaceEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str):
        super().__init__()

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self, update_episode_list = True):
        self.episode_data_parser()

        node = self.vlist_parser()

        if update_episode_list:
            self.update_episode_list(node)

        return node

    def vlist_parser(self):
        node_data = {
            "number": Translator.EPISODE_TYPE("PROFILE"),
            "title": self.get_node_title()
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        for episode in self.info_data["list"]["vlist"]:
            self.episode_count += 1

            item_data = {
                "aid": episode["aid"],
                "badge": self.get_episode_badge(episode),
                "bvid": episode["bvid"],
                "cover" : episode["pic"],
                "duration": self.get_episode_duration(episode),
                "ep_id": episode.get("season_id", 0),
                "episode_id": self.episode_id,
                "number": self.episode_count,
                "pubtime": episode["created"],
                "title": episode["title"],
                "url": "https://www.bilibili.com/video/{bvid}".format(bvid = episode["bvid"])
            }

            item = TreeItem(item_data)
            
            self.set_episode_attribute(episode, item)

            root_node.add_child(item)

        return root_node
    
    def episode_data_parser(self):
        if self.episode_id:
            return
        
        episode_data = self._init_episode_data()

        episode_data["space_owner"] = self.info_data["info"]["name"]
        episode_data["space_owner_id"] = self.info_data["info"]["mid"]

    def get_episode_badge(self, episode_data: dict):
        if episode_data["is_charging_arc"]:
            return "充电专属"
        
        elif episode_data["is_lesson_video"]:
            return "课程"
        
        elif episode_data["is_union_video"]:
            return "合作"
        
        return ""
        
    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        if episode_data["is_lesson_video"]:
            item.set_attribute(Attribute.CHEESE_BIT)
        
        else:
            item.set_attribute(Attribute.VIDEO_BIT)

        item.set_attribute(Attribute.SPACE_BIT | Attribute.NEED_PARSE_BIT)

    def get_node_title(self):
        return self.info_data["info"]["name"]
