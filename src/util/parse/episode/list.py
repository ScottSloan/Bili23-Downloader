from .tree import TreeItem, EpisodeData, Attribute
from .base import EpisodeParserBase

class ListEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str):
        super().__init__()

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self):
        self.episode_data_parser()

        node = self.seasons_archives_list_parser()

        self.update_episode_list(node)

    def seasons_archives_list_parser(self):
        collection_title = self.get_node_title()
        node_data = {
            "number": "合集",
            "title": collection_title
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        episode_count = 0

        for episode in self.info_data["archives"]:
            episode_count += 1

            item_data = {
                "aid": episode["aid"],
                "bvid": episode["bvid"],
                "cover" : episode["pic"],
                "duration": self.get_episode_duration(episode),
                "number": episode_count,
                "pubtime": episode["pubdate"],
                "episode_id": self.episode_id,
                "title": episode["title"],
                "url": "https://www.bilibili.com/video/{bvid}".format(bvid = episode["bvid"])
            }

            item = TreeItem(item_data)
            item.set_attribute(Attribute.COLLECTION_LIST_BIT | Attribute.VIDEO_BIT | Attribute.NEED_PARSE_BIT)

            root_node.add_child(item)
        
        return root_node
    
    def episode_data_parser(self):
        # 创建 episode_id
        self.episode_id = EpisodeData.add_episode()
        episode_data = EpisodeData.get_episode_data(self.episode_id)

        episode_data["collection_title"] = self.get_node_title()

    def get_node_title(self):
        if "title" in self.info_data["meta"]:
            return self.info_data["meta"]["title"]
        
        else:
            return self.info_data["meta"]["name"]
    