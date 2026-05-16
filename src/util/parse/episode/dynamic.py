from util.common import Translator

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

    def update(self, title: str):
        node_data = {
            "episode_id": 0,
            "number": self.root_node.count() + 1,
            "title": title,
            "duration": 0,
            "pubtime": 0
        }

        child_node = TreeItem(node_data)

        self.root_node.add_child(child_node)

        self.update_episode_list(self.root_node)