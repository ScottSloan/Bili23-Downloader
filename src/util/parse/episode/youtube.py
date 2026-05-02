from util.parse.episode.tree import TreeItem, EpisodeData, Attribute
from util.parse.episode.base import EpisodeParserBase

class YouTubeEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str, kwargs: dict = {}):
        super().__init__(**kwargs)
        self.info_data = info_data
        self.category_name = category_name

    def parse(self):
        self.episode_data_parser()

        entries = self.info_data.get("entries", [])

        if entries:
            node = self.playlist_parser(entries)
        else:
            node = self.single_parser()

        if self.target_episode_info:
            return node
        else:
            episode_data = ("cid", self.info_data.get("id", ""))
            self.update_episode_list(node, episode_data)

    def single_parser(self):
        node_data = {
            "number": self.category_name,
            "title": ""
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        item_data = {
            "episode_id": self.episode_id,
            "aid": 0,
            "badge": "",
            "bvid": self.info_data.get("id", ""),
            "cid": self.info_data.get("id", ""),
            "cover": self.info_data.get("thumbnail", ""),
            "duration": int(self.info_data.get("duration", 0)),
            "number": 1,
            "pubtime": int(self.info_data.get("timestamp", 0)),
            "title": self.info_data.get("title", ""),
            "url": self.info_data.get("webpage_url", ""),
            "uploader": self.info_data.get("uploader", ""),
            "uploader_uid": 0
        }

        item = TreeItem(item_data)
        self.set_attribute(item, Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)

        root_node.add_child(item)

        return root_node

    def playlist_parser(self, entries: list):
        playlist_title = self.info_data.get("title", "Playlist")
        root_node_data = {
            "number": "播放列表",
            "title": playlist_title
        }

        root_node = TreeItem(root_node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        for idx, entry in enumerate(entries, 1):
            item_data = {
                "episode_id": self.episode_id,
                "aid": 0,
                "badge": "",
                "bvid": entry.get("id", ""),
                "cid": entry.get("id", ""),
                "cover": entry.get("thumbnail", ""),
                "duration": int(entry.get("duration", 0)),
                "number": idx,
                "pubtime": int(entry.get("timestamp", 0)),
                "title": entry.get("title", ""),
                "url": entry.get("webpage_url", ""),
                "uploader": entry.get("uploader", ""),
                "uploader_uid": 0
            }

            item = TreeItem(item_data)
            self.set_attribute(item, Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)

            root_node.add_child(item)

        return root_node
