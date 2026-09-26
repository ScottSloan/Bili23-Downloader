"""
util/parse/parser/space.py —— 个人空间解析的用户名缓存。

Data.uname_map 是一张进程级缓存，用来避免翻页时重复请求用户名接口。
它此前是失效的：命中分支忘了 return，走完 update_space_owner_info() 后
继续往下发请求，缓存等于没有。表现上没有任何异常 —— 只是每翻一页多打一次
接口，多一分触发风控的概率。

这类"少写一行 return"的回归不会被任何功能测试发现，只能由针对缓存本身的
用例守住，因此这里把网络层打桩，直接断言请求次数。
"""

from util.parse.parser import space as space_module
from util.parse.parser.space import SpaceParser, Data

import pytest


@pytest.fixture(autouse = True)
def clear_cache():
    Data.uname_map.clear()

    yield

    Data.uname_map.clear()


@pytest.fixture
def stub_request(monkeypatch):
    """把 SyncNetWorkRequest 换成计数桩，记录每次请求的地址"""
    calls: list[str] = []

    class StubRequest:
        def __init__(self, url, **kwargs):
            self.url = url

        def run(self):
            calls.append(self.url)

            return {
                "code": 0,
                "data": {"card": {"name": "测试UP主"}},
            }

    monkeypatch.setattr(space_module, "SyncNetWorkRequest", StubRequest)

    return calls


def make_parser(mid: str = "123"):
    parser = SpaceParser()
    parser.mid = mid
    parser.info_data = {"data": {}}

    return parser


def test_first_call_requests_and_fills_cache(stub_request):
    parser = make_parser()
    parser.get_uname()

    assert len(stub_request) == 1
    assert Data.uname_map["123"] == "测试UP主"
    assert parser.info_data["data"]["info"] == {"name": "测试UP主", "mid": "123"}


def test_cache_hit_does_not_request(stub_request):
    make_parser().get_uname()
    assert len(stub_request) == 1

    # 第二次（翻页）必须完全走缓存
    parser = make_parser()
    parser.get_uname()

    assert len(stub_request) == 1, "缓存命中后仍然发起了请求，return 丢失"
    # 且仍要正确写入 owner 信息，否则命名规则里的 {space_owner} 会空掉
    assert parser.info_data["data"]["info"] == {"name": "测试UP主", "mid": "123"}


def test_different_mid_requests_again(stub_request):
    make_parser("123").get_uname()
    make_parser("456").get_uname()

    assert len(stub_request) == 2
    assert set(Data.uname_map) == {"123", "456"}
