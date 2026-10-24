"""
已完成列表的分页条（CompactPager + PaginationBar）。

CompactPager 按自身宽度动态决定显示几个页码按钮，PaginationBar 把手动改每页条数
的连续输入防抖成一次信号。这两处都不会在类型检查里暴露，但一旦回归，用户看到的是
页码挤成一团或列表因连续重查而卡死。
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer

from gui.component.download_list.pagination_bar import CompactPager, PaginationBar

import pytest


@pytest.fixture(scope = "module")
def app():
    return QApplication.instance() or QApplication([])


class TestCompactPager:
    def test_contiguous_numbers_at_head(self, app):
        pager = CompactPager(None)
        pager.total_pages = 400
        pager.current_page = 1
        pager._max_buttons = 7

        numbers = pager.get_contiguous_numbers()

        assert numbers[0] == 1
        assert len(numbers) <= 7

    def test_contiguous_numbers_at_middle(self, app):
        pager = CompactPager(None)
        pager.total_pages = 400
        pager.current_page = 200
        pager._max_buttons = 7

        numbers = pager.get_contiguous_numbers()

        assert 200 in numbers
        assert len(numbers) <= 7

    def test_contiguous_numbers_at_tail(self, app):
        pager = CompactPager(None)
        pager.total_pages = 400
        pager.current_page = 400
        pager._max_buttons = 7

        numbers = pager.get_contiguous_numbers()

        assert numbers[-1] == 400
        assert len(numbers) <= 7

    def test_total_less_than_max_returns_all(self, app):
        pager = CompactPager(None)
        pager.total_pages = 3
        pager.current_page = 2
        pager._max_buttons = 7

        assert pager.get_contiguous_numbers() == [1, 2, 3]

    def test_max_buttons_bounded_for_any_width(self, app):
        # 具体数值取决于字体与 DPI，这里只验证落在 [MIN, MAX] 区间内
        pager = CompactPager(None)
        pager.total_pages = 40000
        pager.current_page = 20000

        for width in (100, 300, 600, 1000, 2000):
            pager.resize(width, 32)

            n = pager._calc_max_buttons()

            assert CompactPager.MIN_BUTTONS <= n <= CompactPager.MAX_BUTTONS

    def test_update_data_sets_count_label(self, app):
        # pagination_bar.py 的 tr 源串已改为英文 "Page {pages} / {items} items"，
        # 不再含中文「共」，断言语义不变，只改字符串匹配
        pager = CompactPager(None)

        pager.update_data({"current_page": 1, "total_pages": 400, "total_items": 39241})

        assert "Page" in pager.count_label.text()
        assert "400" in pager.count_label.text()
        assert "39241" in pager.count_label.text()


class TestPaginationBar:
    def test_set_state_syncs_spinbox_without_signal(self, app):
        bar = PaginationBar()

        received = []
        bar.pageSizeChanged.connect(received.append)

        bar.setState(0, 500, 200)

        assert bar.page_size_spin.value() == 200
        assert bar.page_size() == 200
        # 同步显示不应触发信号，否则会反过来再查一次
        assert received == []

    def test_set_state_updates_pager(self, app):
        bar = PaginationBar()

        bar.setState(3, 1000, 100)

        assert bar.pager.total_pages == 10
        assert bar.pager.current_page == 4

    def test_debounce_only_emits_last_value(self, app):
        bar = PaginationBar()

        received = []
        bar.pageSizeChanged.connect(received.append)

        bar.page_size_spin.setValue(50)
        bar.page_size_spin.setValue(200)
        bar.page_size_spin.setValue(500)

        # 防抖窗口未到，尚未发出
        assert received == []

        loop = QEventLoop()
        QTimer.singleShot(300, loop.quit)
        loop.exec()

        assert received == [500]
        assert bar.page_size() == 500

    def test_debounce_does_not_emit_when_value_unchanged(self, app):
        bar = PaginationBar()
        bar.setState(0, 500, 100)

        received = []
        bar.pageSizeChanged.connect(received.append)

        # 模拟一次相同值：SpinBox 内部设置或 setState 回写
        bar._pending_page_size = 100
        bar._emit_page_size_changed()

        assert received == []

    def test_pager_page_changed_converts_to_zero_based(self, app):
        bar = PaginationBar()
        bar.setState(0, 500, 100)

        received = []
        bar.pageChanged.connect(received.append)

        bar.pager.on_change_page(3)

        # Pager 发 3（1 起），对外发 2（0 起）
        assert received == [2]