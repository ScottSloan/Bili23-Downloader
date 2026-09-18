from ..enum import ConventionType, VariableType

from ...format.time import Time

from enum import StrEnum

convention_type_map = {
    "NORMAL": ConventionType.NORMAL,
    "PART": ConventionType.PART,
    "COLLECTION": ConventionType.COLLECTION,
    "INTERACTIVE_VIDEO": ConventionType.INTERACTIVE_VIDEO,
    "BANGUMI": ConventionType.BANGUMI,
    # 会员购商城课程曾是这里独立的一项（31），现已并入课程：两者的默认规则一字不差，
    # 分开列只是让用户在规则列表里看到两条同名的预设
    "CHEESE": ConventionType.CHEESE,
    "FAVORITE": ConventionType.FAVORITE,
    "SPACE": ConventionType.SPACE,
    "HISTORY": ConventionType.HISTORY,
    "WATCH_LATER": ConventionType.WATCH_LATER,
    "WEEKLY": ConventionType.WEEKLY,
    "AUDIO": ConventionType.AUDIO
}

reversed_convention_type_map = {v: k for k, v in convention_type_map.items()}

class SampleShape(StrEnum):
    """
    预览样本的条目形态

    同一条规则要同时适配这几种形态，预览必须把它们并排摆出来，
    否则用户根本看不出可选段在哪一种下会收缩
    """

    SINGLE = "single"                   # 单个视频
    MULTI = "multi"                     # 分P视频中的一P
    COLLECTION = "collection"           # 合集中的一集

# 各规则类型实际可能遇到的条目形态。
# 收藏夹、个人空间、历史记录、稍后再看都是「来源」，里面混着普通视频、分P与合集，
# 这三种形态由命名规则的可选段在来源类型内部消化。
# 剧集、课程、音乐则没有分P与合集之分。
# 每周必看的条目不带 NEED_PARSE_BIT，从不二次解析，因此也没有分P形态
SUPPORTED_SHAPES = {
    ConventionType.NORMAL: (SampleShape.SINGLE,),
    ConventionType.PART: (SampleShape.MULTI,),
    ConventionType.COLLECTION: (SampleShape.COLLECTION,),
    ConventionType.INTERACTIVE_VIDEO: (SampleShape.SINGLE,),
    ConventionType.BANGUMI: (SampleShape.SINGLE,),
    ConventionType.CHEESE: (SampleShape.SINGLE,),
    # 合集类型的两种形态说的是「这一集在稿件内部是单P还是多P」：合集列表里的条目
    # 多数只有合集标题 + 标题，{section_title}/{parent_title}/{p} 都是空的
    ConventionType.COLLECTION: (SampleShape.SINGLE, SampleShape.COLLECTION),
    ConventionType.FAVORITE: (SampleShape.SINGLE, SampleShape.MULTI, SampleShape.COLLECTION),
    ConventionType.SPACE: (SampleShape.SINGLE, SampleShape.MULTI, SampleShape.COLLECTION),
    ConventionType.HISTORY: (SampleShape.SINGLE, SampleShape.MULTI, SampleShape.COLLECTION),
    ConventionType.WATCH_LATER: (SampleShape.SINGLE, SampleShape.MULTI, SampleShape.COLLECTION),
    ConventionType.WEEKLY: (SampleShape.SINGLE,),
    ConventionType.AUDIO: (SampleShape.SINGLE,),
}

# 混在「来源」列表里的其他类型条目
#
# 它们**不**套用来源类型的命名规则，而是走自己类型的规则 —— 见
# FileNameFormatter.get_type_id_from_attribute 里「媒体形态位优先于来源位」那一段。
# 编辑器的预览据此多列一行，免得用户以为整份列表都归当前这条规则管。
#
# 每一格都在解析器里对得上：
#   收藏夹按 ogv 判影视（favlist.py）、稍后再看按 bangumi 判影视（watch_later.py）、
#   历史记录按 business 三分（history.py）、个人空间按 is_lesson_video 判课程（space.py）。
# 课程不在收藏夹与稍后再看里，影视不在个人空间里。
MIXED_ENTRY_TYPES = {
    ConventionType.FAVORITE: (ConventionType.BANGUMI,),
    ConventionType.HISTORY: (ConventionType.BANGUMI, ConventionType.CHEESE),
    ConventionType.WATCH_LATER: (ConventionType.BANGUMI,),
    ConventionType.SPACE: (ConventionType.CHEESE,),
}

