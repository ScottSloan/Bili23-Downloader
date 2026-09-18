"""
util/parse/episode/ 下「平铺列表」类解析器的特征测试。

space / watch_later / favlist / history / popular / list 六个解析器把
B 站接口返回的列表转成解析列表要显示的树。它们的骨架完全一致，差异只在
六个点：列表在响应里的位置、节点类型、节点标题、条目字段映射、属性位、
以及写入共享 episode 数据的内容。

本文件是重构前的特征测试（characterization test）—— 它描述的是这些解析器
「现在」的行为，而非「应该」的行为。接下来要把重复的骨架抽成模板方法，
这些用例的作用是证明抽取前后输出完全一致。

断言走 signal_bus 的 update_parse_list 信号，而不是 parse() 的返回值：
popular 的 parse() 目前不返回节点，走信号对六者是统一的，也顺带覆盖了
base.update_episode_list() 里包装外层根节点、回退节点标题的逻辑。
"""

from util.common.signal_bus import signal_bus
from util.parse.episode.tree import Attribute, EpisodeData

import pytest


@pytest.fixture
def parse_result():
    """侦听解析完成信号，返回 (title, category_name, wrapper_node, current_episode_data)"""
    captured = []

    def on_update(*args):
        captured.append(args)

    signal_bus.parse.update_parse_list.connect(on_update)

    try:
        yield captured
    finally:
        signal_bus.parse.update_parse_list.disconnect(on_update)


@pytest.fixture(autouse = True)
def clean_episode_data():
    EpisodeData.table.clear()
    EpisodeData._active_parsers = 0

    yield

    EpisodeData.table.clear()
    EpisodeData._active_parsers = 0


def run(parser, captured):
    """执行解析并取出信号里的根节点（外层 wrapper 的第一个子节点）"""
    parser.parse()

    assert len(captured) == 1, f"期望发出 1 次解析完成信号，实际 {len(captured)} 次"

    title, category_name, wrapper, current = captured[0]

    return title, category_name, wrapper.child(0)


class TestSpaceParser:
    DATA = {
        "data": {
            "info": {"name": "某UP主", "mid": 123},
            "list": {"vlist": [
                {"aid": 1, "bvid": "BV1", "pic": "cover1", "duration": 90,
                 "created": 1700000000, "title": "投稿A", "season_id": 0,
                 "is_charging_arc": False, "is_lesson_video": False, "is_union_video": False},
                {"aid": 2, "bvid": "BV2", "pic": "cover2", "duration": 120,
                 "created": 1700000001, "title": "充电视频", "season_id": 0,
                 "is_charging_arc": True, "is_lesson_video": False, "is_union_video": False},
            ]},
            "page": {"count": 2},
        }
    }

    def test_tree_shape(self, parse_result):
        from util.parse.episode.space import SpaceEpisodeParser

        title, category, root = run(SpaceEpisodeParser(self.DATA, "PROFILE"), parse_result)

        assert category == "PROFILE"
        assert title == "某UP主"
        assert root.has_attribute(Attribute.TREE_NODE_BIT)
        assert root.count() == 2

    def test_item_fields(self, parse_result):
        from util.parse.episode.space import SpaceEpisodeParser

        _, _, root = run(SpaceEpisodeParser(self.DATA, "PROFILE"), parse_result)
        item = root.child(0)

        assert item.title == "投稿A"
        assert item.bvid == "BV1"
        assert item.aid == 1
        assert item.duration == 90
        assert item.number == 1
        assert item.url == "https://www.bilibili.com/video/BV1"

    def test_badge_and_attributes(self, parse_result):
        from util.parse.episode.space import SpaceEpisodeParser

        _, _, root = run(SpaceEpisodeParser(self.DATA, "PROFILE"), parse_result)

        assert root.child(0).badge == ""
        assert root.child(1).badge == "充电专属"

        for item in (root.child(0), root.child(1)):
            assert item.has_attribute(Attribute.VIDEO_BIT)
            assert item.has_attribute(Attribute.SPACE_BIT)
            assert item.has_attribute(Attribute.NEED_PARSE_BIT)

    def test_owner_written_to_episode_data(self, parse_result):
        from util.parse.episode.space import SpaceEpisodeParser

        _, _, root = run(SpaceEpisodeParser(self.DATA, "PROFILE"), parse_result)
        data = EpisodeData.get_episode_data(root.child(0).episode_id)

        assert data["space_owner"] == "某UP主"
        assert data["space_owner_id"] == 123

    def test_empty_list(self, parse_result):
        from util.parse.episode.space import SpaceEpisodeParser

        empty = {"data": {"info": {"name": "某UP主", "mid": 123},
                          "list": {"vlist": []}, "page": {"count": 0}}}
        _, _, root = run(SpaceEpisodeParser(empty, "PROFILE"), parse_result)

        assert root.count() == 0


