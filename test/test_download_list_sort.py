"""
gui/component/download_list/proxy_model.py —— 新追加的任务要按当前排序方式归位。

代理模型关着 dynamicSortFilter，Qt 只把新插入的一批行在批内排好、整批接在末尾。
启动时列表为空、任务一次性载入，看不出问题；之后新建的任务、下载完成移进"已完成"
列表的任务都会停在最底下，降序排列时尤其明显。

这里直接用真实的源模型与代理模型，按界面里的顺序先开排序、再分批追加，断言每批
追加之后整个列表仍然有序。
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

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
