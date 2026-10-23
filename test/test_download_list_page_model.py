"""
分页模式下 DownloadListModel 的行为。

分页本身依赖三个东西：
- setPageTasks：整页替换；
- appendRows：追加一批任务后索引与 _task_list 同步；
- _row_by_task_id：getRow 的 O(1) 查询依赖。

这里只断言这些行为的结果正确，不依赖排序 role 下推（SORT_ROLE_*）这类可选优化 ——
分页模式下 proxy 不参与排序，SORT_ROLE_* 用不上。
"""

from PySide6.QtWidgets import QApplication

from gui.component.download_list.model import DownloadListModel

from types import SimpleNamespace

import pytest


@pytest.fixture(scope = "module")
def app():
    return QApplication.instance() or QApplication([])


def make_task(value: int, title = ""):
    return SimpleNamespace(
        Basic = SimpleNamespace(
            task_id = f"task-{value}",
            created_time = value,
            completed_time = value * 10,
            show_title = title or f"title-{value}"
        ),
        Download = SimpleNamespace(
            total_size = value,
            progress = value,
            status = None,
            info_label = "",
            status_label = ""
        )
    )


class TestAppendRowsIndex:
    def test_existing_rows_keep_their_index(self, app):
        model = DownloadListModel([make_task(i) for i in range(1, 6)])
        original = dict(model._row_by_task_id)

        model.appendRows([make_task(6), make_task(7)])

        assert len(model._row_by_task_id) == 7

        for task_id, row in original.items():
            assert model._row_by_task_id[task_id] == row

    def test_appended_rows_get_contiguous_indices(self, app):
        model = DownloadListModel([make_task(1), make_task(2)])

        model.appendRows([make_task(3), make_task(4), make_task(5)])

        assert model._row_by_task_id["task-3"] == 2
        assert model._row_by_task_id["task-4"] == 3
        assert model._row_by_task_id["task-5"] == 4

    def test_task_list_order_preserved(self, app):
        model = DownloadListModel([make_task(1)])

        model.appendRows([make_task(2), make_task(3)])

        assert [t.Basic.task_id for t in model._task_list] == ["task-1", "task-2", "task-3"]

    def test_empty_append_is_noop(self, app):
        model = DownloadListModel([make_task(1)])
        snapshot = dict(model._row_by_task_id)

        model.appendRows([])

        assert model.rowCount() == 1
        assert model._row_by_task_id == snapshot


class TestSetPageTasks:
    def test_replaces_everything(self, app):
        model = DownloadListModel([make_task(1), make_task(2)])

        model.setPageTasks([make_task(10), make_task(20), make_task(30)])

        assert [t.Basic.task_id for t in model._task_list] == ["task-10", "task-20", "task-30"]
        assert model._row_by_task_id == {"task-10": 0, "task-20": 1, "task-30": 2}

    def test_empty_list(self, app):
        model = DownloadListModel([make_task(1)])

        model.setPageTasks([])

        assert model.rowCount() == 0
        assert model._row_by_task_id == {}

    def test_get_row_works_after_replacement(self, app):
        model = DownloadListModel([make_task(1)])
        task = make_task(2)

        model.setPageTasks([task, make_task(3)])

        assert model.getRow(task) == 0