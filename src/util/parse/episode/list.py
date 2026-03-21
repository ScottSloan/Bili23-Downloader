from util.parse.episode.tree import TreeItem, Attribute
from util.parse.episode.base import EpisodeParserBase

class ListEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict):
        super().__init__()

        self.info_data = info_data["data"]

    def parse(self):
        node = self.seasons_archives_list_parser()

        self.update_episode_list(node)

    def seasons_archives_list_parser(self):
        collection_title = self.get_node_title()
        node_data = {
            "number": "合集系列",
            "title": collection_title
        }

        root_node = TreeItem(node_data)

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
                "title": episode["title"],
                "related_titles": {
                    "collection_title": collection_title
                },
                "url": "https://www.bilibili.com/video/{bvid}".format(bvid = episode["bvid"])
            }

            item = TreeItem(item_data)
            item.set_attribute(Attribute.VIDEO_BIT)

            root_node.add_child(item)
        
        return root_node
    
    def get_node_title(self):
        if "title" in self.info_data["meta"]:
            return self.info_data["meta"]["title"]
        
        else:
            return self.info_data["meta"]["name"]
    