class TestWatchLaterParser:
    DATA = {
        "data": {"list": [
            {"aid": 1, "bvid": "BV1", "cid": 11, "pic": "c1", "duration": 60,
             "pubdate": 1700000000, "add_at": 1700000100, "title": "稍后看A"},
            {"aid": 2, "bvid": "BV2", "cid": 22, "pic": "c2", "duration": 80,
             "pubdate": 1700000002, "add_at": 1700000200, "title": "番剧B",
             "bangumi": {"ep_id": 999}, "pgc_label": "第1话"},
        ]}
    }

    def test_tree_and_fields(self, parse_result):
        from util.parse.episode.watch_later import WatchLaterEpisodeParser

        title, category, root = run(WatchLaterEpisodeParser(self.DATA, "WATCH_LATER"), parse_result)

        # 无关键词时节点标题为空，由 update_episode_list 回退为分类名
        assert title == root.number
        assert category == "WATCH_LATER"
        assert root.count() == 2
        assert root.child(0).favtime == 1700000100

    def test_bangumi_entry(self, parse_result):
        from util.parse.episode.watch_later import WatchLaterEpisodeParser

        _, _, root = run(WatchLaterEpisodeParser(self.DATA, "WATCH_LATER"), parse_result)

        assert root.child(0).badge == ""
        assert root.child(0).has_attribute(Attribute.VIDEO_BIT)

        assert root.child(1).badge == "第1话"
        assert root.child(1).ep_id == 999
        assert root.child(1).has_attribute(Attribute.BANGUMI_BIT)

        for item in (root.child(0), root.child(1)):
            assert item.has_attribute(Attribute.WATCH_LATER_BIT)

    def test_none_list(self, parse_result):
        from util.parse.episode.watch_later import WatchLaterEpisodeParser

        _, _, root = run(WatchLaterEpisodeParser({"data": {"list": None}}, "WATCH_LATER"), parse_result)

        assert root.count() == 0

    def test_entry_label_written_to_source_title(self, parse_result):
        """
        入口标签写进 source_title，不写 parent_title

        parent_title 只留给二次解析产出的稿件标题 —— 两个含义共用一个变量时，
        分P条目上的 related_titles 会把入口标签盖掉，编辑器的预览看不出所以然
        """
        from util.parse.episode.watch_later import WatchLaterEpisodeParser

        _, _, root = run(WatchLaterEpisodeParser(self.DATA, "WATCH_LATER"), parse_result)

        data = EpisodeData.get_episode_data(root.child(0).episode_id)

        assert data["source_title"] == "Watch Later"
        assert "parent_title" not in data


class TestFavlistParser:
    DATA = {
        "data": {
            "info": {"title": "我的收藏夹", "id": 5, "upper": {"name": "夹主", "mid": 77}},
            "medias": [
                {"bvid": "BV1", "cover": "c1", "duration": 60, "id": 101,
                 "pubtime": 1700000000, "fav_time": 1700000100, "title": "收藏A", "page": 1},
                {"bvid": "BV2", "cover": "c2", "duration": 70, "id": 102,
                 "pubtime": 1700000001, "fav_time": 1700000200, "title": "分P视频", "page": 3},
                {"bvid": "BV3", "cover": "c3", "duration": 80, "id": 103,
                 "pubtime": 1700000002, "fav_time": 1700000300, "title": "番剧",
                 "intro": "简介", "page": 1, "ogv": {"type_name": "番剧"}},
            ],
        }
    }

    def test_tree_and_title(self, parse_result):
        from util.parse.episode.favlist import FavlistEpisodeParser

        title, _, root = run(FavlistEpisodeParser(self.DATA, "FAVORITES"), parse_result)

        assert title == "我的收藏夹"
        assert root.count() == 3

    def test_badges(self, parse_result):
        from util.parse.episode.favlist import FavlistEpisodeParser

        _, _, root = run(FavlistEpisodeParser(self.DATA, "FAVORITES"), parse_result)

        assert root.child(0).badge == ""
        assert root.child(1).badge == "分P"        # page > 1
        assert root.child(2).badge == "番剧"       # ogv

    def test_ogv_title_merges_intro(self, parse_result):
        from util.parse.episode.favlist import FavlistEpisodeParser

        _, _, root = run(FavlistEpisodeParser(self.DATA, "FAVORITES"), parse_result)

        assert root.child(2).title == "番剧 - 简介"

    def test_attributes(self, parse_result):
        from util.parse.episode.favlist import FavlistEpisodeParser

        _, _, root = run(FavlistEpisodeParser(self.DATA, "FAVORITES"), parse_result)

        assert root.child(0).has_attribute(Attribute.VIDEO_BIT)
        assert root.child(1).has_attribute(Attribute.FAVORITE_WITH_MULTI_PART_VIDEO_BIT)
        assert root.child(2).has_attribute(Attribute.BANGUMI_BIT)

        for i in range(3):
            assert root.child(i).has_attribute(Attribute.FAVLIST_BIT)

    def test_owner_written_to_episode_data(self, parse_result):
        from util.parse.episode.favlist import FavlistEpisodeParser

        _, _, root = run(FavlistEpisodeParser(self.DATA, "FAVORITES"), parse_result)
        data = EpisodeData.get_episode_data(root.child(0).episode_id)

        assert data["favorites_name"] == "我的收藏夹"
        assert data["favorites_id"] == 5
        assert data["favorites_owner"] == "夹主"
        assert data["favorites_owner_id"] == 77

    def test_none_medias(self, parse_result):
        from util.parse.episode.favlist import FavlistEpisodeParser

        empty = {"data": {"info": self.DATA["data"]["info"], "medias": None}}
        _, _, root = run(FavlistEpisodeParser(empty, "FAVORITES"), parse_result)

        assert root.count() == 0


