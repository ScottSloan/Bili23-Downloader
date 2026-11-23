import pytest

from PySide6.QtCore import QSize

import util.download.cover.query_worker as query_worker_module
from util.download.cover.query_worker import CoverQueryWorker


class _FakeRequest:
    """按 url 关键字路由的假请求

    注意：不模拟业务错误码异常。SyncNetWorkRequest 只封装网络请求，
    code != 0 的判断在 ParserBase.check_response 里，不在网络层。
    """

    responses = {}
    requests = []

    def __init__(self, url, *args, **kwargs):
        self.url = url

    def run(self):
        _FakeRequest.requests.append(self.url)

        for fragment, response in _FakeRequest.responses.items():
            if fragment in self.url:
                return response

        return {}


def _reset_fake(folder_info = None, resource_list = None, extra = None):
    _FakeRequest.requests.clear()
    _FakeRequest.responses = {}

    if folder_info is not None:
        _FakeRequest.responses["/x/v3/fav/folder/info"] = folder_info

    if resource_list is not None:
        _FakeRequest.responses["/x/v3/fav/resource/list"] = resource_list

    if extra is not None:
        _FakeRequest.responses.update(extra)


def _build_worker(monkeypatch, media_id = "123", api_url = "https://api.bilibili.com/x/v3/fav/resource/list", fallback = True):
    monkeypatch.setattr(query_worker_module, "SyncNetWorkRequest", _FakeRequest)

    return CoverQueryWorker(
        model = None,
        cover_key = f"__query__{media_id}@120x67",
        cover_url = media_id,
        cover_size = QSize(120, 67),
        query_param = {
            "api_url": api_url,
            "params": {"media_id": media_id},
            "fallback_first_media_cover": fallback,
        },
    )


class _StubManager:
    """只替换 cover_manager 的 query/create，保留 arrange_cover_id/arrange_cover_key 逻辑"""

    def __init__(self):
        self.queried = []
        self.created = []

    def query(self, key):
        self.queried.append(key)
        return None

    def create(self, key, data):
        self.created.append(key)

    def arrange_cover_id(self, cover_url: str):
        from hashlib import md5
        return md5(cover_url.encode("utf-8")).hexdigest()

    def arrange_cover_key(self, cover_id: str, cover_size: QSize):
        return f"{cover_id}@{cover_size.width()}x{cover_size.height()}"


# ---- 封面取值顺序 ----

def test_query_url_uses_info_cover_when_set(monkeypatch):
    # 收藏夹设置了封面：直接用 data.info.cover，不读 medias
    _reset_fake(resource_list = {
        "data": {
            "info": {"cover": "https://i0.hdslb.com/folder.jpg"},
            "medias": [{"cover": "https://i0.hdslb.com/first.jpg"}],
        }
    })

    worker = _build_worker(monkeypatch)

    assert worker.query_url() is True
    assert worker.cover_url == "https://i0.hdslb.com/folder.jpg"


def test_query_url_falls_back_to_medias_cover(monkeypatch):
    # 收藏夹未设封面：data.info.cover 为空，回退到 data.medias[0].cover
    _reset_fake(resource_list = {
        "data": {
            "info": {"cover": ""},
            "medias": [{"cover": "https://i0.hdslb.com/first.jpg"}],
        }
    })

    worker = _build_worker(monkeypatch)

    assert worker.query_url() is True
    assert worker.cover_url == "https://i0.hdslb.com/first.jpg"


def test_query_url_medias_none_returns_false(monkeypatch):
    # 实测空收藏夹（test）的 resource/list 返回 medias: null 而非 []
    _reset_fake(resource_list = {"data": {"info": {"cover": ""}, "medias": None}})

    worker = _build_worker(monkeypatch)

    assert worker.query_url() is False
    assert worker.cover_url == "123"
    assert worker.cache_key == worker.cover_key


def test_query_url_medias_empty_list_returns_false(monkeypatch):
    # 与上面等价：medias 为 [] 而非 null
    _reset_fake(resource_list = {"data": {"info": {"cover": ""}, "medias": []}})

    worker = _build_worker(monkeypatch)

    assert worker.query_url() is False


