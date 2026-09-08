"""
解析的纯逻辑 —— 不依赖 Qt

`worker.py` 里的 `WorkerBase` 本来就是纯逻辑（按 URL 认类型、惰性实例化 parser），
只是和 QObject 住在同一个模块里，WebUI 一导入就被 PySide6 拦下。这里把它搬出来，
`worker.py` 改为从这里导入，两端跑同一份。

## 结果是「发出来」的，不是「返回」的

解析结果不走返回值：`episode/base.py` 的 `update_episode_list()` 会
`signal_bus.parse.update_parse_list.emit(title, category_name, root_node, ...)`。
桌面侧接这个事件往树控件里塞，服务端也接同一个 —— 解析链路本身一行不用改。

代价是要在调用前后临时订阅一次，于是有两个坑：

1. **必须用 DIRECT 调度器订阅。** 服务端装的默认调度器会把回调投递到事件循环线程
   （见 web/dispatch.py），而我们是在工作线程里同步等结果的 —— 投递出去就再也接不住，
   表现为「解析成功但拿不到数据」。
2. **必须串行化。** signal_bus 是全局的，同时跑两个解析会互相截获对方的结果。
   一把锁解决，单用户场景下也不需要更复杂的东西。
"""

from threading import Lock
from typing import List, Optional
import logging

from ..auth.session import ensure_wbi_keys
from ..common.data import url_patterns
from ..common.enum import CheckState
from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..thread.dispatch import DIRECT

from .episode.tree import Attribute, EpisodeData, TreeItem

logger = logging.getLogger(__name__)

# 见模块说明：signal_bus 是全局的，解析必须一个一个来
_parse_lock = Lock()

class ParserResolver:
    """按 URL 认出解析类型，并惰性实例化对应的 parser"""

    def get_parser(self, parser_type: str):
        match parser_type:
            case "video":
                from .parser.video import VideoParser
                return VideoParser()

            case "bangumi":
                from .parser.bangumi import BangumiParser
                return BangumiParser()

            case "cheese":
                from .parser.cheese import CheeseParser
                return CheeseParser()

            case "lesson":
                from .parser.lesson import LessonParser
                return LessonParser()

            case "space":
                from .parser.space import SpaceParser
                return SpaceParser()

            case "favlist":
                from .parser.favlist import FavlistParser
                return FavlistParser()

            case "list":
                from .parser.list import ListParser
                return ListParser()

            case "popular":
                from .parser.popular import PopularParser
                return PopularParser()

            case "watch_later":
                from .parser.watch_later import WatchLaterParser
                return WatchLaterParser()

            case "history":
                from .parser.history import HistoryParser
                return HistoryParser()

            case "audio":
                from .parser.audio import AudioParser
                return AudioParser()

            case _:
                raise ValueError("未知的解析类型")

    def get_parser_type(self, url: str):
        for parser_type, pattern in url_patterns:
            if pattern.search(url):
                return parser_type

        raise ValueError(Translator.ERROR_MESSAGES("INVALID_LINK"))

    def resolve_redirect(self, url: str) -> tuple:
        """b23 短链与 festival 活动页要先跳一次才知道真正的类型"""
        from .parser.b23 import B23Parser
        from .parser.festival import FestivalParser

        parsers = {
            "b23": B23Parser(),
            "festival": FestivalParser(),
        }

        parser_type = self.get_parser_type(url)

        for prefix, parser in parsers.items():
            if prefix in url:
                url = parser.parse(url)

                parser_type = self.get_parser_type(url)

        return url, parser_type

