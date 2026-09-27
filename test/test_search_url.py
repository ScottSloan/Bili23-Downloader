"""
util/parse/search_url.py —— 搜索关键词与链接的互转。

2.14.0 起关键词一律随链接传递，翻页、自动解析分页、解析历史全都直接复用链接，
不再单独维护搜索状态。也就是说这组函数一旦出错，表现不是"搜索坏了"，
而是"翻到第二页搜索条件丢了"或"解析历史点回去变成了全量列表"。

TODO.md 里下个版本的分区/排序筛选计划沿用同一套机制，这些用例同时是那次改动的护栏。
"""

from util.parse.search_url import (
    get_keyword_param, support_search, extract_keyword, build_search_url
)

import pytest


SPACE = "https://space.bilibili.com/123"
FAVLIST = "https://space.bilibili.com/123/favlist"
WATCH_LATER = "bili23://watch_later"
HISTORY = "bili23://history"
VIDEO = "https://www.bilibili.com/video/BV1xx411c7mD"
COLLECTION = "https://www.bilibili.com/list/456"


class TestSupportMatrix:
    @pytest.mark.parametrize(
        "url, param",
        [
            (SPACE, "keyword"),
            (FAVLIST, "keyword"),
            (HISTORY, "keyword"),
            (WATCH_LATER, "key"),   # 稍后再看接口用的参数名与其余三者不同
        ],
    )
    def test_supported(self, url, param):
        assert get_keyword_param(url) == param
        assert support_search(url) is True

    @pytest.mark.parametrize("url", [VIDEO, COLLECTION, "https://example.com/"])
    def test_unsupported(self, url):
        # 合集、每周必看等接口没有搜索参数，必须明确返回不支持，
        # 否则界面会给出服务端搜索的入口，实际却只能筛当前页
        assert get_keyword_param(url) == ""
        assert support_search(url) is False


class TestExtract:
    def test_percent_decoding(self):
        assert extract_keyword(f"{SPACE}?keyword=%E6%B5%8B%E8%AF%95") == "测试"

    def test_uses_type_specific_param(self):
        assert extract_keyword(f"{WATCH_LATER}?key=abc") == "abc"
        # 参数名不匹配时不应误读
        assert extract_keyword(f"{WATCH_LATER}?keyword=abc") == ""

    def test_strips_whitespace(self):
        assert extract_keyword(f"{SPACE}?keyword=%20abc%20") == "abc"

    def test_absent_and_unsupported(self):
        assert extract_keyword(SPACE) == ""
        assert extract_keyword(f"{VIDEO}?keyword=x") == ""


class TestBuild:
    def test_write(self):
        assert extract_keyword(build_search_url(SPACE, "测试")) == "测试"

    def test_overwrite(self):
        assert extract_keyword(build_search_url(f"{SPACE}?keyword=old", "new")) == "new"

    def test_empty_keyword_removes_param(self):
        # 清空关键词即恢复完整列表，参数必须被移除而不是留成 keyword=
        assert "keyword" not in build_search_url(f"{SPACE}?keyword=old", "")

    def test_unsupported_url_returned_unchanged(self):
        assert build_search_url(VIDEO, "x") == VIDEO

    def test_preserves_other_params(self):
        result = build_search_url(f"{SPACE}?tid=1&order=pubdate", "测试")

        assert "tid=1" in result
        assert "order=pubdate" in result
        assert extract_keyword(result) == "测试"

    @pytest.mark.parametrize("keyword", ["测试", "a b", "a&b=c", "100%", "a/b"])
    def test_roundtrip(self, keyword):
        # 关键词里可能出现任何字符，写入再读出必须完全一致，
        # 否则翻页会带着被破坏的关键词去请求接口
        assert extract_keyword(build_search_url(SPACE, keyword)) == keyword
