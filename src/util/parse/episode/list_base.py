from ...common.translator import Translator

from .tree import TreeItem, Attribute
from .base import EpisodeParserBase


class ListEpisodeParserBase(EpisodeParserBase):
    """
    平铺列表类解析结果的共用骨架。

    个人空间、收藏夹、历史记录、稍后再看、每周必看、合集这六类内容，接口返回的
    都是一个平铺的视频列表，转成解析列表时的处理完全一样：建一个树节点、遍历
    列表、逐条建条目、设属性、挂到节点下。此前这段骨架在六个文件里各抄了一遍，
    差异只在下面几个钩子上。

    子类需要提供：

    ==========================  ====================================================
    NODE_TYPE_KEY               节点行显示的类型名，取自 Translator.EPISODE_TYPE
    get_episode_list()          列表在响应中的位置
    build_item_data(episode)    单个条目的字段映射
    set_episode_attribute()     单个条目的属性位
    ==========================  ====================================================

    可选覆盖：

    ==========================  ====================================================
    get_node_title()            节点标题，默认为空（由 update_episode_list 回退
                                为分类名称，历史记录与稍后再看即依赖这一点）
    episode_data_parser()       写入该次解析共享的 episode 数据，默认不写
    get_current_episode_data()  链接指向的那一条，默认为空（链接不指向具体条目）
    ==========================  ====================================================
    """

    # Translator.EPISODE_TYPE 的键，子类必须指定
    NODE_TYPE_KEY: str = ""

    def __init__(self, info_data: dict, category_name: str):
        super().__init__()

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self, update_episode_list: bool = True):
        self.episode_data_parser()

        node = self.build_node()

        if update_episode_list:
            self.update_episode_list(node, self.get_current_episode_data())

        return node

    def get_node_type_name(self) -> str:
        """本类内容的显示名称。历史记录、稍后再看还会把它用作条目的父级标题"""
        return Translator.EPISODE_TYPE(self.NODE_TYPE_KEY)

    def build_node(self):
        root_node = TreeItem({
            "number": self.get_node_type_name(),
            "title": self.get_node_title()
        })
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        # 关键词搜索可能没有任何结果，部分接口此时直接省略列表字段而不是给空列表
        for episode in self.get_episode_list() or []:
            self.episode_count += 1

            item = TreeItem(self.build_item_data(episode))

            self.set_episode_attribute(episode, item)

            root_node.add_child(item)

        return root_node

    # ------------------------------------------------------------------
    # 子类实现
    # ------------------------------------------------------------------

    def get_episode_list(self) -> list:
        raise NotImplementedError

    def build_item_data(self, episode_data: dict) -> dict:
        raise NotImplementedError

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 可选覆盖
    # ------------------------------------------------------------------

    def get_node_title(self) -> str:
        return ""

    def episode_data_parser(self):
        pass

    def get_current_episode_data(self) -> tuple:
        """
        链接指向的那一条，形如 (TreeItem 的字段名, 值)。

        只有指向具体条目的链接才有内容：个人空间、收藏夹的链接不指向某一集，
        所以默认返回空；播放页链接（www.bilibili.com/list/{mid}?…）指向列表里
        的某一个视频，解析列表据此定位并勾选它。
        """
        return None

    # ------------------------------------------------------------------
    # 供子类复用
    # ------------------------------------------------------------------

    @staticmethod
    def build_video_url(bvid: str) -> str:
        return "https://www.bilibili.com/video/{bvid}".format(bvid = bvid)
