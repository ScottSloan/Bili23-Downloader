from util.parse.episode.tree import TreeNode, TreeItem, Attribute
from util.parse.episode.base import EpisodeParserBase

class PopularEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict):
        super().__init__()

        self.info_data = info_data["data"]

    def parse(self):
        node = self.list_parser()

        self.update_episode_list(node.to_dict())

    def list_parser(self):
        weekly_title = self.info_data["config"]["label"]
        node_data = {
            "number": "每周必看",
            "title": weekly_title
        }

        root_node = TreeNode(node_data)

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
                "title": episode["title"],
                "related_titles": {
                    "weekly_title": weekly_title
                },
                "url": "https://www.bilibili.com/video/{bvid}".format(bvid = episode["bvid"])
            }

            item = TreeItem(item_data)
            item.set_attribute(Attribute.VIDEO_BIT | Attribute.POPULAR_BIT)

            root_node.add_child(item)

        return root_node
