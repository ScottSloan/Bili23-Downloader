from emoji import replace_emoji
from enum import IntFlag
import uuid

class EpisodeData:
    # 全局剧集数据表
    table: dict[str, dict] = {}

    @classmethod
    def add_episode(cls):
        episode_id = str(uuid.uuid4())

        cls.table[episode_id] = {}

        return episode_id
    
    @classmethod
    def get_episode_data(cls, episode_id: str):
        return cls.table.get(episode_id, {})

    @classmethod
    def clear_cache(cls):
        cls.table.clear()

class Attribute(IntFlag):
    ITEM_NODE_BIT          = 1 << 0          # 是否为节点（node）
    VIDEO_BIT              = 1 << 1          # 是否为视频（item）
    BANGUMI_BIT            = 1 << 2          # 是否为剧集（item）
    CHEESE_BIT             = 1 << 3          # 是否为课程（item）
    POPULAR_BIT            = 1 << 4          # 是否为每周必看（item）
    SPACE_BIT              = 1 << 5          # 是否为个人空间（item）
    FAVLIST_BIT            = 1 << 6          # 是否为收藏夹（item）
    NEED_PARSE_BIT         = 1 << 7          # 是否需要二次解析，如个人空间、收藏夹中的视频（item）
    
    NORMAL_BIT             = 1 << 8          # 是否为单个视频（item）
    PART_BIT               = 1 << 9          # 是否为分P（item）
    COLLECTION_BIT         = 1 << 10         # 是否为合集（node）
    INTERACTIVE_BIT        = 1 << 11         # 是否为互动视频（item）

class TreeNode:
    def __init__(self, node_data: dict):
        super().__init__()

        self.attribute = Attribute.ITEM_NODE_BIT
        self.children: list[TreeNode | TreeItem] = []

        self.duration = node_data.get("duration", 0)
        self.number = node_data.get("number", "")
        self.title = node_data.get("title", "")

    def add_child(self, child):
        self.children.append(child)

    def set_attribute(self, flag: int):
        self.attribute |= flag

    def to_dict(self):
        return {
            "attribute": self.attribute,                                          # 属性标志位
            "children": [child.to_dict() for child in self.children],
            "duration": self.duration,                                            # 时长（s）
            "number": self.number,                                                # 在剧集列表中显示的序号
            "title": replace_emoji(self.title, "")                                # 标题，去除 emoji 表情
        }

class TreeItem:
    def __init__(self, item_data: dict):
        self.attribute = 0
        self.episode_id = item_data.get("episode_id", "")
        self.related_titles = item_data.get("related_titles", {})

        self.aid = item_data.get("aid", 0)
        self.badge = item_data.get("badge", "")
        self.bvid = item_data.get("bvid", "")
        self.cid = item_data.get("cid", 0)
        self.cover = item_data.get("cover", "")
        self.duration = item_data.get("duration", 0)
        self.ep_id = item_data.get("ep_id", 0)
        self.episode_number = item_data.get("episode_number", 0)
        self.number = item_data.get("number", "")
        self.pubtime = item_data.get("pubtime", 0)
        self.part_number = item_data.get("part_number", 0)
        self.title = item_data.get("title", "")
        self.url = item_data.get("url", "")

    def set_attribute(self, flag: int):
        self.attribute |= flag

    def set_category(self, category):
        pass

    def to_dict(self):
        return {
            "attribute": self.attribute,                           # 属性标志位
            "episode_id": self.episode_id,                         # 剧集 ID
            "episode_number": self.episode_number,                 # 剧集序号，仅剧集正片有效
            "aid": self.aid,
            "badge": self.badge,                                   # 备注
            "bvid": self.bvid,
            "cid": self.cid,
            "cover": self.cover,
            "duration": self.duration,                             # 时长（s）
            "ep_id": self.ep_id,
            "number": self.number,                                 # 在剧集列表中显示的序号
            "pubtime": self.pubtime,                               # 发布时间（时间戳）
            "part_number": self.part_number,                       # 分P序号，仅分P有效
            "related_titles": self.related_titles,                 # 相关标题，如合集标题、章节标题等
            "title": replace_emoji(self.title, ""),                # 标题，去除 emoji 表情
            "url": self.url
        }
    