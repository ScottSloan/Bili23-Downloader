from PySide6.QtCore import Qt

from contextlib import contextmanager
from threading import RLock
from enum import IntFlag
from typing import List
import uuid

class EpisodeData:
    # 全局剧集数据表
    table: dict[str, dict] = {}

    # 解析界面与分P对话框可以同时存活，两边的解析各自跑在自己的线程里，都会往 table 写。
    # 键是 uuid，条目之间不会冲突，真正危险的是 clear_cache()：它会把另一边刚写进去的
    # 数据一并擦掉，之后创建下载任务时 get_episode_data() 拿到空字典，UP 主、简介等
    # 附加信息全部丢失。因此用 _active_parsers 记录正在写入的解析数，有并发解析时跳过清理，
    # 顶多多留一份用不到的数据，等下一次独占解析时再回收。
    _lock = RLock()
    _active_parsers = 0

    @classmethod
    def add_episode(cls):
        episode_id = str(uuid.uuid4())

        with cls._lock:
            cls.table[episode_id] = {}

        return episode_id

    @classmethod
    def get_episode_data(cls, episode_id: str):
        with cls._lock:
            return cls.table.get(episode_id, {})

    @classmethod
    def clear_cache(cls):
        with cls._lock:
            if cls._active_parsers:
                return

            cls.table.clear()

    @classmethod
    @contextmanager
    def parsing(cls, clear_cache: bool = True):
        """
        标记一段正在写入剧集数据的解析流程

        clear_cache 为 True 时会在进入前尝试清空旧数据，清空与登记必须在同一把锁内完成，
        否则清空之后、登记之前挤进来的另一个解析会被误判为可清理
        """
        with cls._lock:
            if clear_cache and not cls._active_parsers:
                cls.table.clear()

            cls._active_parsers += 1

        try:
            yield

        finally:
            with cls._lock:
                cls._active_parsers = max(0, cls._active_parsers - 1)

class Attribute(IntFlag):
    VIDEO_BIT                                 = 1 << 0                   # 是否为投稿视频
    BANGUMI_BIT                               = 1 << 1                   # 是否为剧集
    CHEESE_BIT                                = 1 << 2                   # 是否为课程
    WEEKLY_BIT                                = 1 << 3                   # 是否为每周必看
    COLLECTION_LIST_BIT                       = 1 << 4                   # 是否为合集列表
    SPACE_BIT                                 = 1 << 5                   # 是否为个人空间
    FAVLIST_BIT                               = 1 << 6                   # 是否为收藏夹

    NEED_PARSE_BIT                            = 1 << 7                   # 是否需要二次解析，如个人空间、收藏夹、合集列表中的视频

    NORMAL_BIT                                = 1 << 8                   # 是否为单个视频（item）
    PART_BIT                                  = 1 << 9                   # 是否为分P（item）
    COLLECTION_BIT                            = 1 << 10                  # 是否为合集（node）
    INTERACTIVE_BIT                           = 1 << 11                  # 是否为互动视频（item）

    DOWNLOAD_AS_SINGLE_VIDEO_BIT              = 1 << 12                  # 是否下载为单个视频

    WATCH_LATER_BIT                           = 1 << 13                  # 是否为稍后再看
    HISTORY_BIT                               = 1 << 14                  # 是否为历史记录

    TREE_NODE_BIT                             = 1 << 15                  # 是否为树节点

    AUDIO_BIT                                 = 1 << 16                  # 是否为音频

    FAVORITE_WITH_MULTI_PART_VIDEO_BIT        = 1 << 17                  # 收藏夹中是否包含分P视频

