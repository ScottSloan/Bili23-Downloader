from ...common.translator import Translator

from .tree import TreeItem, Attribute
from .base import EpisodeParserBase

class AudioEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str):
        super().__init__()

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self):
        if "data" not in self.info_data:
            self.info_data["data"] = [
                self.info_data.copy()
            ]

        node = self.audio_menu_parser()
        
        self.update_episode_list(node, None)

    def audio_menu_parser(self):
        menu_title = self.info_data.get("menu_title", "")
        node_data = {
            "number": Translator.EPISODE_TYPE("AUDIO"),
            "title": menu_title
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        for episode in self.info_data["data"]:
            self.episode_count += 1

            episode_item_data = {
                "author": episode["author"],
                "cover": episode["cover"],
                "duration": episode["duration"],
                "sid": episode["statistic"]["sid"],
                "number": self.episode_count,
                "pubtime": episode["passtime"],
                "title": episode["title"],
                "related_titles": {
                    "parent_title": menu_title
                },
                "url": "https://www.bilibili.com/audio/au{sid}".format(sid = episode["statistic"]["sid"])
            }

            episode_item = TreeItem(episode_item_data)
            episode_item.set_attribute(Attribute.AUDIO_BIT)

            root_node.add_child(episode_item)

        return root_node