class TestHistoryParser:
    DATA = {
        "data": {"list": [
            {"title": "普通视频", "cover": "c1", "duration": 60, "badge": "",
             "view_at": 1700000000, "uri": "", "show_title": "",
             "history": {"bvid": "BV1", "cid": 11, "epid": 0, "business": "archive"}},
            {"title": "番剧", "cover": "c2", "duration": 70, "badge": "番剧",
             "view_at": 1700000001, "uri": "https://example.com/ep1", "show_title": "第1话",
             "history": {"bvid": "BV2", "cid": 22, "epid": 555, "business": "pgc"}},
            {"title": "失效视频", "cover": "c3", "duration": 0, "badge": "",
             "view_at": 1700000002, "uri": "", "show_title": "",
             "history": {"bvid": "BV3", "cid": 33, "epid": 0, "business": "archive"}},
        ]}
    }

    def test_titles_and_urls(self, parse_result):
        from util.parse.episode.history import HistoryEpisodeParser

        _, _, root = run(HistoryEpisodeParser(self.DATA, "HISTORY"), parse_result)

        assert root.child(0).title == "普通视频"
        assert root.child(0).url == "https://www.bilibili.com/video/BV1"

        # pgc 且有 show_title 时合并标题；uri 非空时优先用 uri
        assert root.child(1).title == "番剧 - 第1话"
        assert root.child(1).url == "https://example.com/ep1"

    def test_expired_entry(self, parse_result):
        from util.parse.episode.history import HistoryEpisodeParser

        _, _, root = run(HistoryEpisodeParser(self.DATA, "HISTORY"), parse_result)

        assert root.child(2).expired is True
        assert root.child(2).badge != ""     # 失效条目显示提示文案
        assert root.child(0).expired is False

    def test_business_maps_to_attribute(self, parse_result):
        from util.parse.episode.history import HistoryEpisodeParser

        _, _, root = run(HistoryEpisodeParser(self.DATA, "HISTORY"), parse_result)

        assert root.child(0).has_attribute(Attribute.VIDEO_BIT)
        assert root.child(1).has_attribute(Attribute.BANGUMI_BIT)

        for i in range(3):
            assert root.child(i).has_attribute(Attribute.HISTORY_BIT)

    def test_entry_label_written_to_source_title(self, parse_result):
        # 入口标签走 source_title，parent_title 留给二次解析产出的稿件标题
        from util.parse.episode.history import HistoryEpisodeParser

        _, _, root = run(HistoryEpisodeParser(self.DATA, "HISTORY"), parse_result)

        data = EpisodeData.get_episode_data(root.child(0).episode_id)

        assert data["source_title"] == "History"
        assert "parent_title" not in data

    def test_unknown_business_still_gets_a_media_bit(self, parse_result):
        """
        business 是 B 站自己的判别字段，取值会陆续增加

        漏掉它的时候（这里的分支曾经没有 default），条目只带 HISTORY|NEED_PARSE，
        一个媒体形态位都没有 —— 二次解析走到无分支可走的那一步，抛出的
        UnboundLocalError 被原样塞进提示框，用户只看到一个 Python 变量名
        """
        from util.parse.episode.history import HistoryEpisodeParser

        data = {"data": {"list": [
            {"title": "某种新内容", "cover": "c9", "duration": 30, "badge": "",
             "view_at": 1700000009, "uri": "", "show_title": "",
             "history": {"bvid": "BV9", "cid": 99, "epid": 0, "business": "live"}},
        ]}}

        _, _, root = run(HistoryEpisodeParser(data, "HISTORY"), parse_result)

        assert root.child(0).has_attribute(Attribute.VIDEO_BIT)
        assert root.child(0).has_attribute(Attribute.HISTORY_BIT)


