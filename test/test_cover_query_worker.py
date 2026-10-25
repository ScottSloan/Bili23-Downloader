import pytest

from PySide6.QtCore import QSize

import util.download.cover.query_worker as query_worker_module
from util.download.cover.query_worker import CoverQueryWorker


class _FakeRequest:
    """按 url 关键字路由的假请求，用来区分 folder/info 与 resource/list 两次调用

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


def _build_worker(monkeypatch, media_id = "123", api_url = "https://api.bilibili.com/x/v3/fav/folder/info"):
    monkeypatch.setattr(query_worker_module, "SyncNetWorkRequest", _FakeRequest)

    return CoverQueryWorker(
        model = None,
        cover_key = f"__query__{media_id}@120x67",
        cover_url = media_id,
        cover_size = QSize(120, 67),
        query_param = {
            "api_url": api_url,
            "params": {"media_id": media_id},
        },
    )


def test_query_url_uses_folder_cover_when_set(monkeypatch):
    # 收藏夹设置了封面：直接用 folder/info 返回的 cover，不触发 fallback
    _reset_fake(folder_info = {"data": {"cover": "https://i0.hdslb.com/folder.jpg"}})

    worker = _build_worker(monkeypatch)

    worker.query_url()

    assert worker.cover_url == "https://i0.hdslb.com/folder.jpg"
    assert all("/x/v3/fav/resource/list" not in r for r in _FakeRequest.requests)


def test_query_url_falls_back_to_first_video_cover(monkeypatch):
    # 收藏夹未设置封面：回退到 resource/list 第一条的 cover
    _reset_fake(
        folder_info = {"data": {"cover": ""}},
        resource_list = {"data": {"medias": [{"cover": "https://i0.hdslb.com/first.jpg"}]}},
    )

    worker = _build_worker(monkeypatch)

    worker.query_url()

    assert worker.cover_url == "https://i0.hdslb.com/first.jpg"
    assert any("/x/v3/fav/resource/list" in r for r in _FakeRequest.requests)


def test_query_url_falls_back_when_cover_field_is_none(monkeypatch):
    # folder/info 返回 data.cover = None（字段存在但值为空），视为用户未设置封面，
    # 应回退到 resource/list 第一条的 cover
    _reset_fake(
        folder_info = {"data": {"cover": None}},
        resource_list = {"data": {"medias": [{"cover": "https://i0.hdslb.com/first.jpg"}]}},
    )

    worker = _build_worker(monkeypatch)

    worker.query_url()

    assert worker.cover_url == "https://i0.hdslb.com/first.jpg"


def test_query_url_fallback_url_params(monkeypatch):
    # fallback 请求的 URL 应携带 media_id / pn=1 / ps=1 / order=mtime，
    # 与 FavlistParser.get_favlist() 的参数保持一致
    _reset_fake(
        folder_info = {"data": {"cover": ""}},
        resource_list = {"data": {"medias": [{"cover": "https://i0.hdslb.com/first.jpg"}]}},
    )

    worker = _build_worker(monkeypatch, media_id = "456")

    worker.query_url()

    fallback_url = next(r for r in _FakeRequest.requests if "/x/v3/fav/resource/list" in r)

    assert "media_id=456" in fallback_url
    assert "pn=1" in fallback_url
    assert "ps=1" in fallback_url
    assert "order=mtime" in fallback_url


def test_query_url_raises_when_both_empty(monkeypatch):
    # 收藏夹既无封面也无视频：两次请求都为空，仍应抛 ValueError 让上层走 onCoverFailed
    _reset_fake(
        folder_info = {"data": {"cover": ""}},
        resource_list = {"data": {"medias": []}},
    )

    worker = _build_worker(monkeypatch)

    with pytest.raises(ValueError, match = "获取封面 URL 失败"):
        worker.query_url()


def test_query_url_raises_when_resource_list_data_missing(monkeypatch):
    # resource/list 返回业务错误（data 缺失 / data 为 null / data 为空 dict / 空响应）
    # 时不应抛 AttributeError，而是退化到 ValueError，让上层走 onCoverFailed
    for bad_response in ({"code": -403, "message": "请求被拦截"}, {"data": None}, {"data": {}}, {}):
        _reset_fake(
            folder_info = {"data": {"cover": ""}},
            resource_list = bad_response,
        )

        worker = _build_worker(monkeypatch)

        with pytest.raises(ValueError, match = "获取封面 URL 失败"):
            worker.query_url()


def test_query_url_raises_when_first_media_has_no_cover(monkeypatch):
    # 保持"只取第一个视频封面"的语义：第一条无 cover 时不遍历后续，
    # 直接抛 ValueError 退化到占位图。这是明确的取舍，避免误显示非首个视频的封面
    _reset_fake(
        folder_info = {"data": {"cover": ""}},
        resource_list = {"data": {"medias": [{"cover": ""}, {"cover": "https://i0.hdslb.com/second.jpg"}]}},
    )

    worker = _build_worker(monkeypatch)

    with pytest.raises(ValueError, match = "获取封面 URL 失败"):
        worker.query_url()


def test_query_url_does_not_fallback_when_data_missing(monkeypatch):
    # 业务出错、响应中没有 data 键：不应误判为"用户未设置封面"而触发 fallback，
    # 否则一次接口故障会被静默换成一张错误的封面
    _reset_fake(
        folder_info = {"code": -412, "message": "请求被拦截"},
        resource_list = {"data": {"medias": [{"cover": "https://i0.hdslb.com/first.jpg"}]}},
    )

    worker = _build_worker(monkeypatch)

    with pytest.raises(ValueError, match = "获取封面 URL 失败"):
        worker.query_url()

    assert all("/x/v3/fav/resource/list" not in r for r in _FakeRequest.requests)


def test_query_url_does_not_fallback_when_data_is_null(monkeypatch):
    # 业务出错、data 为 null：同上，不应触发 fallback
    _reset_fake(
        folder_info = {"code": -412, "message": "请求被拦截", "data": None},
        resource_list = {"data": {"medias": [{"cover": "https://i0.hdslb.com/first.jpg"}]}},
    )

    worker = _build_worker(monkeypatch)

    with pytest.raises(ValueError, match = "获取封面 URL 失败"):
        worker.query_url()

    assert all("/x/v3/fav/resource/list" not in r for r in _FakeRequest.requests)


def test_query_url_does_not_fallback_for_non_favlist_api(monkeypatch):
    # __query__ 是通用机制，未来可能被其他列表复用。非收藏夹场景（api_url 不含
    # /x/v3/fav/folder/info）即使 params 里有 media_id，也不应走 fallback
    _reset_fake(
        extra = {
            "/x/v3/fav/folder/collected/list": {"data": {"cover": ""}},
            "/x/v3/fav/resource/list": {"data": {"medias": [{"cover": "https://i0.hdslb.com/first.jpg"}]}},
        },
    )

    worker = _build_worker(monkeypatch, api_url = "https://api.bilibili.com/x/v3/fav/folder/collected/list")

    with pytest.raises(ValueError, match = "获取封面 URL 失败"):
        worker.query_url()

    # 只发出了 collected/list 请求，没有 fallback 到 resource/list
    assert any("collected/list" in r for r in _FakeRequest.requests)
    assert all("/x/v3/fav/resource/list" not in r for r in _FakeRequest.requests)


def test_query_url_does_not_recompute_cover_key(monkeypatch):
    # 键一致性回归测试：query_url 成功后 cover_key 必须保持发起请求时的形态。
    # 若改为 md5(cover_url)@{w}x{h}，模型侧 _release_waiting_rows 找不到等待集，
    # 封面写进缓存但永不回显（详见 query_url 末尾注释）
    _reset_fake(folder_info = {"data": {"cover": "https://i0.hdslb.com/folder.jpg"}})

    worker = _build_worker(monkeypatch, media_id = "456")

    original_key = worker.cover_key
    worker.query_url()

    assert worker.cover_key == original_key
    assert worker.cover_key == "__query__456@120x67"


def test_run_skips_query_url_when_query_param_none(monkeypatch):
    # query_param 为 None 时 _run 跳过 query_url，防止未来误改 if self.query_param: 分支。
    # image / return_to_model 都 mock 掉，不依赖 QImage 的具体内容
    _reset_fake()

    worker = CoverQueryWorker(
        model = None,
        cover_key = "k@120x67",
        cover_url = "https://i0.hdslb.com/x.jpg",
        cover_size = QSize(120, 67),
        query_param = None,
    )

    called = []
    monkeypatch.setattr(worker, "query_url", lambda: called.append(True))
    monkeypatch.setattr(worker, "query_cache", lambda: object())
    monkeypatch.setattr(worker, "return_to_model", lambda image: None)

    worker._run()

    assert called == []


def test_run_empty_cover_does_not_notify_failed(monkeypatch):
    # cover_url 为空且无 query_param 时直接 return，不回报失败、也不发网络请求。
    # 这是会员购课程等"本来就没封面"的路径，回报失败会导致每次重绘都重新发起请求
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
    # 收藏夹 fid=0 时 parser 产出的 cover = 0（int）。0 在 _run 的
    # if not self.cover_url 判断里是 falsy，会直接 return，既不请求也不 notify_failed。
    # 这是沿用的既有行为，不在本 PR 额外处理；此测试把语义钉死，
    # 防止未来有人误以为是 bug 去"修"
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