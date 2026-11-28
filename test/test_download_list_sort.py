"""
gui/component/download_list/model.py —— 下载列表的排序。

排序在源模型里用 list.sort(key = ...) 完成，新任务按二分查找插到该在的位置；
代理模型只负责筛选，从不调用 sort()。这样做是因为代理排序每次比较都要回调 Python，
已完成列表攒到数万条时点一次表头、每完成一个任务都会卡住界面好几秒。

这里直接用真实的源模型与代理模型，按界面里的顺序先开排序、再分批追加，断言每批
追加之后整个列表仍然有序；另外钉住重排时持久索引（选中项）跟着任务走。
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPersistentModelIndex, Qt

from gui.component.download_list.model import DownloadListModel
from gui.component.download_list.proxy_model import DownloadListProxyModel

from types import SimpleNamespace

import pytest


@pytest.fixture(scope = "module")
def app():
    return QApplication.instance() or QApplication([])


def make_task(value: int):
    """排序只读 Basic / Download 上的几个字段，不必构造完整的 TaskInfo"""
    return SimpleNamespace(
        Basic = SimpleNamespace(
            task_id = f"task-{value}",
            created_time = value,
            completed_time = value,
            show_title = f"title-{value}"
        ),
        Download = SimpleNamespace(
            total_size = value,
            progress = value,
            status = None,
            info_label = "",
            status_label = ""
        )
    )


def make_proxy(key: str, ascending: bool):
    source = DownloadListModel([])

    proxy = DownloadListProxyModel()
    proxy.setSourceModel(source)

    # 与 DownloadInterface 一致：先开排序，任务之后才陆续加入
    proxy.enableSorting(key, ascending)

    return proxy


def visible_order(proxy: DownloadListProxyModel):
    return [
        proxy.index(row, 0).data(Qt.ItemDataRole.UserRole).Basic.created_time
        for row in range(proxy.rowCount())
    ]


@pytest.mark.parametrize("ascending", [True, False])
def test_appended_tasks_follow_sort_order(app, ascending):
    proxy = make_proxy("created_time", ascending)

    proxy.appendRows([make_task(2), make_task(1), make_task(3)])
    proxy.appendRow(make_task(5))
    proxy.appendRows([make_task(4), make_task(6)])

    assert visible_order(proxy) == sorted(range(1, 7), reverse = not ascending)


def test_sort_change_applies_to_later_appends(app):
    """用户在界面里改了排序方向之后，后续追加的任务也要按新方向归位"""
    proxy = make_proxy("created_time", True)

    proxy.appendRows([make_task(1), make_task(2)])

    proxy.sortBy("created_time", False)

    proxy.appendRow(make_task(3))

    assert visible_order(proxy) == [3, 2, 1]


def test_insert_lands_after_equal_keys(app):
    """键值相等时新任务落在已有任务之后，与稳定排序的结果一致，翻来覆去不会跳位"""
    for ascending in (True, False):
        proxy = make_proxy("created_time", ascending)

        first, second = make_task(5), make_task(5)
        second.Basic.task_id = "task-5-later"

        proxy.appendRows([make_task(1), first, make_task(9)])
        proxy.appendRow(second)

        tasks = [proxy.index(row, 0).data(Qt.ItemDataRole.UserRole) for row in range(proxy.rowCount())]

        assert tasks.index(first) + 1 == tasks.index(second)


def test_large_batch_append_is_sorted(app):
    """超过逐条插入阈值的一批走「接在末尾 + 整体重排」，结果同样有序，行号索引也要跟着更新"""
    proxy = make_proxy("created_time", False)
    source = proxy.sourceModel()

    proxy.appendRows([make_task(value) for value in range(0, 1000, 2)])
    proxy.appendRows([make_task(value) for value in range(1, 1000, 2)])

    assert visible_order(proxy) == list(range(999, -1, -1))

    for row in (0, 500, 999):
        task_info = source.index(row).data(Qt.ItemDataRole.UserRole)

        assert source.getRow(task_info) == row


def test_resort_keeps_persistent_index_on_same_task(app):
    """选中项挂在持久索引上，重排后必须仍指向同一个任务，而不是停在原来的行号上"""
    proxy = make_proxy("created_time", True)

    proxy.appendRows([make_task(1), make_task(2), make_task(3)])

    selected = QPersistentModelIndex(proxy.index(0, 0))
    task_info = selected.data(Qt.ItemDataRole.UserRole)

    proxy.sortBy("created_time", False)

    assert selected.row() == 2
    assert selected.data(Qt.ItemDataRole.UserRole) is task_info


def test_resort_without_order_change_emits_nothing(app):
    """顺序没变时不发 layoutChanged：下载中每 50 毫秒就可能触发一次重排，没必要让代理模型反复重建映射"""
    proxy = make_proxy("created_time", True)
    source = proxy.sourceModel()

    proxy.appendRows([make_task(1), make_task(2), make_task(3)])

    emitted = []
    source.layoutChanged.connect(lambda: emitted.append(True))

    source.resort()

    assert emitted == []


def test_progress_change_reorders_after_refresh(app):
    """进度排序下，下载进度变化要经代理模型的去抖刷新后重新归位"""
    proxy = make_proxy("progress", False)

    tasks = [make_task(1), make_task(2), make_task(3)]
    proxy.appendRows(tasks)

    tasks[0].Download.progress = 100

    proxy._scheduleRefresh(refresh_sort = True)
    proxy._flushPendingRefresh()

    assert [proxy.index(row, 0).data(Qt.ItemDataRole.UserRole) for row in range(3)] == [tasks[0], tasks[2], tasks[1]]
