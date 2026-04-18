from util.common import Translator

from .tree import TreeItem, EpisodeData, Attribute
from .base import EpisodeParserBase

class FavlistEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str):
        super().__init__()

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self):
        self.episode_data_parser()

        node = self.medias_parser()

        self.update_episode_list(node)

    def medias_parser(self):
        favlist_title = self.info_data["info"]["title"]
        node_data = {
            "number": Translator.EPISODE_TYPE("FAVORITES"),
            "title": favlist_title
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        episode_count = 0

        if self.info_data.get("medias") is None:
            return root_node

        for episode in self.info_data.get("medias"):
            episode_count += 1

            item_data = {
                "badge": self.get_episode_badge(episode),
                "bvid": episode["bvid"],
                "cover" : episode["cover"],
                "duration": self.get_episode_duration(episode),
                "ep_id": episode["id"],
                "episode_id": self.episode_id,
                "number": episode_count,
                "pubtime": episode["pubtime"],
                "favtime": episode["fav_time"],
                "title": self.get_episode_title(episode)
            }

            item = TreeItem(item_data)

            self.set_episode_attribute(episode, item)

            root_node.add_child(item)

        return root_node

    def episode_data_parser(self):
        self.episode_id = EpisodeData.add_episode()
        episode_data = EpisodeData.get_episode_data(self.episode_id)

        episode_data["favorites_name"] = self.info_data["info"]["title"]
        episode_data["favorites_id"] = self.info_data["info"]["id"]
        episode_data["favorites_owner"] = self.info_data["info"]["upper"]["name"]
        episode_data["favorites_owner_id"] = self.info_data["info"]["upper"]["mid"]

    def get_episode_badge(self, episode_data: dict):
        if episode_data.get("ogv"):
            return episode_data["ogv"]["type_name"]
        
        return ""
    
    def get_episode_title(self, episode_data: dict):
        if episode_data.get("ogv"):
            return "{title} - {intro}".format(
                title = episode_data["title"],
                intro = episode_data["intro"]
            )
        
        return episode_data["title"]

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        if episode_data.get("ogv"):
            item.set_attribute(Attribute.BANGUMI_BIT)
        else:
            item.set_attribute(Attribute.VIDEO_BIT)

        item.set_attribute(Attribute.FAVLIST_BIT | Attribute.NEED_PARSE_BIT)
