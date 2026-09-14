"""
util/common/data/url_pattern.py —— 链接到解析类型的分发表。

这张表是**顺序敏感**的：space.bilibili.com/{mid}/lists 与 /favlist 都能被
兜底的 space 规则匹配上，只有排在它之前才会被正确识别。调整表内顺序
（哪怕只是"整理一下"）就会把个人空间以外的类型全部吞掉，而这类回归
在界面上表现为"解析出来的是 UP 主主页而不是收藏夹"，不易第一时间归因。
"""

from util.common.data import url_patterns

import pytest


def match_parser_type(url: str):
    """复刻 search_url.get_keyword_param 与各 parser 的分发逻辑：取首个命中的规则"""
    for parser_type, pattern in url_patterns:
        if pattern.search(url):
            return parser_type

    return None


@pytest.mark.parametrize(
    "url, expected",
    [
        # 完整链接
        ("https://www.bilibili.com/video/BV1xx411c7mD", "video"),
        ("https://www.bilibili.com/bangumi/play/ep123", "bangumi"),
        ("https://www.bilibili.com/bangumi/media/md123", "bangumi"),
        ("https://www.bilibili.com/cheese/play/ss123", "cheese"),
        ("https://mall.bilibili.com/lesson/play?id=1", "lesson"),
        ("https://www.bilibili.com/v/popular/weekly", "popular"),
        ("https://www.bilibili.com/festival/abc", "festival"),
        ("https://b23.tv/abcdef", "b23"),
        ("https://bili2233.cn/abcdef", "b23"),

        # 顺序敏感：以下三条都能被兜底的 space 规则匹配，靠表内顺序区分
        ("https://space.bilibili.com/123/lists", "list"),
        ("https://space.bilibili.com/123/favlist", "favlist"),
        ("https://space.bilibili.com/123", "space"),

        # 同样顺序敏感：/list/ml{id} 是收藏夹，/list/{id} 才是合集
        ("https://www.bilibili.com/list/ml456", "favlist"),
        ("https://www.bilibili.com/list/456", "list"),

        # 程序内部使用的伪协议
        ("bili23://watch_later", "watch_later"),
        ("bili23://history", "history"),

        # 裸 ID
        ("BV1xx411c7mD", "video"),
        ("av123", "video"),
        ("ep456", "bangumi"),
        ("ss456", "bangumi"),
        ("au789", "audio"),
        ("am789", "audio"),
    ],
)
def test_dispatch(url, expected):
    assert match_parser_type(url) == expected


def test_query_string_does_not_affect_dispatch():
    # 搜索关键词随链接传递，附加查询参数不得改变解析类型
    assert match_parser_type("https://space.bilibili.com/123?keyword=x") == "space"
    assert match_parser_type("https://space.bilibili.com/123/favlist?keyword=x") == "favlist"


def test_unknown_url():
    assert match_parser_type("https://example.com/") is None
