from ...common.translator import Translator

from .tree import TreeItem, EpisodeData, Attribute
from .base import EpisodeParserBase

class DynamicEpisodeParser(EpisodeParserBase):
    # 不同于其他类型的解析器，动态解析器支持实时更新剧集列表，无需等待所有节点解析完成再更新界面
    def __init__(self, info_data: dict, category_name: str, kwargs: dict = {}):
        super().__init__(**kwargs)

        self.info_data = info_data
        self.category_name = category_name

        self.root_node: TreeItem = self.init_root_node(self.info_data["title"])

    def init_root_node(self, title):
        node_data = {
            "number": Translator.EPISODE_TYPE(self.category_name),
            "title": title,
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        self.update_episode_list(root_node)

        return root_node

    def video_episode_data_parser(self):
        # 创建 episode_id
        self.episode_id = EpisodeData.add_episode()
        episode_data = EpisodeData.get_episode_data(self.episode_id)

        if self.target_episode_data_id:
            data = EpisodeData.get_episode_data(self.target_episode_data_id)

            episode_data.update(data)

        # 简介
        episode_data["description"] = self.info_data.get("desc", "")
        # 分区信息
        episode_data["tid"] = self.info_data.get("tid", 0)
        episode_data["tid_v2"] = self.info_data.get("tid_v2", 0)
        # UP 主信息
        episode_data["uploader"] = self.info_data["owner"]["name"]
        episode_data["uploader_uid"] = self.info_data["owner"]["mid"]
        episode_data["uploader_face"] = self.info_data["owner"]["face"]

    def update(self, title: str, cid: int):
        node_data = {
            "episode_id": self.episode_id,
            "aid": self.info_data["aid"],
            "bvid": self.info_data["bvid"],
            "cid": cid,
            "cover": self.info_data["pic"],
            "duration": 0,
            "number": self.root_node.count() + 1,
            "pubtime": self.info_data["pubdate"],
            "title": title,
            "related_titles": {
                "collection_title": self.info_data["title"],
            },
            "url": "https://www.bilibili.com/video/{bvid}".format(bvid = self.info_data["bvid"])
        }

        child_node = TreeItem(node_data)
        child_node.set_attribute(Attribute.INTERACTIVE_BIT | Attribute.VIDEO_BIT)

        self.root_node.add_child(child_node)

        self.update_episode_list(self.root_node)