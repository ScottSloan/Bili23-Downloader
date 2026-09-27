"""
util/parse/parser/list.py —— 合集/系列播放页链接的解析分支。

播放页链接（www.bilibili.com/list/{mid}?…）是合集/系列播放页地址栏里的形式，
列表身份并不总是写在链接里：sid 指向的可能是合集也可能是系列，只给了视频时更是
完全没提。判断只能靠请求接口，所以这里把网络层打桩，断言"哪种链接走了哪几个接口、
用的是哪几个 id"。

这类改动出错时不会报错，而是解析出错误的列表甚至空列表：合集与系列的接口对
"id 存在但不属于本类型"的容忍度不一样（系列接口明确报错 147002，合集接口只有
id 不存在时才报错），走错了也未必有异常。因此用例盯的是请求本身，而不是最终列表。
"""

from util.common.signal_bus import signal_bus
from util.common.config import config
from util.parse.episode.tree import EpisodeData
from util.parse.parser import list as list_module
from util.parse.parser.list import ListParser

import pytest


BVID = "BV1xx411c7mD"

ARCHIVE = {
    "aid": 123,
    "bvid": BVID,
    "pic": "https://example.com/cover.jpg",
    "pubdate": 1700000000,
    "title": "测试视频",
    "duration": 100,
}

VIEW = {
    "code": 0,
    "data": {
        "bvid": BVID,
        "aid": 123,
        "cid": 456,
        # 合集归属由接口给出：链接路径里的数字未必与它一致，用例据此断言取值来源
        "ugc_season": {"id": 789, "mid": 99999, "title": "测试合集"},
    }
}

VIEW_WITHOUT_SEASON = {
    "code": 0,
    "data": {"bvid": BVID, "aid": 123, "cid": 456},
}

SEASON_ARCHIVES = {
    "code": 0,
    "data": {
        "meta": {"season_id": 789, "mid": 99999, "title": "测试合集", "name": "合集·测试合集", "total": 1},
        "page": {"page_num": 1, "page_size": 30, "total": 1},
        "archives": [ARCHIVE],
    },
}

SERIES_META = {
    "code": 0,
    "data": {"meta": {"series_id": 1462496, "mid": 12345, "name": "测试系列", "total": 1}},
}

# 非系列的 id 落到系列元信息接口上时，B 站返回的就是这个
SERIES_NOT_FOUND = {"code": 147002, "message": "视频列表已失效"}

SERIES_ARCHIVES = {
    "code": 0,
    "data": {
        "aids": [123],
        "page": {"num": 1, "size": 30, "total": 1},
        "archives": [ARCHIVE],
    },
}


class StubNetwork:
    """按关键字匹配返回预置响应的网络桩，同时记录请求顺序"""

    def __init__(self):
        self.calls: list[str] = []
        self.routes: list[tuple[str, dict]] = []

    def route(self, keyword: str, response: dict):
        self.routes.append((keyword, response))

        return self

    def request_class(self):
        network = self

        class StubRequest:
            def __init__(self, url, **kwargs):
                self.url = url

            def run(self):
                network.calls.append(self.url)

                for keyword, response in network.routes:
                    if keyword in self.url:
                        return response

                raise AssertionError(f"未打桩的请求：{self.url}")

        return StubRequest

    def urls(self, keyword: str):
        return [url for url in self.calls if keyword in url]


@pytest.fixture(autouse = True)
def clean_episode_data():
    EpisodeData.table.clear()
    EpisodeData._active_parsers = 0

    yield

    EpisodeData.table.clear()
    EpisodeData._active_parsers = 0


@pytest.fixture(autouse = True)
def wbi_keys():
    """
    view 接口带 wbi 签名，签名用的两个 key 平时由 cookie 刷新流程写入，
    测试环境里是空串。空串会在 enc_wbi 里直接下标越界，且两个 key 拼起来
    必须够 mixinKeyEncTab 用的 64 位，所以这里填满 32 位各一份。
    """
    config.set(config.img_key, "a" * 32)
    config.set(config.sub_key, "b" * 32)

    yield

    config.set(config.img_key, "")
    config.set(config.sub_key, "")


@pytest.fixture
def network(monkeypatch):
    stub = StubNetwork()

    monkeypatch.setattr(list_module, "SyncNetWorkRequest", stub.request_class())

    return stub


@pytest.fixture
def parse_result():
    """侦听解析完成信号，返回 (title, category_name, node, current_episode_data)"""
    captured = []

    def on_update(*args):
        captured.append(args)

    signal_bus.parse.update_parse_list.connect(on_update)

    try:
        yield captured
    finally:
        signal_bus.parse.update_parse_list.disconnect(on_update)


def parse(url: str):
    parser = ListParser()
    parser.parse(url, 1)

    return parser


