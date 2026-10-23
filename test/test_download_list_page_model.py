"""
分页模式下 DownloadListModel 的行为。

分页本身依赖三个东西：
- setPageTasks：整页替换；
- appendRows：追加一批任务后索引与 _task_list 同步（只给新增条目赋值，O(k)，
  不再遍历整表重建索引）；
- _row_by_task_id：getRow 的 O(1) 查询依赖。

另外，删除路径上有两个信号：
- row_removed：所有删除（cancelDownload、redownload、batch_cancel）都经由
  removeRow / removeTasks，在这里统一发射，供分页条更新总数；
- task_permanently_deleted：只在数据库落盘成功且确实移除了界面行后发射，
  供分页模式重载补位。redownload 也会走 removeRow，但那条路径下库里记录还在，
  不能重载，所以不发这个信号。

失败路径的 toast 断言用 monkeypatch 替换 model 模块的 signal_bus，
不碰真实的 signal_bus —— 无参 disconnect() 会断开该信号的全部连接，
测试会静默影响其他用例。
"""

from PySide6.QtWidgets import QApplication

from gui.component.download_list.model import DownloadListModel

from util.common.enum import DownloadStatus, ToastNotificationCategory

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


class _ToastRecorder:
    """记录 emit / connect 调用的假信号

    测试里如果对真实 signal_bus 连 lambda 再用无参 disconnect()，会断开该信号的
    全部连接（包括 DownloadInterface 等处的订阅），导致其他用例莫名不弹 toast。
    改用 monkeypatch 替换 model 模块的 signal_bus 更干净。

    同时提供 emit 与 connect：
    - emit 供 redownload、删除失败 toast 等路径使用；
    - connect 供 connectUpdateDataSignal 使用（当前测试不触发，但提供 no-op
      让 fake_bus 对未来测试也兼容）。
    """

    def __init__(self):
        self.calls = []
        self.connected_slots = []

    def emit(self, *args):
        self.calls.append(args)

    def connect(self, slot):
        # connectUpdateDataSignal 走这条路径；当前测试不触发，
        # 提供 no-op 让 fake_bus 对未来测试也兼容
        self.connected_slots.append(slot)