# 变量的数据类型。只有这几个变量做数字格式化（{number:02d} 之类）有意义，
# 其余标识符虽然也是整数，但补零毫无用途，一律按文本处理。
# 这张表决定编辑器里格式项的形态：日期给 strftime 预设，数字给补零位数，文本不显示
_VARIABLE_TYPE = {
    "pub_time": VariableType.DATETIME,
    "create_time": VariableType.DATETIME,
    "fav_time": VariableType.DATETIME,
    "last_watched_time": VariableType.DATETIME,

    "number": VariableType.NUMBER,
    "season_number": VariableType.NUMBER,
    "episode_number": VariableType.NUMBER,
    "p": VariableType.NUMBER,
}

# 预览样本里「没有取到值」时填什么。必须与 EpisodeInfo 的 dataclass 默认值
# 保持一致 —— 整数字段是 0，字符串字段是空串。
#
# 这里不能图省事一律用空串：{p:02d}、{aid:05d} 这类写法碰上空串会抛
# ValueError，预览便报「规则无效」，而同样的规则在运行期完全正常。
# 编辑器拒绝一条运行期可用的规则，正是 issue #461 的病根
_NUMERIC_VARIABLES = frozenset({
    "pub_ts", "create_ts", "fav_ts", "last_watched_ts", "number",
    "uploader_uid", "aid", "cid", "ep_id", "season_id",
    "course_id", "lesson_id", "item_id", "section_id",
    "season_number", "episode_number", "p",
    "favorites_id", "favorites_owner_id", "space_owner_id",
})

_SAMPLE_TIMESTAMP = 1772841600

# 同一个变量在不同类型下含义不同，_FOR_XXX 描述键只在该类型的推荐清单里准确。
# 作为「更多变量」追加时改用通用描述，免得个人空间的 leaf_title 被说成「分P标题」
_GENERIC_DESCRIPTION = {
    "leaf_title": "LEAF_TITLE_GENERIC",
    "parent_title": "PARENT_TITLE_GENERIC",
    "p": "PART_NUMBER_GENERIC",
    "section_title": "SECTION_TITLE_GENERIC",
    "series_title": "SERIES_TITLE_GENERIC",
    "episode_title": "EPISODE_TITLE_GENERIC",
}

# 这几类的 parent_title 是入口固定标签（「历史记录」「稍后再看」「第377期」「歌单名称」），
# 单个条目时不该被形态覆盖清空。
#
# 分P条目则不同：二次解析产生的 related_titles 会盖掉入口标签，此时 parent_title
# 确实是稿件标题 —— 见 TaskManager.__update_episode_info 的合并顺序，
# 条目级 related_titles 排在来源级 EpisodeData 之后
_LABEL_PARENT_TITLE_TYPES = frozenset({
    ConventionType.HISTORY,
    ConventionType.WATCH_LATER,
    ConventionType.WEEKLY,
    ConventionType.AUDIO,
})

# 下面这几类的 collection_title 是**归属信息**而不是形态信息，任何形态下都该有值。
#
# 形态覆盖里清空它，是因为来源列表里的分P稿件不在任何合集里；但合集条目自己就住在
# 合集里，清空等于告诉用户 {collection_title} 取不到值
_SHAPE_KEEPS_COLLECTION_TYPES = frozenset({ConventionType.COLLECTION})

_SHAPE_OVERRIDES = {
    # 只清空形态相关的键，leaf_title 留给各类型自己的样例
    SampleShape.SINGLE: {
        "parent_title": "",
        "p": 0,
        "collection_title": "",
        "section_title": "",
    },
    SampleShape.MULTI: {
        "parent_title": "【KEY社20周年音乐专辑】Key BEST SELECTION",
        "p": 4,
        "leaf_title": "04 アルカテイル",
        "collection_title": "",
        "section_title": "",
    },
    SampleShape.COLLECTION: {
        "collection_title": "艾尔登法环白金攻略",
        "section_title": "DLC黄金树幽影",
        "parent_title": "全收集、全流程、全剧情攻略",
        "p": 3,
        "leaf_title": "03【墓地平原-西+艾拉克河】",
    },
}