def test_play_page_takes_season_from_video(network, parse_result):
    # 链接只给了视频，合集身份向视频反查；mid 与被请求的 season_id 都以接口为准
    network.route("web-interface/wbi/view", VIEW)
    network.route("seasons_archives_list", SEASON_ARCHIVES)

    parse(f"https://www.bilibili.com/list/12345/?oid=123&bvid={BVID}")

    assert len(network.calls) == 2, "播放页链接应只发一次视频接口、一次合集接口"
    assert "bvid=" + BVID in network.calls[0]

    season_url = network.urls("seasons_archives_list")[0]

    assert "season_id=789" in season_url
    assert "mid=99999" in season_url, "mid 应取接口返回的，而不是链接路径里的 12345"

    # 信号里是外层 wrapper，它的第一个子节点才是合集节点，再往下才是条目
    title, category_name, wrapper, current = parse_result[0]

    assert category_name == "COLLECTION_LIST"
    assert title == "测试合集"
    assert current == ("bvid", BVID), "链接指向的视频应交给解析列表定位"
    assert wrapper.child(0).child(0).bvid == BVID, "定位用的字段必须真的存在于条目上"


def test_play_page_by_oid_only(network):
    # 少数链接只有 oid，同样按 aid 去查，不另做 av→BV 换算
    network.route("web-interface/wbi/view", VIEW)
    network.route("seasons_archives_list", SEASON_ARCHIVES)

    parse("https://www.bilibili.com/list/12345?oid=123")

    assert "aid=123" in network.calls[0]


def test_play_page_video_without_season_raises(network):
    # 视频不属于任何合集时链接里没有可解析的列表，报错而不是解析出一个空合集
    network.route("web-interface/wbi/view", VIEW_WITHOUT_SEASON)

    with pytest.raises(ValueError):
        parse(f"https://www.bilibili.com/list/12345?oid=123&bvid={BVID}")

    assert len(network.calls) == 1


def test_play_page_sid_series(network):
    # sid 是系列：探针命中后直接复用它的 meta，不再重复请求一次
    network.route("x/series/series", SERIES_META)
    network.route("x/series/archives", SERIES_ARCHIVES)

    parse("https://www.bilibili.com/list/12345?sid=1462496")

    assert len(network.urls("x/series/series")) == 1, "探针拿到的 meta 应被复用"
    assert "series_id=1462496" in network.urls("x/series/archives")[0]
    assert network.urls("seasons_archives_list") == [], "探针命中系列后不应再查合集"


def test_play_page_sid_beats_the_season_of_the_video(network):
    # 链接同时给了 sid 和视频，且 sid 指的不是视频所在的合集：以链接为准 ——
    # B 站的标准链接（?sid=…&oid=…&bvid=…）里 sid 就是页面正在播放的那个列表
    network.route("web-interface/wbi/view", VIEW)
    network.route("x/series/series", SERIES_META)
    network.route("x/series/archives", SERIES_ARCHIVES)

    parse(f"https://www.bilibili.com/list/12345?sid=1462496&oid=123&bvid={BVID}")

    assert network.urls("seasons_archives_list") == [], "sid 明说了是系列，不该解析成视频的合集"
    assert "series_id=1462496" in network.urls("x/series/archives")[0]


def test_play_page_sid_matching_the_video_season_skips_the_probe(network):
    # sid 与视频所属的合集一致（就是合集播放页的标准链接），不必再去探系列接口
    network.route("web-interface/wbi/view", VIEW)
    network.route("seasons_archives_list", SEASON_ARCHIVES)

    parse(f"https://www.bilibili.com/list/12345?sid=789&oid=123&bvid={BVID}")

    assert len(network.calls) == 2, "能靠视频判断就不该多打一次探针"
    assert "season_id=789" in network.urls("seasons_archives_list")[0]


def test_play_page_sid_season(network):
    # sid 是合集：探针不命中，转去查合集。此前这里一律当系列查，
    # 结果是空列表 + "视频列表已失效"
    network.route("x/series/series", SERIES_NOT_FOUND)
    network.route("seasons_archives_list", SEASON_ARCHIVES)

    parse("https://www.bilibili.com/list/12345?sid=789")

    assert "season_id=789" in network.urls("seasons_archives_list")[0]
    assert network.urls("x/series/archives") == []


def test_play_page_without_list_raises(network):
    # 合集索引页（没有 sid / oid / bvid）仍然解析不了，且不应发出请求
    with pytest.raises(ValueError):
        parse("https://www.bilibili.com/list/456")

    assert network.calls == []


def test_get_bvid_skips_query_key():
    # 链接里的 "bvid=" 自带 "bv"，正则若不在参数值上匹配就会取回 "bvid" 本身
    parser = ListParser()
    parser.url = f"https://www.bilibili.com/list/12345?oid=123&bvid={BVID}"

    assert parser.get_bvid() == BVID
    assert parser.get_mid() == "12345", "mid 不应被查询串里的数字干扰"