class ParseSession(ParserResolver):
    """阻塞跑一次解析，返回可直接序列化的结果"""

    def parse(self, url: str, pn: int = 1) -> dict:
        captured = {}

        def on_update(title, category_name, root_node, current_episode_data = None):
            captured["title"] = title
            captured["category_name"] = category_name
            captured["root_node"] = root_node
            captured["current"] = current_episode_data

        # 同预览：解析链路里多处要用 wbi 签名，密钥缺失时的报错认不出来
        ensure_wbi_keys()

        with _parse_lock:
            # DIRECT：要在本线程就地拿到结果，不能被投递到事件循环去
            signal_bus.parse.update_parse_list.connect(on_update, dispatcher = DIRECT)

            try:
                with EpisodeData.parsing():
                    url, parser_type = self.resolve_redirect(url)

                    parser = self.get_parser(parser_type)

                    parser.parse(url, pn)

                    extra = parser.get_extra_data()
                    category = parser.get_category_name()

            finally:
                signal_bus.parse.update_parse_list.disconnect(on_update)

        root_node = captured.get("root_node")

        if root_node is None:
            # 解析没报错却什么都没发出来。真发生的话多半是新增了一种 parser 却忘了
            # 调 update_episode_list()，这里把它变成显式失败而不是返回一棵空树
            raise RuntimeError("解析未产出任何结果")

        return {
            "title": captured.get("title") or "",
            "category": captured.get("category_name") or category,
            "parser_type": parser_type,
            "url": url,
            "extra": extra,
            "tree": serialize_node(root_node),
            "current": _serialize_current(captured.get("current")),
        }

def attribute_names(attribute: int) -> List[str]:
    """
    把 Attribute 位标志摊成名字列表

    **前端要靠这些位分支**（是不是树节点、需不需要二次解析、是视频还是音频），
    发数字的话每加一位前端都得同步一张表
    """
    return [flag.name.lower() for flag in Attribute if attribute & flag != 0]

def serialize_node(node: TreeItem) -> dict:
    """
    把一棵解析树转成嵌套字典

    叶子节点带上 `episode`（即 `to_dict()` 的产物）—— 那正是创建下载任务时要交回来的
    东西，前端原样回传即可，不必自己拼
    """
    data = {
        "title": node.title,
        "number": node.number,
        "badge": node.badge,
        "cover": node.cover,
        "duration": node.duration,
        # 时间三兄弟外加 `dyn_time`。
        #
        # **`dyn_time` 必须由这边给**：它是 `TreeItem` 上的属性，按 Attribute 位决定
        # 该显示哪一个（收藏夹看收藏时间、历史记录看观看时间、其余看发布时间）。
        # 让前端自己「哪个有值用哪个」看似等价，实则不是 —— 收藏夹的条目两个时间都有，
        # 那样会显示成发布时间
        "pubtime": node.pubtime,
        "favtime": node.favtime,
        "viewtime": node.viewtime,
        "dyn_time": node.dyn_time,
        "attribute": int(node.attribute),
        "attributes": attribute_names(node.attribute),
        "is_node": bool(node.attribute & Attribute.TREE_NODE_BIT),
        "checked": node.checked == CheckState.CHECKED,
        "children": [serialize_node(child) for child in node.children],
    }

    if not node.children:
        data["episode"] = node.to_dict()

    return data

def collect_episodes(tree: dict, only_checked: bool = False) -> List[dict]:
    """从序列化后的树里把叶子的 episode 收集出来，供创建下载任务用"""
    if not tree:
        return []

    children = tree.get("children") or []

    if not children:
        episode = tree.get("episode")

        if episode is None or tree.get("is_node"):
            return []

        if only_checked and not tree.get("checked"):
            return []

        return [episode]

    collected = []

    for child in children:
        collected.extend(collect_episodes(child, only_checked = only_checked))

    return collected

def _serialize_current(current) -> Optional[dict]:
    """
    链接指向的那一集的**定位方式**

    形如 `("ep_id", 123456)` —— 前一个是按哪个字段找，后一个是要找的值。
    不是 episode_id，也不是属性位：番剧按 ep_id 定位，课程按 ep_id，
    分P 视频按 cid，各自不同，所以传的是「字段 + 值」而非某个固定的键。

    解析列表默认全选，但用户点进来的是某一集的链接 —— 前端要据此把它高亮出来，
    媒体信息预览也靠它决定预览哪一个
    """
    if not current:
        return None

    try:
        field, value = current[0], current[1]

    except Exception:
        logger.warning("认不出的定位信息：%r", current)

        return None

    return {"field": field, "value": value}