# 通用形态覆盖之上的按类型补丁
#
# 通用覆盖是按形态写的，够不着「同一个形态在某类型下另有说法」的情况。
# 合集就是这种：_collection_variable 里的 leaf_title 例子带着「03」这样的分P
# 序号（它伺候的是「合集中的一集」那个形态），拿来当单P条目的样本会让人以为
# 标题本身就长这样。这里换成一个普通稿件标题，与单个视频类型用的是同一个
_SHAPE_OVERRIDES_BY_TYPE = {
    (ConventionType.COLLECTION, SampleShape.SINGLE): {
        "leaf_title": "游戏科学新作《黑神话：钟馗》先导预告",
    },
}

class VariableListFactory:
    def __init__(self):
        pass

    def build(self, type, full: bool = True):
        """
        取该类型的变量清单

        full 为真时，在类型专属的推荐变量之后追加其余全部变量。

        命名规则的键空间本来就是恒定的 —— get_variable_data_from_task_info
        无条件填齐全部键 —— 按类型裁剪只是界面上的「推荐」。一旦拿这份裁剪过的
        清单去当 str.format 的 kwargs，编辑器就会因为 KeyError 拒绝一条运行期
        完全正常的规则：个人空间下写不了 {parent_title}/{p} 正是这么来的。
        """
        primary = [self._decorate(entry, "PRIMARY") for entry in self._primary_variable(type)]

        if not full:
            return primary

        known = {entry["name"] for entry in primary}

        return primary + [
            self._decorate(entry, "MORE", generic = True)
            for entry in self._all_variable
            if entry["name"] not in known
        ]

    def build_variable_data(self, type, shape = SampleShape.SINGLE):
        """构造一份预览用的变量数据，键空间与运行期完全一致"""
        data = {
            entry["name"]: self._unset_value(entry["name"])
            for entry in self._all_variable
        }

        for entry in self._primary_variable(type):
            data[entry["name"]] = entry["example"]

        for name, value in _SHAPE_OVERRIDES[shape].items():
            if name == "parent_title" and shape is SampleShape.SINGLE and type in _LABEL_PARENT_TITLE_TYPES:
                continue

            if name == "collection_title" and type in _SHAPE_KEEPS_COLLECTION_TYPES:
                continue

            data[name] = value

        for name, value in _SHAPE_OVERRIDES_BY_TYPE.get((type, shape), {}).items():
            data[name] = value

        # 时间变量必须是 datetime，否则 {pub_time:%Y-%m-%d} 会抛异常
        for name, variable_type in _VARIABLE_TYPE.items():
            if variable_type == VariableType.DATETIME:
                data[name] = Time.from_timestamp(_SAMPLE_TIMESTAMP)

        return data

    @property
    def _all_variable(self):
        """按 name 去重的全集，顺序取各类型推荐清单的出现次序"""
        entries = []
        known = set()

        for type in convention_type_map.values():
            for entry in self._primary_variable(type):
                if entry["name"] not in known:
                    known.add(entry["name"])
                    entries.append(entry)

        return entries

    @staticmethod
    def _decorate(entry: dict, group: str, generic: bool = False):
        entry = entry.copy()

        entry["group"] = group
        entry["type"] = _VARIABLE_TYPE.get(entry["name"], VariableType.TEXT)

        if generic:
            entry["description"] = _GENERIC_DESCRIPTION.get(entry["name"], entry["description"])

        return entry

    @staticmethod
    def _unset_value(name: str):
        if name in _NUMERIC_VARIABLES:
            return 0

        return ""

    def _primary_variable(self, type):
        match type:
            case ConventionType.NORMAL:
                return self._base_variable + self._normal_variable
            
            case ConventionType.PART:
                return self._base_variable + self._part_variable
            
            case ConventionType.COLLECTION:
                return self._base_variable + self._collection_variable
            
            case ConventionType.INTERACTIVE_VIDEO:
                return self._base_variable + self._interactive_video_variable
            
            case ConventionType.BANGUMI:
                return self._base_variable + self._bangumi_variable
            
            case ConventionType.CHEESE:
                return self._base_variable + self._cheese_variable

            case ConventionType.FAVORITE:
                return self._base_variable + self._normal_variable + self._favorite_variable

            case ConventionType.SPACE:
                return self._base_variable + self._normal_variable + self._space_variable
            
            case ConventionType.HISTORY:
                return self._base_variable + self._history_variable

            case ConventionType.WATCH_LATER:
                return self._base_variable + self._watch_later_variable
            
            case ConventionType.WEEKLY:
                return self._base_variable + self._weekly_variable

            case ConventionType.AUDIO:
                return self._audio_variable

            case _:
                return []

    @property
    def _base_variable(self):
        return [
            {
                "name": "pub_time",
                "variable": "{pub_time:%Y-%m-%d_%H-%M-%S}",
                "description": "PUB_TIME",
                "example": "2026-03-07_12-00-00",
                "type": VariableType.DATETIME
            },
            {
                "name": "pub_ts",
                "variable": "{pub_ts}",
                "description": "PUB_TS",
                "example": "1772841600",
                "type": VariableType.TEXT
            },
            {
                "name": "create_time",
                "variable": "{create_time:%Y-%m-%d_%H-%M-%S}",
                "description": "CREATE_TIME",
                "example": "2026-03-07_12-00-00",
                "type": VariableType.DATETIME
            },
            {
                "name": "create_ts",
                "variable": "{create_ts}",
                "description": "CREATE_TS",
                "example": "1772841600",
                "type": VariableType.TEXT
            },
            {
                "name": "number",
                "variable": "{number}",
                "description": "NUMBER",
                "example": 1,
                "type": VariableType.NUMBER
            },
            {
                "name": "uploader",
                "variable": "{uploader}",
                "description": "UPLOADER",
                "example": "UP主昵称",
                "type": VariableType.TEXT
            },
            {
                "name": "uploader_uid",
                "variable": "{uploader_uid}",
                "description": "UPLOADER_UID",
                "example": "12345678",
                "type": VariableType.TEXT
            },
            {
                "name": "video_quality",
                "variable": "{video_quality}",
                "description": "VIDEO_QUALITY",
                "example": "1080P",
                "type": VariableType.TEXT
            },
            {
                "name": "audio_quality",
                "variable": "{audio_quality}",
                "description": "AUDIO_QUALITY",
                "example": "192K",
                "type": VariableType.TEXT
            },
            {
                "name": "video_codec",
                "variable": "{video_codec}",
                "description": "VIDEO_CODEC",
                "example": "HEVC",
                "type": VariableType.TEXT
            }
        ]
    
    @property
    def _normal_variable(self):
        return [
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "115056436060087"
            },
            {
                "name": "bvid",
                "variable": "{bvid}",
                "description": "BVID",
                "example": "BV1sHePzWEbG"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "31809079869"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_NORMAL",
                "example": "游戏科学新作《黑神话：钟馗》先导预告"
            }
        ]
    
    @property
    def _part_variable(self):
        return [
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_PART",
                "example": "【KEY社20周年音乐专辑】Key BEST SELECTION"
            },
            {
                "name": "p",
                "variable": "{p}",
                "description": "PART_NUMBER_FOR_PART",
                "example": 4
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_PART",
                "example": "04 アルカテイル"
            },
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "634233546"
            },
            {
                "name": "bvid",
                "variable": "{bvid}",
                "description": "BVID",
                "example": "BV1Rb4y1t7gc"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "442845594"
            }
        ]

    @property
    def _collection_variable(self):
        return [
            {
                "name": "collection_title",
                "variable": "{collection_title}",
                "description": "COLLECTION_TITLE",
                "example": "艾尔登法环白金攻略"
            },
            {
                "name": "section_title",
                "variable": "{section_title}",
                "description": "SECTION_TITLE_FOR_COLLECTION",
                "example": "DLC黄金树幽影"
            },
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_COLLECTION",
                "example": "全收集、全流程、全剧情攻略"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_COLLECTION",
                "example": "03【墓地平原-西+艾拉克河】"
            },
            {
                "name": "p",
                "variable": "{p}",
                "description": "PART_NUMBER_FOR_COLLECTION",
                "example": 3
            },
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "1555921697"
            },
            {
                "name": "bvid",
                "variable": "{bvid}",
                "description": "BVID",
                "example": "BV1r1421r78r"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "1599644073"
            }
        ]

    @property
    def _interactive_video_variable(self):
        return [
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_INTERACTIVE_VIDEO",
                "example": "序幕"
            },
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_INTERACTIVE_VIDEO",
                "example": "【互动视频】你能逃出这个房间吗？"
            }
        ]

    @property
    def _bangumi_variable(self):
        return [
            {
                "name": "series_title",
                "variable": "{series_title}",
                "description": "SERIES_TITLE_FOR_BANGUMI",
                "example": "轻音少女"
            },
            {
                "name": "season_title",
                "variable": "{season_title}",
                "description": "SEASON_TITLE",
                "example": "轻音少女 第二季"
            },
            {
                "name": "section_title",
                "variable": "{section_title}",
                "description": "SECTION_TITLE_FOR_BANGUMI_CHEESE",
                "example": "正片"
            },
            {
                "name": "episode_title",
                "variable": "{episode_title}",
                "description": "EPISODE_TITLE",
                "example": "第18话 主角！"
            },
            {
                "name": "season_number",
                "variable": "{season_number}",
                "description": "SEASON_NUMBER",
                "example": 2
            },
            {
                "name": "episode_number",
                "variable": "{episode_number}",
                "description": "EPISODE_NUMBER",
                "example": 18
            },
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "849267924"
            },
            {
                "name": "bvid",
                "variable": "{bvid}",
                "description": "BVID",
                "example": "BV1NL4y1i7L2"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "91560482"
            },
            {
                "name": "ep_id",
                "variable": "{ep_id}",
                "description": "EP_ID",
                "example": "21296"
            },
            {
                "name": "season_id",
                "variable": "{season_id}",
                "description": "SEASON_ID",
                "example": "1173"
            }
        ]
    
    @property
    def _cheese_variable(self):
        return [
            {
                "name": "series_title",
                "variable": "{series_title}",
                "description": "SERIES_TITLE_FOR_CHEESE",
                "example": "【618限时价】清华梁爽：0-N1日语精讲高级班"
            },
            {
                "name": "section_title",
                "variable": "{section_title}",
                "description": "SECTION_TITLE_FOR_BANGUMI_CHEESE",
                "example": "先导片"
            },
            {
                "name": "episode_title",
                "variable": "{episode_title}",
                "description": "EPISODE_TITLE",
                "example": "【先导片】清华梁爽带你重新定义日语学习，教你说好、更能考好日语！"
            },
            {
                "name": "aid",
                "variable": "{aid}",
                "description": "AID",
                "example": "315163535"
            },
            {
                "name": "cid",
                "variable": "{cid}",
                "description": "CID",
                "example": "1639897333"
            },
            {
                "name": "ep_id",
                "variable": "{ep_id}",
                "description": "EP_ID",
                "example": "158662"
            },
            {
                "name": "season_id",
                "variable": "{season_id}",
                "description": "SEASON_ID",
                "example": "4016"
            },

            # 下面四个是会员购商城课程独有的定位标识，它并入课程之后跟着一并挪了过来。
            # 必须留在这张清单里：_all_variable 是遍历各类型清单拼出的全局键空间，
            # 四个键一旦没有出处就会从编辑器里彻底消失 —— 运行期照样填值，界面却
            # 把它们当未知变量拒掉
            {
                "name": "course_id",
                "variable": "{course_id}",
                "description": "COURSE_ID",
                "example": "1000625147"
            },
            {
                "name": "lesson_id",
                "variable": "{lesson_id}",
                "description": "LESSON_ID",
                "example": "180281190609920"
            },
            {
                "name": "item_id",
                "variable": "{item_id}",
                "description": "ITEM_ID",
                "example": "10302975"
            },
            {
                "name": "section_id",
                "variable": "{section_id}",
                "description": "SECTION_ID",
                "example": "180281190650881"
            }
        ]

    @property
    def _favorite_variable(self):
        return [
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_FAVORITE",
                "example": "【KEY社20周年音乐专辑】Key BEST SELECTION"
            },
            {
                "name": "favorites_name",
                "variable": "{favorites_name}",
                "description": "FAVORITES_NAME",
                "example": "默认收藏夹"
            },
            {
                "name": "favorites_id",
                "variable": "{favorites_id}",
                "description": "FAVORITES_ID",
                "example": "12345678"
            },
            {
                "name": "favorites_owner",
                "variable": "{favorites_owner}",
                "description": "FAVORITES_OWNER",
                "example": "用户昵称"
            },
            {
                "name": "favorites_owner_id",
                "variable": "{favorites_owner_id}",
                "description": "FAVORITES_OWNER_ID",
                "example": "12345678"
            },
            {
                "name": "fav_time",
                "variable": "{fav_time:%Y-%m-%d_%H-%M-%S}",
                "description": "FAV_TIME",
                "example": "2026-03-07_12-00-00"
            },
            {
                "name": "fav_ts",
                "variable": "{fav_ts}",
                "description": "FAV_TS",
                "example": "1772841600"
            }
        ]
    
    @property
    def _space_variable(self):
        return [
            {
                "name": "space_owner",
                "variable": "{space_owner}",
                "description": "SPACE_OWNER",
                "example": "用户昵称"
            },
            {
                "name": "space_owner_id",
                "variable": "{space_owner_id}",
                "description": "SPACE_OWNER_ID",
                "example": "12345678"
            }
        ]

    @property
    def _history_variable(self):
        return [
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_HISTORY",
                "example": "历史记录"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_NORMAL",
                "example": "游戏科学新作《黑神话：钟馗》先导预告"
            },
            {
                "name": "last_watched_time",
                "variable": "{last_watched_time:%Y-%m-%d_%H-%M-%S}",
                "description": "LAST_WATCHED_TIME",
                "example": "2026-03-07_12-00-00"
            },
            {
                "name": "last_watched_ts",
                "variable": "{last_watched_ts}",
                "description": "LAST_WATCHED_TS",
                "example": "1772841600"
            }
        ]
    
    @property
    def _watch_later_variable(self):
        return [
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_WATCH_LATER",
                "example": "稍后再看"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_NORMAL",
                "example": "游戏科学新作《黑神话：钟馗》先导预告"
            },
            {
                "name": "fav_time",
                "variable": "{fav_time:%Y-%m-%d_%H-%M-%S}",
                "description": "FAV_TIME",
                "example": "2026-03-07_12-00-00"
            },
            {
                "name": "fav_ts",
                "variable": "{fav_ts}",
                "description": "FAV_TS",
                "example": "1772841600"
            }
        ]

    @property
    def _weekly_variable(self):
        return [
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_WEEKLY",
                "example": "第377期(0612更新)"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_NORMAL",
                "example": "游戏科学新作《黑神话：钟馗》先导预告"
            }
        ]

    @property
    def _audio_variable(self):
        return [
            {
                "name": "pub_time",
                "variable": "{pub_time:%Y-%m-%d_%H-%M-%S}",
                "description": "PUB_TIME",
                "example": "2026-03-07_12-00-00"
            },
            {
                "name": "pub_ts",
                "variable": "{pub_ts}",
                "description": "PUB_TS",
                "example": "1772841600"
            },
            {
                "name": "create_time",
                "variable": "{create_time:%Y-%m-%d_%H-%M-%S}",
                "description": "CREATE_TIME",
                "example": "2026-03-07_12-00-00"
            },
            {
                "name": "create_ts",
                "variable": "{create_ts}",
                "description": "CREATE_TS",
                "example": "1772841600"
            },
            {
                "name": "number",
                "variable": "{number}",
                "description": "NUMBER",
                "example": "1"
            },
            {
                "name": "leaf_title",
                "variable": "{leaf_title}",
                "description": "LEAF_TITLE_FOR_AUDIO",
                "example": "歌曲名称"
            },
            {
                "name": "uploader",
                "variable": "{uploader}",
                "description": "UPLOADER_FOR_AUDIO",
                "example": "歌手"
            },
            {
                "name": "parent_title",
                "variable": "{parent_title}",
                "description": "PARENT_TITLE_FOR_AUDIO",
                "example": "歌单名称"
            },
            {
                "name": "audio_quality",
                "variable": "{audio_quality}",
                "description": "AUDIO_QUALITY",
                "example": "192K"
            }
        ]