def test_query_url_first_media_no_cover_returns_without_raise(monkeypatch):
    # 只取第一个视频封面：第一条无 cover 时不遍历后续，返回 False
    _reset_fake(resource_list = {
        "data": {
            "info": {"cover": ""},
            "medias": [{"cover": ""}, {"cover": "https://i0.hdslb.com/second.jpg"}],
        }
    })

    worker = _build_worker(monkeypatch)

    assert worker.query_url() is False
    assert worker.cover_url == "123"


# ---- 业务错误仍 raise ----

def test_query_url_raises_when_data_missing(monkeypatch):
    # 业务错误、响应中没有 data 键
    _reset_fake(resource_list = {"code": -412, "message": "请求被拦截"})

    worker = _build_worker(monkeypatch)

    with pytest.raises(ValueError, match = "获取封面 URL 失败"):
        worker.query_url()


def test_query_url_raises_when_data_is_null(monkeypatch):
    # 业务错误、data 为 null
    _reset_fake(resource_list = {"code": -412, "message": "请求被拦截", "data": None})

    worker = _build_worker(monkeypatch)

    with pytest.raises(ValueError, match = "获取封面 URL 失败"):
        worker.query_url()


# ---- URL 参数 ----

def test_query_url_fallback_url_params(monkeypatch):
    # resource/list 的 URL 应携带 media_id / pn=1 / ps=1 / order=mtime
    _reset_fake(resource_list = {
        "data": {"info": {"cover": "https://i0.hdslb.com/folder.jpg"}, "medias": []}
    })

    worker = _build_worker(monkeypatch, media_id = "456")

    worker.query_url()

    url = _FakeRequest.requests[0]

    assert "media_id=456" in url
    assert "pn=1" in url
    assert "ps=1" in url
    assert "order=mtime" in url


# ---- 显式开关 ----

def test_query_url_switch_off_reads_data_cover(monkeypatch):
    # 开关关闭：按原约定从 data.cover 读，不读 data.info.cover
    _reset_fake(folder_info = {"data": {"cover": "https://i0.hdslb.com/folder.jpg"}})

    worker = _build_worker(
        monkeypatch,
        api_url = "https://api.bilibili.com/x/v3/fav/folder/info",
        fallback = False,
    )

    assert worker.query_url() is True
    assert worker.cover_url == "https://i0.hdslb.com/folder.jpg"


def test_query_url_switch_off_empty_returns_false(monkeypatch):
    # 开关关闭、cover 为空：返回 False，不触发 medias 读取
    _reset_fake(folder_info = {"data": {"cover": ""}})

    worker = _build_worker(
        monkeypatch,
        api_url = "https://api.bilibili.com/x/v3/fav/folder/info",
        fallback = False,
    )

    assert worker.query_url() is False


# ---- 键拆分 ----

def test_query_url_does_not_recompute_cover_key(monkeypatch):
    # 键一致性回归测试：query_url 成功后 cover_key 必须保持发起请求时的形态
    _reset_fake(resource_list = {
        "data": {"info": {"cover": "https://i0.hdslb.com/folder.jpg"}, "medias": []}
    })

    worker = _build_worker(monkeypatch, media_id = "456")

    original_key = worker.cover_key
    worker.query_url()

    assert worker.cover_key == original_key
    assert worker.cover_key == "__query__456@120x67"


def test_cache_key_defaults_to_cover_key(monkeypatch):
    monkeypatch.setattr(query_worker_module, "SyncNetWorkRequest", _FakeRequest)

    worker = CoverQueryWorker(
        model = None,
        cover_key = "abc@120x67",
        cover_url = "https://i0.hdslb.com/x.jpg",
        cover_size = QSize(120, 67),
        query_param = None,
    )

    assert worker.cache_key == "abc@120x67"


def test_query_url_sets_cache_key_from_cover_url(monkeypatch):
    _reset_fake(resource_list = {
        "data": {"info": {"cover": "https://i0.hdslb.com/folder.jpg"}, "medias": []}
    })

    from hashlib import md5

    worker = _build_worker(monkeypatch, media_id = "456")

    worker.query_url()

    expected = f"{md5('https://i0.hdslb.com/folder.jpg'.encode('utf-8')).hexdigest()}@120x67"

    assert worker.cache_key == expected
    assert worker.cover_key == "__query__456@120x67"


