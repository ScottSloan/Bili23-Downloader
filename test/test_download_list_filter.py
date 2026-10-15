"""
gui/component/download_list/proxy_model.py —— 下载列表的搜索与筛选。

除了「筛得对不对」，这里重点钉住两件不显眼的事：

1. 筛选生效时，顶栏的批量操作只作用于看得见的任务。「全部删除」「全部清除」没有二次确认，
   若仍按整个列表执行，会一键删掉一批根本没显示出来的任务。
2. 代理模型关着 dynamicSortFilter，被筛掉的行重新放出来时必须回到排序后的位置，
   而不是接在末尾。
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.component.download_list.model import DownloadListModel
from gui.component.download_list.proxy_model import DownloadListProxyModel

from util.common.enum import DownloadStatus, DownloadType
from util.parse.episode.tree import Attribute

from types import SimpleNamespace

import pytest


@pytest.fixture(scope = "module")
def app():
    return QApplication.instance() or QApplication([])


def make_task(
    value: int, title = "", status = DownloadStatus.QUEUED, attribute = Attribute.VIDEO_BIT,
    download_type = DownloadType.VIDEO | DownloadType.AUDIO, uploader = "", collection_title = ""
):
    """筛选只读 Basic / File / Episode / Download 上的几个字段，不必构造完整的 TaskInfo"""
    return SimpleNamespace(
        Basic = SimpleNamespace(
            task_id = f"task-{value}",
            created_time = value,
            completed_time = value,
            show_title = title or f"title-{value}"
        ),
        File = SimpleNamespace(name = ""),
        Episode = SimpleNamespace(
            attribute = attribute,
            uploader = uploader,
            bvid = f"BV{value}",
            parent_title = "",
            collection_title = collection_title,
            series_title = "",
            season_title = "",
            favorites_name = ""
        ),
        Download = SimpleNamespace(
            type = download_type,
            total_size = value,
            progress = value,
            status = status,
            info_label = "",
            status_label = ""
        )
    )


def make_proxy(tasks: list, key = "created_time", ascending = True):
    source = DownloadListModel([])

    proxy = DownloadListProxyModel()
    proxy.setSourceModel(source)
    proxy.enableSorting(key, ascending)
    proxy.appendRows(tasks)

    return proxy


def apply(proxy: DownloadListProxyModel, **kwargs):
    """筛选条件改动走 50 毫秒去抖，测试里直接冲刷，不等定时器"""
    if "text" in kwargs:
        proxy.setFilterText(kwargs["text"])

    if "statuses" in kwargs:
        proxy.setStatusFilter(kwargs["statuses"])

    if "media_types" in kwargs:
        proxy.setMediaTypeFilter(kwargs["media_types"])

    proxy._flushPendingRefresh()


def visible_ids(proxy: DownloadListProxyModel):
    return [
        proxy.index(row, 0).data(Qt.ItemDataRole.UserRole).Basic.created_time
        for row in range(proxy.rowCount())
    ]


def test_search_matches_all_keywords_case_insensitively(app):
    proxy = make_proxy([
        make_task(1, title = "Minecraft 生存", uploader = "Alice"),
        make_task(2, title = "Minecraft 建筑", uploader = "Bob"),
        make_task(3, title = "原神", uploader = "alice", collection_title = "旅行合集"),
    ])

    apply(proxy, text = "minecraft")
    assert visible_ids(proxy) == [1, 2]

    # 空格分隔的多个关键词须同时命中，可以跨字段（标题 + UP 主）
    apply(proxy, text = "  ALICE   minecraft ")
    assert visible_ids(proxy) == [1]

    # 合集名、BV 号也在搜索范围内
    apply(proxy, text = "旅行")
    assert visible_ids(proxy) == [3]

    apply(proxy, text = "bv2")
    assert visible_ids(proxy) == [2]

    apply(proxy, text = "")
    assert visible_ids(proxy) == [1, 2, 3]
    assert not proxy.isFiltering()


def test_status_and_media_type_filters_combine(app):
    proxy = make_proxy([
        make_task(1, status = DownloadStatus.PAUSED),
        make_task(2, status = DownloadStatus.FAILED),
        make_task(3, status = DownloadStatus.PAUSED, attribute = Attribute.BANGUMI_BIT),
        # 仅下载音频的投稿视频，与封面角标一致归为「音频」
        make_task(4, status = DownloadStatus.PAUSED, download_type = DownloadType.AUDIO),
    ])

    apply(proxy, statuses = {DownloadStatus.PAUSED})
    assert visible_ids(proxy) == [1, 3, 4]

    apply(proxy, media_types = {"VIDEO"})
    assert visible_ids(proxy) == [1]

    apply(proxy, media_types = {"BANGUMI", "AUDIO"})
    assert visible_ids(proxy) == [3, 4]

    proxy.clearFilter()
    proxy._flushPendingRefresh()
    assert visible_ids(proxy) == [1, 2, 3, 4]


@pytest.mark.parametrize("ascending", [True, False])
def test_rows_shown_again_keep_sort_order(app, ascending):
    """被筛掉的行重新放出来时要落回排序后的位置，而不是整批接在末尾"""
    proxy = make_proxy([make_task(value) for value in [3, 1, 5, 2, 4]], ascending = ascending)

    apply(proxy, text = "title-2")
    assert visible_ids(proxy) == [2]

    apply(proxy, text = "")
    assert visible_ids(proxy) == sorted(range(1, 6), reverse = not ascending)


def test_status_filter_follows_status_changes(app):
    paused = make_task(1, status = DownloadStatus.PAUSED)
    downloading = make_task(2, status = DownloadStatus.DOWNLOADING)

    proxy = make_proxy([paused, downloading])

    apply(proxy, statuses = {DownloadStatus.PAUSED})
    assert visible_ids(proxy) == [1]

    paused.Download.status = DownloadStatus.DOWNLOADING
    downloading.Download.status = DownloadStatus.PAUSED

    proxy.onUpdateData(paused)
    proxy._flushPendingRefresh()

    assert visible_ids(proxy) == [2]


def test_batch_operations_only_touch_visible_tasks(app, monkeypatch):
    tasks = [make_task(value, status = DownloadStatus.COMPLETED) for value in range(1, 5)]
    proxy = make_proxy(tasks)

    received = []

    monkeypatch.setattr(proxy.sourceModel(), "batch_cancel", lambda task_list = None: received.append(task_list))

    # 未筛选时传 None，由源模型作用于整个列表，行为与加筛选之前一致
    proxy.batch_cancel()
    assert received.pop() is None

    apply(proxy, text = "title-3")
    proxy.batch_cancel()
    assert [task.Basic.created_time for task in received.pop()] == [3]


def test_source_batch_cancel_respects_task_list(app, monkeypatch):
    """源模型拿到目标列表后只删这几条，其余任务原样留在列表里"""
    from gui.component.download_list import model as model_module

    deleted = []

    monkeypatch.setattr(model_module.task_manager, "delete_many", lambda task_list, completed: deleted.extend(task_list))

    tasks = [make_task(value, status = DownloadStatus.COMPLETED) for value in range(1, 4)]
    source = DownloadListModel(list(tasks))

    source.batch_cancel([tasks[1]])

    assert deleted == [tasks[1]]
    assert [task.Basic.created_time for task in source._task_list] == [1, 3]


def make_search_box(available_width: int):
    from gui.component.download_list.top_widget import ExpandableSearchBox

    search_box = ExpandableSearchBox()
    search_box.setAvailableWidth(available_width)

    return search_box


def send_focus_out(search_box, reason = Qt.FocusReason.MouseFocusReason):
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtCore import QEvent

    QApplication.sendEvent(search_box.line_edit, QFocusEvent(QEvent.Type.FocusOut, reason))


def test_search_box_pinned_only_when_width_is_ample(app):
    from gui.component.download_list.top_widget import ExpandableSearchBox

    ample = ExpandableSearchBox.FULL_WIDTH + ExpandableSearchBox.SPARE_WIDTH

    search_box = make_search_box(ample)
    assert not search_box.isCollapsed()
    assert search_box.line_edit.width() == ExpandableSearchBox.FULL_WIDTH

    # 刚好放得下搜索框、却不留空白时也要收起，否则顶栏看着仍是塞满的
    search_box.setAvailableWidth(ample - 1)
    assert search_box.isCollapsed()


def test_collapsed_search_box_expands_and_collapses(app):
    from gui.component.download_list.top_widget import ExpandableSearchBox

    search_box = make_search_box(150)

    search_box.search_btn.click()
    assert not search_box.isCollapsed()
    assert search_box.line_edit.width() == 150

    # 弹出右键菜单导致的失焦不收起
    send_focus_out(search_box, Qt.FocusReason.PopupFocusReason)
    assert not search_box.isCollapsed()

    send_focus_out(search_box)
    assert search_box.isCollapsed()

    # 空间再少也不窄于 MIN_WIDTH
    search_box.setAvailableWidth(50)
    search_box.expand()
    assert search_box.line_edit.width() == ExpandableSearchBox.MIN_WIDTH


def test_search_box_stays_expanded_while_keyword_present(app):
    """有搜索词时只剩一个图标，筛选在生效却看不出来，用户会以为任务丢了"""
    search_box = make_search_box(150)

    search_box.expand()
    search_box.line_edit.setText("keyword")

    send_focus_out(search_box)
    assert not search_box.isCollapsed()

    # 窗口从宽变窄、搜索框由常驻转为可收起时，同样保持展开
    search_box.setAvailableWidth(1000)
    search_box.setAvailableWidth(150)
    assert not search_box.isCollapsed()


def test_escape_clears_and_collapses_search_box(app):
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import QEvent

    search_box = make_search_box(150)
    received = []
    search_box.textChanged.connect(received.append)

    search_box.expand()
    search_box.line_edit.setText("keyword")

    QApplication.sendEvent(
        search_box.line_edit,
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    )

    assert search_box.text() == ""
    assert search_box.isCollapsed()
    # 清空也要经 textChanged 通知列表撤销搜索
    assert received == ["keyword", ""]
