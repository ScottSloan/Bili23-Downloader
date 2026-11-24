"""
收藏夹封面的查询与回显（#485）。

收藏夹封面不在列表接口里，要按收藏夹 id 先查出 URL 再下载，模型侧用 __query__{fid} 键登记等待。
封面缓存重构后，worker 拿到 URL 就把这个键改写成按 URL 计算的键，回报时模型找不到等待集，
封面进了缓存却永不回显（自 2.20.0 起所有收藏夹封面都显示不出来）。

这里钉住：回报键始终是模型登记的那个，数据库缓存按 URL 存；没设封面的收藏夹退回第一个视频的
封面；确实没有封面时不回报失败（否则每次重绘都重发请求），接口出错时才回报失败、允许重试。
"""

from PySide6.QtCore import QBuffer, QSize
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
import pytest

from collections import OrderedDict
from urllib.parse import parse_qs, urlparse


FOLDER_INFO = "https://api.bilibili.com/x/v3/fav/folder/info"


@pytest.fixture(scope = "module")
def app():
    return QApplication.instance() or QApplication([])


def png_bytes():
    image = QImage(64, 36, QImage.Format.Format_RGB32)
    image.fill(0xFF3366)

    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")

    return bytes(buffer.data())


@pytest.fixture
def api(app, monkeypatch):
    """
    替换网络与数据库边界：folder/info、resource/list、图片下载各返回什么由用例设置，
    数据库缓存换成内存 dict，并记录每次请求
    """
    from util.download.cover import query_worker
    from util.download.cover.cache import CoverCache
    from util.download.cover.manager import cover_manager

    state = {
        "folder_info": {"code": 0, "data": {"cover": "https://i0.hdslb.com/custom.jpg"}},
        "resource_list": {"code": 0, "data": {"medias": [{"cover": "https://i0.hdslb.com/first.jpg"}]}},
        "requested": [],
        "db": {},
    }

    class FakeRequest:
        def __init__(self, url, *args, **kwargs):
            self.url = url

        def run(self):
            state["requested"].append(self.url)

            if self.url.startswith(FOLDER_INFO):
                return state["folder_info"]

            if "/fav/resource/list" in self.url:
                return state["resource_list"]

            return png_bytes()

    monkeypatch.setattr(query_worker, "SyncNetWorkRequest", FakeRequest)
    # 解码后的位图缓存是进程级的：不隔离的话，前一个用例回显的封面会让后面的用例直接命中缓存，
    # 根本不会走到 worker
    monkeypatch.setattr(CoverCache, "cache", OrderedDict())
    monkeypatch.setattr(cover_manager, "query", lambda key: state["db"].get(key))
    monkeypatch.setattr(cover_manager, "create", lambda key, data: state["db"].__setitem__(key, data))

    return state


@pytest.fixture
def entry_model(api, monkeypatch):
    """
    真实的收藏夹列表模型。worker 改为同步执行，这样回报经过的是与线上相同的
    invokeMethod 排队路径，只是不再跨线程
    """
    from gui.component.entry_list.model import EntryListModel
    from util.download.cover.manager import cover_manager
    from util.download.cover.query_worker import CoverQueryWorker

    workers = []

    def run_now(model, cover_key, cover_url, cover_size, query_param = None):
        worker = CoverQueryWorker(model, cover_key, cover_url, cover_size, query_param)
        workers.append(worker)
        worker.run()

    monkeypatch.setattr(cover_manager, "request", run_now)

    entries = [{"title": "收藏夹", "url": "", "count": 3, "cover": 42, "cover_id": "__query__42"}]
    model = EntryListModel(entries)

    return model, workers


def request_cover(app, model):
    changed = []
    model.dataChanged.connect(lambda top, bottom: changed.append(top.row()))

    model.queryRowCover("__query__42", 42, 0, 1.0)
    # 回报走 QueuedConnection，要让事件循环跑一轮
    app.processEvents()

    return changed


def test_cover_is_shown_after_query(app, api, entry_model):
    model, workers = entry_model

    changed = request_cover(app, model)

    # 回报键与模型登记的等待集对上，才会刷新这一行并释放等待集
    assert changed == [0]
    assert model.cover_waiting_rows == {}
    assert workers[0].cover_key.startswith("__query__42@")