def make_fake_signal_bus():
    """替换 model 模块的 signal_bus，只记录 emit / connect 调用

    现有测试用到 toast.show_long_message（删除失败 toast）和 download 上的
    三条信号。后者当前测试不会走到，但一并放进去：
    - remove_from_completed_list / remove_from_downloading_list 用 emit；
    - update_downloading_item 用 connect（connectUpdateDataSignal 路径）；
    _ToastRecorder 同时提供 emit 与 connect，未来加 redownload 或
    connectUpdateDataSignal 的测试不需要再改 fake_bus。
    """
    return SimpleNamespace(
        toast = SimpleNamespace(
            show_long_message = _ToastRecorder(),
        ),
        download = SimpleNamespace(
            remove_from_completed_list = _ToastRecorder(),
            remove_from_downloading_list = _ToastRecorder(),
            update_downloading_item = _ToastRecorder(),
        ),
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


class TestRemoveRows:
    def test_remove_row_emits_signal(self, app):
        model = DownloadListModel([make_task(1), make_task(2), make_task(3)])

        received = []
        model.row_removed.connect(received.append)

        assert model.removeRow(1)

        assert received == [1]
        assert [t.Basic.task_id for t in model._task_list] == ["task-1", "task-3"]

    def test_remove_row_out_of_range_does_not_emit(self, app):
        model = DownloadListModel([make_task(1)])

        received = []
        model.row_removed.connect(received.append)

        assert not model.removeRow(99)

        assert received == []

    def test_remove_tasks_emits_count(self, app):
        tasks = [make_task(i) for i in range(1, 5)]
        model = DownloadListModel(list(tasks))

        received = []
        model.row_removed.connect(received.append)

        model.removeTasks([tasks[1], tasks[3]])

        assert received == [2]
        assert [t.Basic.task_id for t in model._task_list] == ["task-1", "task-3"]

    def test_remove_tasks_with_no_match_does_not_emit(self, app):
        model = DownloadListModel([make_task(1)])

        received = []
        model.row_removed.connect(received.append)

        model.removeTasks([make_task(99)])

        assert received == []

    def test_remove_tasks_returns_actual_removed_count(self, app):
        """removeTasks 返回实际移除数，不是传入的任务数

        分页模式下 task_info_list 可能包含不在当前页的任务，两者数量可能不同。
        调用方（batch_cancel）据此 emit 准确的删除数
        """
        tasks = [make_task(i) for i in range(1, 4)]
        model = DownloadListModel(list(tasks))

        # 传 2 条，其中 off_page 不在当前 model 里
        off_page = make_task(99)

        removed = model.removeTasks([tasks[0], off_page])

        assert removed == 1
        assert [t.Basic.task_id for t in model._task_list] == ["task-2", "task-3"]

    def test_remove_tasks_returns_zero_when_no_match(self, app):
        model = DownloadListModel([make_task(1)])

        removed = model.removeTasks([make_task(99)])

        assert removed == 0


class TestCancelDownload:
    def test_cancel_download_success_emits_both_signals(self, app, monkeypatch):
        """单条删除成功：发 row_removed + task_permanently_deleted，行被移除"""
        from gui.component.download_list import model as model_module

        task = make_task(1)
        task.Download.status = DownloadStatus.COMPLETED

        model = DownloadListModel([task])

        monkeypatch.setattr(model_module.task_manager, "delete", lambda *a, **kw: True)

        row_removed = []
        permanently_deleted = []
        model.row_removed.connect(row_removed.append)
        model.task_permanently_deleted.connect(permanently_deleted.append)

        model.cancelDownload(task)

        assert row_removed == [1]
        assert permanently_deleted == [1]
        assert model._task_list == []

    def test_cancel_download_failure_keeps_row_and_toasts(self, app, monkeypatch):
        """delete(wait=True) 返回 False 时行保留、不发信号、弹一次 ERROR toast

        toast 断言用 monkeypatch 替换 model 模块的 signal_bus：
        连真实信号再 disconnect() 会断开该信号的全部连接，影响其他测试
        """
        from gui.component.download_list import model as model_module

        task = make_task(1)
        task.Download.status = DownloadStatus.COMPLETED

        model = DownloadListModel([task])

        monkeypatch.setattr(model_module.task_manager, "delete", lambda *a, **kw: False)

        fake_bus = make_fake_signal_bus()
        monkeypatch.setattr(model_module, "signal_bus", fake_bus)

        row_removed = []
        permanently_deleted = []
        model.row_removed.connect(row_removed.append)
        model.task_permanently_deleted.connect(permanently_deleted.append)

        model.cancelDownload(task)

        # 行保留
        assert [t.Basic.task_id for t in model._task_list] == ["task-1"]

        # 两个信号都不发
        assert row_removed == []
        assert permanently_deleted == []

        # 弹了 ERROR toast
        calls = fake_bus.toast.show_long_message.calls

        assert len(calls) == 1
        assert calls[0][0] == ToastNotificationCategory.ERROR

        # title 与 content 非空：防「翻译 key 缺失返回空串」的回归
        assert calls[0][1]
        assert calls[0][2]

    def test_cancel_download_success_when_row_missing_does_not_emit_permanently_deleted(self, app, monkeypatch):
        """delete 成功但 getRow 返回 -1（task 不在当前页）时不 emit task_permanently_deleted

        分页模式下用户右键的 task 理论上一定在当前页，但 getRow 返回 -1 时
        removeRow 会失败，此时不该触发无意义的补位重载
        """
        from gui.component.download_list import model as model_module

        task = make_task(1)
        task.Download.status = DownloadStatus.COMPLETED

        model = DownloadListModel([])   # 空 model，getRow 返回 -1

        monkeypatch.setattr(model_module.task_manager, "delete", lambda *a, **kw: True)

        received = []
        model.task_permanently_deleted.connect(received.append)

        model.cancelDownload(task)

        assert received == []


class TestBatchCancel:
    def test_batch_cancel_success_emits_actual_removed_count(self, app, monkeypatch):
        """task_permanently_deleted 的 count 是实际移除数，不是传入任务数

        分页模式下 completed_tasks 可能包含不在当前页的任务，两者数量可能不同。
        用 removeTasks 的返回值而不是 len(completed_tasks)
        """
        from gui.component.download_list import model as model_module

        on_page = [make_task(i) for i in range(1, 3)]
        off_page = make_task(99)
        for t in on_page + [off_page]:
            t.Download.status = DownloadStatus.COMPLETED

        model = DownloadListModel(list(on_page))

        monkeypatch.setattr(model_module.task_manager, "delete_many", lambda *a, **kw: True)

        received = []
        model.task_permanently_deleted.connect(received.append)

        model.batch_cancel([on_page[0], off_page])

        # 传入 2 条，实际只在当前页移除了 1 条
        assert received == [1]

    def test_batch_cancel_failure_keeps_rows_and_toasts(self, app, monkeypatch):
        """delete_many 返回 False 时所有行保留、不发信号、弹一次 ERROR toast

        同 test_cancel_download_failure_keeps_row_and_toasts：用 monkeypatch
        替换 model 模块的 signal_bus，不碰真实信号
        """
        from gui.component.download_list import model as model_module

        tasks = [make_task(i) for i in range(1, 4)]
        for t in tasks:
            t.Download.status = DownloadStatus.COMPLETED

        model = DownloadListModel(list(tasks))

        monkeypatch.setattr(model_module.task_manager, "delete_many", lambda *a, **kw: False)

        fake_bus = make_fake_signal_bus()
        monkeypatch.setattr(model_module, "signal_bus", fake_bus)

        row_removed = []
        permanently_deleted = []
        model.row_removed.connect(row_removed.append)
        model.task_permanently_deleted.connect(permanently_deleted.append)

        model.batch_cancel()

        # 三行都保留
        assert len(model._task_list) == 3

        # 两个信号都不发
        assert row_removed == []
        assert permanently_deleted == []

        # 弹了 ERROR toast
        calls = fake_bus.toast.show_long_message.calls

        assert len(calls) == 1
        assert calls[0][0] == ToastNotificationCategory.ERROR

        # title 与 content 非空：防「翻译 key 缺失返回空串」的回归
        assert calls[0][1]
        assert calls[0][2]