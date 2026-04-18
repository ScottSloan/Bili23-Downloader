from .tree import TreeItem, EpisodeData, Attribute
from .base import EpisodeParserBase

class PopularEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str):
        super().__init__()

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self):
        self.episode_parser()

        node = self.list_parser()

        self.update_episode_list(node)

    def list_parser(self):
        weekly_title = self.info_data["config"]["label"]
        node_data = {
            "number": "每周必看",
            "title": weekly_title
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        episode_count = 0

        for episode in self.info_data["list"]:
            episode_count += 1

            item_data = {
                "aid": episode["aid"],
                "bvid": episode["bvid"],
                "cid": episode["cid"],
                "cover": episode["pic"],
                "duration": self.get_episode_duration(episode),
                "number": episode_count,
                "pubtime": episode["pubdate"],
                "episode_id": self.episode_id,
                "title": episode["title"],
                "related_titles": {
                    "collection_title": weekly_title
                },
                "url": "https://www.bilibili.com/video/{bvid}".format(bvid = episode["bvid"])
            }

            item = TreeItem(item_data)
            item.set_attribute(Attribute.VIDEO_BIT | Attribute.POPULAR_BIT)

            root_node.add_child(item)

        return root_node

    def episode_parser(self):
        self.episode_id = EpisodeData.add_episode()