class TestPopularParser:
    DATA = {
        "data": {
            "config": {"label": "每周必看 第1期"},
            "list": [
                {"aid": 1, "bvid": "BV1", "cid": 11, "pic": "c1", "duration": 60,
                 "pubdate": 1700000000, "title": "入选A"},
            ],
        }
    }

    def test_tree_and_fields(self, parse_result):
        from util.parse.episode.popular import PopularEpisodeParser

        title, category, root = run(PopularEpisodeParser(self.DATA, "WEEKLY"), parse_result)

        assert title == "每周必看 第1期"
        assert category == "WEEKLY"
        assert root.count() == 1
        assert root.child(0).cid == 11

    def test_attributes(self, parse_result):
        from util.parse.episode.popular import PopularEpisodeParser

        _, _, root = run(PopularEpisodeParser(self.DATA, "WEEKLY"), parse_result)

        assert root.child(0).has_attribute(Attribute.VIDEO_BIT)
        assert root.child(0).has_attribute(Attribute.WEEKLY_BIT)

    def test_issue_label_written_to_source_title(self, parse_result):
        # 每周必看的条目从不二次解析，没有结构上级 —— 期号是「来源列表名称」
        from util.parse.episode.popular import PopularEpisodeParser

        _, _, root = run(PopularEpisodeParser(self.DATA, "WEEKLY"), parse_result)

        assert root.child(0).related_titles["source_title"] == "每周必看 第1期"


class TestAudioParser:
    # AudioEpisodeParser 取 info_data["data"] 之后再取里面的 data ——
    # menu_title 与歌曲列表是同一层的兄弟键
    DATA = {
        "data": {
            "menu_title": "我的歌单",
            "data": [
                {"cover": "c1", "duration": 60, "passtime": 1700000000, "title": "歌曲A",
                 "author": "歌手", "statistic": {"sid": 111}},
            ],
        }
    }

    def test_song_title_written_to_source_title(self, parse_result):
        # 音频走 related_titles（它没有 episode_id，不经过 EpisodeData）
        from util.parse.episode.audio import AudioEpisodeParser

        _, _, root = run(AudioEpisodeParser(self.DATA, "AUDIO"), parse_result)

        assert root.child(0).related_titles["source_title"] == "我的歌单"


class TestListParser:
    DATA = {
        "data": {
            "meta": {"title": "我的合集"},
            "archives": [
                {"aid": 1, "bvid": "BV1", "pic": "c1", "duration": 60,
                 "pubdate": 1700000000, "title": "合集视频A"},
            ],
        }
    }

    def test_tree_and_title(self, parse_result):
        from util.parse.episode.list import ListEpisodeParser

        title, _, root = run(ListEpisodeParser(self.DATA, "COLLECTION"), parse_result)

        assert title == "我的合集"
        assert root.count() == 1

    def test_falls_back_to_name(self, parse_result):
        from util.parse.episode.list import ListEpisodeParser

        data = {"data": {"meta": {"name": "备用名"}, "archives": []}}
        title, _, _ = run(ListEpisodeParser(data, "COLLECTION"), parse_result)

        assert title == "备用名"

    def test_attributes(self, parse_result):
        from util.parse.episode.list import ListEpisodeParser

        _, _, root = run(ListEpisodeParser(self.DATA, "COLLECTION"), parse_result)
        item = root.child(0)

        for attr in (Attribute.COLLECTION_LIST_BIT, Attribute.COLLECTION_BIT,
                     Attribute.VIDEO_BIT, Attribute.NEED_PARSE_BIT):
            assert item.has_attribute(attr)

    def test_collection_title_written_to_episode_data(self, parse_result):
        from util.parse.episode.list import ListEpisodeParser

        _, _, root = run(ListEpisodeParser(self.DATA, "COLLECTION"), parse_result)

        assert EpisodeData.get_episode_data(root.child(0).episode_id)["collection_title"] == "我的合集"


class TestNumbering:
    """六者共用的序号规则：从 1 开始、按列表顺序连续递增"""

    def test_sequential(self, parse_result):
        from util.parse.episode.space import SpaceEpisodeParser

        data = {"data": {"info": {"name": "u", "mid": 1}, "page": {"count": 3},
                         "list": {"vlist": [
                             {"aid": i, "bvid": f"BV{i}", "pic": "", "duration": 1,
                              "created": 0, "title": f"v{i}", "season_id": 0,
                              "is_charging_arc": False, "is_lesson_video": False,
                              "is_union_video": False}
                             for i in range(3)
                         ]}}}

        _, _, root = run(SpaceEpisodeParser(data, "PROFILE"), parse_result)

        assert [root.child(i).number for i in range(3)] == [1, 2, 3]
