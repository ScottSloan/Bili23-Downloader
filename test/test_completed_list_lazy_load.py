"""
已完成列表的按需分批读取（gui/component/download_list/completed_model.py 与 db.query_completed_batch）。

已完成任务长期累积，攒到数万条时全量读出要卡好几秒、常驻几百 MB 内存，因此改为滚动到底再从数据库
取下一批，排序与筛选都在数据库里执行。这里钉住几件一旦出错就表现为「列表里少了 / 多了几条」、
平时却极难察觉的事：

1. 分批读取不重不漏：每种排序方式、升降序、含同值与空值，逐批读完恰好是全集
2. 数据库里的筛选与下载中列表的内存筛选判定一致
3. 浏览期间新完成的任务：排在已读范围内的立即插入，排在之后的留给后续批次，两种情况都只出现一次
4. 「全部清除」作用于数据库里所有满足筛选的记录，而不只是读出来的那几批
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QModelIndex, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent

from util.common.enum import DownloadStatus, DownloadType
from util.parse.episode.tree import Attribute

from threading import Event
import time

import pytest


@pytest.fixture(scope = "module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def manager(tmp_path, monkeypatch):
    # 独立的库，不与其他用例共用 qttest 目录下的 task.db
    from util.download.task import db as db_module
    from util.download.task.manager import TaskManager
    from gui.component.download_list import completed_model

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    manager = TaskManager()

    monkeypatch.setattr(completed_model, "task_manager", manager)

    yield manager

    # 连接是线程本地的，读线程与写线程的连接都要投递回各自的线程去关
    manager._read_executor.submit(manager.db_manager.close_connection)
    manager._read_executor.shutdown(wait = True)

    manager._update_executor.submit(manager.db_manager.close_connection)
    manager._update_executor.shutdown(wait = True)
    manager._cancel_executor.shutdown(wait = True)

    manager.db_manager.close_connection()


def make_task(index: int, title = None, completed_time = None, total_size = None, attribute = Attribute.VIDEO_BIT,
              download_type = DownloadType.VIDEO | DownloadType.AUDIO, uploader = ""):
    from util.download.task.info import TaskInfo

    task_info = TaskInfo()
    task_info.Basic.task_id = f"task-{index:05d}"
    task_info.Basic.show_title = f"标题 {index:05d}" if title is None else title
    task_info.Basic.completed_time = 1_700_000_000 + index if completed_time is None else completed_time
    task_info.Download.total_size = index * 10 if total_size is None else total_size
    task_info.Download.status = DownloadStatus.COMPLETED
    task_info.Download.type = download_type
    task_info.Episode.attribute = attribute
    task_info.Episode.uploader = uploader

    return task_info


def add_completed(manager, task_info_list):
    manager.db_manager.add_tasks(task_info_list, completed = True)


def read_all(manager, order_by, ascending, batch_size = 7, **filters):
    ids = []
    after = None

    while True:
        rows = manager.query_completed_batch(order_by, ascending, batch_size, after, **filters)

        ids.extend(task_info.Basic.task_id for _, _, task_info in rows)

        if len(rows) < batch_size:
            return ids

        after = rows[-1][:2]


# --------------------------------------------------------------------------
# 数据库层
# --------------------------------------------------------------------------

@pytest.mark.parametrize("order_by", ["completed_time", "show_title", "file_size"])
@pytest.mark.parametrize("ascending", [True, False])
def test_batches_cover_every_row_exactly_once(manager, order_by, ascending):
    # 刻意制造大量同值（时间、大小只有 5 种取值，标题只有 3 种并混着大小写），
    # 再加上空标题，游标若没处理好同值或 NULL，就会漏行或重复
    tasks = [
        make_task(index, title = ["abc", "ABD", "中文"][index % 3], completed_time = index % 5, total_size = index % 5)
        for index in range(60)
    ]
    tasks.append(make_task(60, title = ""))

    add_completed(manager, tasks)

    ids = read_all(manager, order_by, ascending)

    assert sorted(ids) == sorted(task_info.Basic.task_id for task_info in tasks)
    assert len(ids) == len(set(ids))


def test_title_order_matches_in_memory_key(manager):
    """数据库的 NOCASE 与内存插入用的 nocase_key 必须给出同样的顺序，否则新任务会插错位置"""
    from gui.component.download_list.model import nocase_key

    titles = ["b", "B", "a", "Á", "中文", "Zed", "zed", "", "_x", "10", "9"]
    tasks = [make_task(index, title = title) for index, title in enumerate(titles)]

    add_completed(manager, tasks)

    ids = read_all(manager, "show_title", True, batch_size = 100)
    by_id = {task_info.Basic.task_id: task_info for task_info in tasks}

    keys = [nocase_key(by_id[task_id].Basic.show_title) for task_id in ids]

    assert keys == sorted(keys)


def test_sql_filter_matches_in_memory_filter(manager):
    """已完成列表在数据库里筛，下载中列表在内存里筛，同样的条件必须筛出同样的任务"""
    from util.download.task.filter import get_media_type_key, get_searchable_text, matches_keywords, split_keywords

    tasks = [
        make_task(1, title = "Minecraft 生存", uploader = "Alice"),
        make_task(2, title = "MINECRAFT 建筑", uploader = "Bob"),
        make_task(3, title = "原神", uploader = "alice"),
        make_task(4, title = "播客", download_type = DownloadType.AUDIO),
        make_task(5, title = "番剧 minecraft", attribute = Attribute.BANGUMI_BIT),
        make_task(6, title = "100%_done"),
    ]

    add_completed(manager, tasks)

    cases = [
        ("minecraft", None),
        ("  ALICE   minecraft ", None),
        ("alice", frozenset({"VIDEO", "INTERACTIVE"})),
        ("", frozenset({"AUDIO"})),
        ("minecraft", frozenset({"BANGUMI"})),
        # LIKE 的通配符在这里只是普通字符
        ("%_", None),
    ]

    for text, media_types in cases:
        keywords = split_keywords(text)

        expected = sorted(
            task_info.Basic.task_id for task_info in tasks
            if (not media_types or get_media_type_key(task_info) in media_types)
            and matches_keywords(get_searchable_text(task_info), keywords)
        )

        actual = sorted(read_all(manager, "completed_time", False, keywords = keywords, media_types = media_types))

        assert actual == expected, (text, media_types)


def test_delete_matching_only_removes_matching_rows(manager):
    add_completed(manager, [make_task(1, title = "保留"), make_task(2, title = "删除 a"), make_task(3, title = "删除 b")])

    manager.db_manager.delete_completed_matching(["删除"], None)

    assert read_all(manager, "completed_time", True) == ["task-00001"]

    manager.db_manager.delete_completed_matching((), None)

    assert read_all(manager, "completed_time", True) == []


def test_sort_indexes_are_used(manager):
    """每种排序方式都要走索引按序取，否则每读一批都是全表扫加排序"""
    from util.download.task.db import _COMPLETED_ORDER_EXPRS

    manager.wait_for_pending_writes()

    conn = manager.db_manager.get_connection()

    # 这条连接打开时索引还没建（建索引在写线程上）。EXPLAIN 不开启事务、不会察觉表结构已变，
    # 给出的是旧计划；先执行一次真正的查询让它重新载入表结构。实际读取不受此影响
    conn.execute('SELECT 1 FROM "completed_task" LIMIT 1').fetchall()

    for expr in _COMPLETED_ORDER_EXPRS.values():
        plan = conn.execute(
            f'EXPLAIN QUERY PLAN SELECT "data" FROM "completed_task" WHERE {expr} <= ? AND ({expr} < ? OR "id" < ?) '
            f'ORDER BY {expr} DESC, "id" DESC LIMIT 100',
            (0, 0, 0)
        ).fetchall()

        detail = " ".join(row[3] for row in plan)

        assert "USING INDEX" in detail and "TEMP B-TREE" not in detail, (expr, detail)


# --------------------------------------------------------------------------
# 模型层
# --------------------------------------------------------------------------

def wait_until(predicate, timeout = 5.0):
    deadline = time.monotonic() + timeout

    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("等待超时")

        QCoreApplication.processEvents()
        time.sleep(0.005)


def make_model(order_by = "completed_time", ascending = False, batch_size = 10):
    from gui.component.download_list.completed_model import CompletedListModel
    from gui.component.download_list.proxy_model import DownloadListProxyModel

    model = CompletedListModel([])
    model.BATCH_SIZE = batch_size

    proxy = DownloadListProxyModel()
    proxy.setSourceModel(model)
    proxy.enableSorting(order_by, ascending)

    wait_until(lambda: not model._loading)

    return model, proxy


def loaded_ids(model):
    return [model.index(row).data(Qt.ItemDataRole.UserRole).Basic.task_id for row in range(model.rowCount())]


def fetch_all(model):
    while model.canFetchMore():
        model.fetchMore()

        wait_until(lambda: not model._loading)


def test_model_loads_first_batch_then_fetches_more(app, manager):
    add_completed(manager, [make_task(index) for index in range(25)])

    model, proxy = make_model(batch_size = 10)

    assert model.rowCount() == 10
    assert proxy.canFetchMore(QModelIndex())

    fetch_all(model)

    assert loaded_ids(model) == [f"task-{index:05d}" for index in range(24, -1, -1)]
    assert not proxy.canFetchMore(QModelIndex())


def test_new_task_within_loaded_range_is_inserted(app, manager):
    add_completed(manager, [make_task(index) for index in range(25)])

    model, _ = make_model(batch_size = 10)

    # 按完成时间降序，刚完成的任务排在最前，属于已读范围
    new_task = make_task(100)
    add_completed(manager, [new_task])
    model.appendRows([new_task])

    assert loaded_ids(model)[0] == "task-00100"

    fetch_all(model)

    ids = loaded_ids(model)

    assert ids.count("task-00100") == 1
    assert len(ids) == 26


def test_new_task_beyond_loaded_range_is_fetched_once(app, manager):
    add_completed(manager, [make_task(index) for index in range(25)])

    # 按完成时间升序，刚完成的任务排在最后，尚未读到
    model, _ = make_model(ascending = True, batch_size = 10)

    new_task = make_task(100)
    add_completed(manager, [new_task])
    model.appendRows([new_task])

    assert "task-00100" not in loaded_ids(model)

    fetch_all(model)

    ids = loaded_ids(model)

    assert ids.count("task-00100") == 1
    assert ids[-1] == "task-00100"
    assert len(ids) == 26


def test_task_completed_during_load_appears_once(app, manager, monkeypatch):
    """读取进行中完成的任务先挂起，等这一批落定再判断，不能因读取恰好也带上它而重复"""
    add_completed(manager, [make_task(index) for index in range(5)])

    model, _ = make_model(batch_size = 10)

    release = Event()
    original = manager.query_completed_batch

    def slow_query(*args, **kwargs):
        release.wait(5)

        return original(*args, **kwargs)

    monkeypatch.setattr(manager, "query_completed_batch", slow_query)

    model.setSortOrder("completed_time", False)

    assert model._loading

    new_task = make_task(100)
    add_completed(manager, [new_task])
    model.appendRows([new_task])

    release.set()

    wait_until(lambda: not model._loading)

    assert loaded_ids(model).count("task-00100") == 1


def test_stale_results_are_dropped(app, manager, monkeypatch):
    """连续切换排序时，先发出的读取晚到也不能覆盖后来的结果"""
    add_completed(manager, [make_task(index) for index in range(5)])

    model, _ = make_model(batch_size = 10)

    release = Event()
    original = manager.query_completed_batch

    def query(order_by, ascending, *args, **kwargs):
        if ascending:
            release.wait(5)

        return original(order_by, ascending, *args, **kwargs)

    monkeypatch.setattr(manager, "query_completed_batch", query)

    # 读线程只有一个，后一次读取排在前一次之后；前一次的结果先到，必须被丢弃
    model.setSortOrder("completed_time", True)
    model.setSortOrder("completed_time", False)

    release.set()

    wait_until(lambda: not model._loading)

    assert loaded_ids(model) == [f"task-{index:05d}" for index in range(4, -1, -1)]


def test_filter_reloads_from_database(app, manager):
    add_completed(manager, [make_task(index, title = "猫" if index % 2 else "狗") for index in range(30)])

    model, _ = make_model(batch_size = 10)

    model.setFilterText("猫")
    model._reload_timer.timeout.emit()

    wait_until(lambda: not model._loading)
    fetch_all(model)

    ids = loaded_ids(model)

    assert len(ids) == 15
    assert model.isFiltering()


def test_clear_all_removes_unloaded_matching_rows(app, manager):
    add_completed(manager, [make_task(index, title = "猫" if index % 2 else "狗") for index in range(30)])

    model, _ = make_model(batch_size = 10)

    model.setFilterText("猫")
    model._reload_timer.timeout.emit()

    wait_until(lambda: not model._loading)

    # 只读进了第一批，但「全部清除」要删掉数据库里全部 15 条
    assert model.rowCount() == 10

    model.batch_cancel()

    assert model.rowCount() == 0
    assert not model.canFetchMore()

    manager.wait_for_pending_writes()

    remaining = read_all(manager, "completed_time", True)

    assert len(remaining) == 15
    assert all(int(task_id[-5:]) % 2 == 0 for task_id in remaining)


def test_view_fetches_more_when_scrolled_to_bottom(app, manager):
    """滚到底要由视图自己触发 fetchMore，这一步在 Qt 里，靠模型层的用例覆盖不到"""
    from gui.component.download_list.list_view import DownloadListView
    from gui.component.download_list import completed_model

    add_completed(manager, [make_task(index) for index in range(300)])

    view = DownloadListView(lazy_load = True)
    view.resize(800, 400)

    model = view._source_model
    assert isinstance(model, completed_model.CompletedListModel)

    view.enableSorting("completed_time", False)
    view.show()

    wait_until(lambda: not model._loading and model.rowCount() > 0)

    first = model.rowCount()

    assert first == model.BATCH_SIZE

    # 视图的布局是延后进行的，布局完成前滚动条的最大值还是 0
    scroll_bar = view.verticalScrollBar()

    wait_until(lambda: scroll_bar.maximum() > 0)

    # 走真实的滚轮事件：经过 qfluentwidgets 的平滑滚动委托，再由它改写滚动条的值
    viewport = view.viewport()
    center = QPointF(viewport.rect().center())

    for _ in range(50):
        event = QWheelEvent(
            center, viewport.mapToGlobal(center), QPoint(), QPoint(0, -12000),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False
        )
        QApplication.sendEvent(viewport, event)

        # 留出平滑滚动动画的时间；滚轮事件来得太密，动画会被不断打断重来，迟迟滚不到底
        deadline = time.monotonic() + 0.05

        while time.monotonic() < deadline:
            QCoreApplication.processEvents()

        if model.rowCount() > first:
            break

    assert model.rowCount() > first

    view.close()
    view.deleteLater()


def test_many_pending_tasks_are_inserted_in_order(app, manager):
    """读取期间积压的新任务可能一次超过父类逐条插入的阈值，同样要插在正确的位置"""
    add_completed(manager, [make_task(index) for index in range(5)])

    model, _ = make_model(ascending = True, batch_size = 10)

    new_tasks = [make_task(index) for index in range(1000, 900, -1)]
    add_completed(manager, new_tasks)
    model.appendRows(new_tasks)

    ids = loaded_ids(model)

    assert len(ids) == 105
    assert ids == sorted(ids)