class TreeItemBase:
    def __init__(self):
        self.parent: TreeItem = None
        self.checked = Qt.CheckState.Unchecked
        self.children: List[TreeItem] = []

    def add_child(self, child: "TreeItem"):
        child.parent = self

        self.children.append(child)

    def child(self, row: int):
        return self.children[row]
    
    def count(self):
        return len(self.children)
    
    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        
        return 0
    
    def set_checked_state(self, state: Qt.CheckState):
        if isinstance(state, int):
            state = Qt.CheckState(state)

        if self.checked == state:
            return

        self.checked = state

        # 向下传递
        if state in (Qt.CheckState.Checked, Qt.CheckState.Unchecked):
            self._propagate_down(state)

        # 向上传递
        if self.parent:
            self.parent._propagate_up()

    def _propagate_down(self, state: Qt.CheckState):
        self.checked = state

        for child in self.children:
            child._propagate_down(state)

    def _propagate_up(self):
        states = [child.checked for child in self.children]

        if all(s == Qt.CheckState.Checked for s in states):
            new_state = Qt.CheckState.Checked

        elif all(s == Qt.CheckState.Unchecked for s in states):
            new_state = Qt.CheckState.Unchecked

        else:
            new_state = Qt.CheckState.PartiallyChecked

        if self.checked != new_state:
            self.checked = new_state

            if self.parent:
                self.parent._propagate_up()

    def refresh_check_state(self):
        """
        自底向上重算整棵子树的勾选状态，叶子节点的状态视为已确定

        用于批量改动（如 Shift 范围勾选）后一次性同步父节点状态，
        避免逐项调用 set_checked_state 触发 O(项数 × 深度) 次向上传递
        """
        if not self.children:
            return self.checked

        states = [child.refresh_check_state() for child in self.children]

        if all(s == Qt.CheckState.Checked for s in states):
            self.checked = Qt.CheckState.Checked

        elif all(s == Qt.CheckState.Unchecked for s in states):
            self.checked = Qt.CheckState.Unchecked

        else:
            self.checked = Qt.CheckState.PartiallyChecked

        return self.checked

    def get_all_leaves(self):
        """
        递归返回所有叶子节点（无子节点的项）
        """
        if not self.children:
            return [self]

        leaves: List[TreeItem] = []

        for child in self.children:
            leaves.extend(child.get_all_leaves())

        return leaves

    def get_all_checked_children(self, to_dict = False, mark_as_downloaded = False):
        checked_items: List[TreeItem] = []

        for child in self.children:
            if child.children:
                checked_items.extend(child.get_all_checked_children(to_dict = to_dict, mark_as_downloaded = mark_as_downloaded))
            else:
                if child.checked == Qt.CheckState.Checked and child.attribute & Attribute.TREE_NODE_BIT == 0:  # 排除树节点

                    if mark_as_downloaded:
                        child.downloaded = True

                    if to_dict:
                        checked_items.append(child.to_dict())
                    else:
                        checked_items.append(child)

        return checked_items

    def get_all_children(self, to_dict = False):
        all_items: List[TreeItem] = []

        for child in self.children:
            if child.children:
                all_items.extend(child.get_all_children(to_dict = to_dict))
            else:
                if child.attribute & Attribute.TREE_NODE_BIT == 0:  # 排除树节点
                    if to_dict:
                        all_items.append(child.to_dict())
                    else:
                        all_items.append(child)

        return all_items

class TreeItem(TreeItemBase):
    def __init__(self, item_data: dict):
        super().__init__()

        self.attribute = 0

        # 发布、收藏、观看时间
        self.pubtime = item_data.get("pubtime", 0)
        self.favtime = item_data.get("favtime", 0)
        self.viewtime = item_data.get("viewtime", 0)

        self.expired = item_data.get("expired", False)

        self.aid = item_data.get("aid", 0)
        self.cid = item_data.get("cid", 0)
        self.sid = item_data.get("sid", 0)
        self.url = item_data.get("url", "")
        self.bvid = item_data.get("bvid", "")
        self.ep_id = item_data.get("ep_id", 0)
        self.badge = item_data.get("badge", "")
        self.cover = item_data.get("cover", "")
        self.title = item_data.get("title", "")
        self.author = item_data.get("author", "")
        self.number = item_data.get("number", "")
        self.duration = item_data.get("duration", 0)
        self.episode_id = item_data.get("episode_id", "")
        self.episode_plot = item_data.get("episode_plot", "")
        self.part_number = item_data.get("part_number", 0)
        self.episode_number = item_data.get("episode_number", 0)
        self.related_titles = item_data.get("related_titles", {})

        self.uploader = item_data.get("uploader", "")
        self.uploader_uid = item_data.get("uploader_uid", 0)

        self.downloaded = False

    def set_attribute(self, flag: int):
        self.attribute |= flag

    def to_dict(self):
        data = {
            "attribute": self.attribute,                           # 属性标志位
            "episode_id": self.episode_id,                         # 剧集 ID
            "episode_number": self.episode_number,                 # 剧集序号，仅剧集正片有效
            "aid": self.aid,
            "badge": self.badge,                                   # 备注
            "bvid": self.bvid,
            "cid": self.cid,
            "sid": self.sid,
            "cover": self.cover,
            "duration": self.duration,                             # 时长（s）
            "ep_id": self.ep_id,
            "number": self.number,                                 # 在解析列表中显示的序号
            "pubtime": self.pubtime,                               # 发布时间（时间戳）
            "favtime": self.favtime,                               # 收藏时间（时间戳）
            "viewtime": self.viewtime,                             # 观看时间（时间戳）
            "part_number": self.part_number,                       # 分P序号，仅分P有效
            "related_titles": self.related_titles,                 # 相关标题，如合集标题、章节标题等
            "title": self.title,                                   # 标题
            "url": self.url,
            "episode_plot": self.episode_plot,                     # 剧集剧情简介
        }

        if self.uploader:
            data["uploader_info"] = {
                "uploader": self.uploader,
                "uploader_uid": self.uploader_uid
            }

        return data
    
    def search_items(self, keyword: str):
        """
        递归搜索匹配关键字的节点
        """
        matches = []
        if keyword.lower() in self.title.lower():
            matches.append(self)

        for child in self.children:
            matches.extend(child.search_items(keyword))

        return matches

    def has_attribute(self, flag: int):
        return (self.attribute & flag) == flag

    @property
    def dyn_time(self):
        if self.attribute & (Attribute.FAVLIST_BIT | Attribute.WATCH_LATER_BIT):
            return self.favtime

        if self.attribute & Attribute.HISTORY_BIT:
            return self.viewtime

        return self.pubtime
    