"""
同时运行的 FFmpeg 合并数（#490）。

合并并发原先写死为 1：并行合并曾把机器拖到卡死。现在开放成设置项，但默认值仍然是 1，
设置里也明确推荐保持 1。这里钉住默认值与上限，以及调度器确实按设置值放行。
"""

from PySide6.QtWidgets import QApplication
import pytest

from types import SimpleNamespace


@pytest.fixture(scope = "module")
def app():
    # 构造 QWidget 之前必须已有 QApplication，否则 Qt 直接中止进程，连堆栈都不留
    return QApplication.instance() or QApplication([])


def test_default_is_serial():
    # 默认值是踩过坑之后的结论，改动前先看 config.merge_parallel 上的注释
    from util.common.config import config

    assert config.merge_parallel.defaultValue == 1
    assert config.merge_parallel.range == (1, 4)


@pytest.fixture
def merge_model(monkeypatch):
    from util.common.enum import DownloadStatus
    from util.download.task.info import TaskInfo
    from gui.component.download_list import model as model_module

    tasks = []

    for index in range(5):
        task = TaskInfo()
        task.Basic.task_id = f"task-{index}"
        task.Download.status = DownloadStatus.FFMPEG_QUEUED
        tasks.append(task)

    model = model_module.DownloadListModel(tasks)

    # 真正启动合并要拉起 Downloader 与 FFmpeg，这里只关心调度器放行了几个
    def start_merge(task):
        task.Download.status = DownloadStatus.MERGING

    monkeypatch.setattr(model, "togglePauseResume", start_merge)

    def set_limit(limit):
        monkeypatch.setattr(model_module, "config", SimpleNamespace(get = lambda item: limit, merge_parallel = None))

    return model, tasks, set_limit


def merging_count(tasks):
    from util.common.enum import DownloadStatus

    return sum(task.Download.status == DownloadStatus.MERGING for task in tasks)


@pytest.mark.parametrize("limit", [1, 2, 4])
def test_scheduler_follows_limit(merge_model, limit):
    model, tasks, set_limit = merge_model

    set_limit(limit)
    model.manageConcurrentMerges()

    assert merging_count(tasks) == limit


def test_running_merges_count_toward_limit(merge_model):
    from util.common.enum import DownloadStatus

    model, tasks, set_limit = merge_model

    # 已经在合并、转换的任务都占额度，调度器只补足差额
    tasks[0].Download.status = DownloadStatus.CONVERTING

    set_limit(2)
    model.manageConcurrentMerges()

    assert merging_count(tasks) == 1
    assert tasks[0].Download.status == DownloadStatus.CONVERTING


def test_guide_link_opens_dialog(app, monkeypatch):
    # 说明弹窗以主窗口为父，而 GroupWidget 只在 addGroup 时从卡片抄到 parent_window。
    # 卡片没设这个属性时，点链接会在槽函数里抛 AttributeError，界面上表现为点了没反应
    from PySide6.QtWidgets import QWidget

    from gui.component import dialog
    from gui.component.setting.card import DownloadConcurrencySettingCard, GroupWidget

    opened = []

    class FakeMessageBox:
        def __init__(self, title, content, parent):
            opened.append(parent)

        def hideCancelButton(self):
            pass

        def show(self):
            pass

    monkeypatch.setattr(dialog, "MessageBox", FakeMessageBox)

    main_window = QWidget()
    card = DownloadConcurrencySettingCard(main_window)

    group = next(group for group in card.findChildren(GroupWidget) if hasattr(group, "hyper_label"))
    group.hyper_label.clicked.emit()

    assert opened == [main_window]
