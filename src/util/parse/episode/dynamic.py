from ...common.translator import Translator
from ...common.enum import ParserType

from .tree import TreeItem, Attribute
from .base import EpisodeParserBase

class DynamicEpisodeParser(EpisodeParserBase):
    # 不同于其他类型的解析器，动态解析器支持实时更新剧集列表，无需等待所有节点解析完成再更新界面
    def __init__(self, info_data: dict, category_name: str, kwargs: dict = {}):
        super().__init__(**kwargs)

        self.info_data = info_data
        self.category_name = category_name

        self.parser = None

    def init_root_node(self, title):
        node_data = {
            "number": Translator.EPISODE_TYPE(self.category_name),
            "title": title,
        }

        self.root_node = TreeItem(node_data)
        self.root_node.set_attribute(Attribute.TREE_NODE_BIT)

        self.update_episode_list(self.root_node)

        return self.root_node

    def _video_episode_data_parser(self):
        self.init_root_node(self.info_data["title"])

        super()._video_episode_data_parser()

    def init_episode_parser(self, parser_type: ParserType):
        # 根据不同的 parser_type 初始化对应的剧集数据解析器
        _empty_info_data = {"data": {}}

        match parser_type:
            case ParserType.FAVLIST:
                from .favlist import FavlistEpisodeParser

                parser = FavlistEpisodeParser(_empty_info_data, self.category_name)

            case ParserType.SPACE:
                from .space import SpaceEpisodeParser

                parser = SpaceEpisodeParser(_empty_info_data, self.category_name)

            case ParserType.HISTORY:
                from .history import HistoryEpisodeParser

                parser = HistoryEpisodeParser(_empty_info_data, self.category_name)

            case ParserType.WATCH_LATER:
                from .watch_later import WatchLaterEpisodeParser

                parser = WatchLaterEpisodeParser(_empty_info_data, self.category_name)

        self.parser = parser

    def update_page_node(self, info_data: dict):
        self.parser.info_data = info_data["data"]

        node = self.parser.parse()

        # 去除 raw_node 最外层的根节点，直接返回其子节点列表
        for child in node.children:
            self.root_node.add_child(child)

        self.update_episode_list(self.root_node)

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