def test_cache_is_keyed_by_cover_url(app, api, entry_model):
    from util.download.cover.manager import cover_manager

    model, workers = entry_model

    request_cover(app, model)

    # 按 URL 存：换了收藏夹封面，URL 变了，缓存自然失效；按收藏夹 id 存的话永远是旧图
    expected = cover_manager.arrange_cover_key(cover_manager.arrange_cover_id("https://i0.hdslb.com/custom.jpg"), workers[0].cover_size)

    assert list(api["db"]) == [expected]
    assert workers[0].storage_key == expected


def test_folder_without_cover_falls_back_to_first_media(app, api, entry_model):
    model, workers = entry_model
    api["folder_info"] = {"code": 0, "data": {"cover": ""}}

    changed = request_cover(app, model)

    assert changed == [0]
    assert workers[0].cover_url == "https://i0.hdslb.com/first.jpg"

    fallback = next(url for url in api["requested"] if "/fav/resource/list" in url)
    query = parse_qs(urlparse(fallback).query)

    assert (query["media_id"], query["pn"], query["ps"]) == (["42"], ["1"], ["1"])


@pytest.mark.parametrize("resource_list", [
    {"code": 0, "data": {"medias": None}},
    {"code": 0, "data": {"medias": []}},
    # 第一条没有封面就算没有，不往后找
    {"code": 0, "data": {"medias": [{"cover": ""}, {"cover": "https://i0.hdslb.com/second.jpg"}]}},
])
def test_no_cover_at_all_is_not_retried(app, api, entry_model, resource_list):
    model, workers = entry_model
    api["folder_info"] = {"code": 0, "data": {"cover": ""}}
    api["resource_list"] = resource_list

    changed = request_cover(app, model)
    requested = len(api["requested"])

    # 本来就没有封面：不回报失败，等待集保留，后续重绘不会再发请求
    assert changed == []
    assert model.cover_waiting_rows

    model.queryRowCover("__query__42", 42, 0, 1.0)
    app.processEvents()

    assert len(api["requested"]) == requested
    assert not any("second.jpg" in url for url in api["requested"])


@pytest.mark.parametrize("stage", ["folder_info", "resource_list"])
def test_api_error_is_reported_for_retry(app, api, entry_model, stage):
    model, workers = entry_model
    api["folder_info"] = {"code": 0, "data": {"cover": ""}}
    # 风控、参数错误时 data 为 null，不能当成"没有封面"静默吞掉
    api[stage] = {"code": -412, "message": "请求被拦截", "data": None}

    request_cover(app, model)

    # 回报失败释放等待集，下次重绘会重试
    assert model.cover_waiting_rows == {}


def test_fallback_needs_explicit_switch(app, api):
    from util.download.cover.query_worker import CoverQueryWorker

    api["folder_info"] = {"code": 0, "data": {"cover": ""}}

    # __query__ 是通用机制，没开开关的列表不能擅自去查收藏夹内容
    worker = CoverQueryWorker(None, "__query__42@64x36", 42, QSize(64, 36), {"api_url": FOLDER_INFO, "params": {"media_id": 42}})
    worker.run()

    assert not any("/fav/resource/list" in url for url in api["requested"])


def test_empty_favorite_folder_still_queries_cover():
    # 封面是收藏夹自己的属性：空收藏夹也可能设了封面，不能因为没有视频就不查
    from util.parse.parser.favorite import FavoriteParser

    received = []

    parser = FavoriteParser.__new__(FavoriteParser)
    parser.success_callback = received.append

    from util.parse.parser import favorite

    favorite.post_to_main_thread, original = (lambda callback, *args: callback(*args)), favorite.post_to_main_thread

    try:
        parser.on_get_favorite_list_success({"data": {"list": [
            {"title": "空收藏夹", "mid": 1, "id": 7, "media_count": 0},
            {"title": "有视频", "mid": 1, "id": 8, "media_count": 5},
        ]}})

    finally:
        favorite.post_to_main_thread = original

    assert [entry["cover_id"] for entry in received[0]] == ["__query__7", "__query__8"]