def test_query_cache_uses_cache_key(monkeypatch):
    from util.download.cover import manager as manager_module

    stub = _StubManager()
    monkeypatch.setattr(manager_module, "cover_manager", stub)

    _reset_fake(resource_list = {
        "data": {"info": {"cover": "https://i0.hdslb.com/folder.jpg"}, "medias": []}
    })

    worker = _build_worker(monkeypatch)

    worker.query_url()
    worker.query_cache()

    from hashlib import md5
    expected = f"{md5('https://i0.hdslb.com/folder.jpg'.encode('utf-8')).hexdigest()}@120x67"

    assert stub.queried == [expected]


def test_save_cache_uses_cache_key(monkeypatch):
    from util.download.cover import manager as manager_module

    stub = _StubManager()
    monkeypatch.setattr(manager_module, "cover_manager", stub)

    worker = CoverQueryWorker(
        model = None,
        cover_key = "__query__456@120x67",
        cover_url = "https://i0.hdslb.com/folder.jpg",
        cover_size = QSize(120, 67),
        query_param = None,
    )

    worker.cache_key = "custom_key@120x67"
    worker.save_cache(b"\x00")

    assert stub.created == ["custom_key@120x67"]


# ---- _run 整体流程 ----

def test_run_empty_favlist_does_not_notify_failed(monkeypatch):
    # 空收藏夹：resource/list 一次请求返回 info.cover 为空、medias 为 null。
    # query_url 返回 False，_run 直接 return，notify_failed 一次都不调用
    _reset_fake(resource_list = {"data": {"info": {"cover": ""}, "medias": None}})

    worker = _build_worker(monkeypatch)

    failed = []
    monkeypatch.setattr(worker, "notify_failed", lambda: failed.append(True))

    worker._run()

    assert failed == []
    assert len(_FakeRequest.requests) == 1


def test_run_business_error_notifies_failed(monkeypatch):
    # 业务错误：data 缺失 → raise → notify_failed
    _reset_fake(resource_list = {"code": -412, "message": "请求被拦截"})

    worker = _build_worker(monkeypatch)

    failed = []
    monkeypatch.setattr(worker, "notify_failed", lambda: failed.append(True))

    worker._run()

    assert failed == [True]


def test_run_skips_query_url_when_query_param_none(monkeypatch):
    _reset_fake()

    worker = CoverQueryWorker(
        model = None,
        cover_key = "k@120x67",
        cover_url = "https://i0.hdslb.com/x.jpg",
        cover_size = QSize(120, 67),
        query_param = None,
    )

    called = []
    monkeypatch.setattr(worker, "query_url", lambda: called.append(True) or True)
    monkeypatch.setattr(worker, "query_cache", lambda: object())
    monkeypatch.setattr(worker, "return_to_model", lambda image: None)

    worker._run()

    assert called == []


def test_run_empty_cover_does_not_notify_failed(monkeypatch):
    _reset_fake()

    worker = CoverQueryWorker(
        model = None,
        cover_key = "k@120x67",
        cover_url = "",
        cover_size = QSize(120, 67),
        query_param = None,
    )

    monkeypatch.setattr(query_worker_module, "SyncNetWorkRequest", _FakeRequest)

    failed = []
    monkeypatch.setattr(worker, "notify_failed", lambda: failed.append(True))

    worker._run()

    assert failed == []
    assert _FakeRequest.requests == []


def test_run_cover_url_zero_treats_as_empty(monkeypatch):
    _reset_fake()

    worker = CoverQueryWorker(
        model = None,
        cover_key = "__query__0@120x67",
        cover_url = 0,
        cover_size = QSize(120, 67),
        query_param = None,
    )

    monkeypatch.setattr(query_worker_module, "SyncNetWorkRequest", _FakeRequest)

    failed = []
    monkeypatch.setattr(worker, "notify_failed", lambda: failed.append(True))

    worker._run()

    assert failed == []
    assert _FakeRequest.requests == []