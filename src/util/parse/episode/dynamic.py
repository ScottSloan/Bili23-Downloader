from ...common.translator import Translator
from ...common.signal_bus import signal_bus
from ...common.enum import ParserType
from ...common.config import config

from ...download.task.manager import task_manager
from ...thread.pool import GlobalThreadPoolTask

from .tree import TreeItem, Attribute
from .base import EpisodeParserBase

from typing import List

class DynamicEpisodeParser(EpisodeParserBase):
    # 不同于其他类型的解析器，动态解析器支持实时更新剧集列表，无需等待所有节点解析完成再更新界面
    def __init__(self, info_data: dict, category_name: str, kwargs: dict = {}):
        super().__init__(**kwargs)

        self.info_data = info_data
        self.category_name = category_name

        self.parser = None
        self.root_node_initialized = False

        # 已投递的节点总数。树本身归 GUI 线程所有，这里不能通过 root_node.count() 去数
        self.node_count = 0

    def init_root_node(self, title):
        node_data = {
            "number": Translator.EPISODE_TYPE(self.category_name),
            "title": title,
        }

        self.root_node = TreeItem(node_data)
        self.root_node.set_attribute(Attribute.TREE_NODE_BIT)

        # 只在这里发出一次全量更新，建立一棵空的树。
        # 自此之后 root_node 归 GUI 线程所有，解析线程只能通过 append_nodes 追加内容
        self.update_episode_list(self.root_node)

        return self.root_node

    def append_nodes(self, nodes: List[TreeItem]):
        """
        把新解析出的节点交给 GUI 线程挂到解析列表上

        绝不能在解析线程里直接改动 root_node：这棵树同时被 GUI 线程的 ParseModel 使用，
        在后台增删子节点会让 QTreeView 缓存的行布局与模型脱节，
        随后视图访问模型时就会越界，进程直接被访问违例终止，且不留任何 Python 栈。
        """
        if not nodes:
            return

        self.node_count += len(nodes)

        # 传出去的是节点本身而非引用视图，投递后解析线程不再持有它们
        signal_bus.parse.append_parse_list_nodes.emit(list(nodes))

    def init_episode_parser(self, parser_type: ParserType):
        # 根据不同的 parser_type 初始化对应的剧集数据解析器
        _empty_info_data = {"data": {}}

        match parser_type:
            case ParserType.VIDEO:
                from .video import VideoEpisodeParser

                parser = VideoEpisodeParser(_empty_info_data, self.category_name)

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

            case ParserType.COLLECTION_LIST:
                from .list import ListEpisodeParser

                parser = ListEpisodeParser(_empty_info_data, self.category_name)

        self.parser = parser

    def update_page_node(self, info_data: dict):
        self.parser.info_data = info_data["data"]

        if not self.root_node_initialized:
            self.init_root_node(self.parser.get_node_title())

            self.root_node_initialized = True

        node = self.parser.parse(update_episode_list = False)

        # 根据设置决定是否自动添加到下载列表
        if config.get(config.auto_add_to_download_list):
            GlobalThreadPoolTask.run_func(task_manager.create, node.get_all_children(to_dict = True), False)

        # 去除 raw_node 最外层的根节点，只把其子节点交给 GUI 线程挂载
        self.append_nodes(node.children)

        return self.parser.episode_count

    def update(self, title: str, cid: int):
        node_data = {
            "episode_id": self.episode_id,
            "badge": "充电专属" if self.info_data["is_upower_exclusive"] else "",
            "aid": self.info_data["aid"],
            "bvid": self.info_data["bvid"],
            "cid": cid,
            "cover": self.info_data["pic"],
            "duration": 0,
            "number": self.node_count + 1,
            "pubtime": self.info_data["pubdate"],
            "title": title,
            "related_titles": {
                "collection_title": self.info_data["title"],
            },
            "url": "https://www.bilibili.com/video/{bvid}".format(bvid = self.info_data["bvid"])
        }

        child_node = TreeItem(node_data)
        child_node.set_attribute(Attribute.INTERACTIVE_BIT | Attribute.VIDEO_BIT)

        self.append_nodes([child_node])