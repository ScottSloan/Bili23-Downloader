from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout

from qfluentwidgets import BodyLabel

from gui.component.widget.spinbox import SpinBox
from gui.component.widget.pager import Pager


class CompactPager(Pager):
    """
    自适应页码数量的 Pager

    Pager 原本固定显示最多 9 个页码按钮，5 位数页码（几万页）时一屏放不下，
    按钮被挤压或挤出可视区。这里覆写 get_contiguous_numbers，根据自身宽度
    动态决定显示几个页码按钮：窗口变宽时多显示、变窄时少显示。

    Pager.get_pager_range 会在首项 > 1 时替换为 [1, "...L"]，末项 < total_pages
    时替换为 ["...R", total_pages]。两个替换同时发生时，最少需要 5 个元素
    才能保留当前页不被省略号覆盖，因此 MIN_BUTTONS 下限是 5。
    """

    MIN_BUTTONS = 5
    MAX_BUTTONS = 7
    BUTTON_PADDING = 24           # 单个页码按钮左右内边距估算
    OTHER_WIDTH_ESTIMATE = 260    # prev + next + count_label + jump + 各种 spacing

    def __init__(self, parent_window, parent = None):
        self._max_buttons = self.MAX_BUTTONS
        self._updating_buttons = False

        super().__init__(parent_window, parent)

    def _estimate_button_width(self) -> int:
        # 用最大页码的位数估算按钮宽度，位数越多按钮越宽
        digits = len(str(max(1, self.total_pages)))
        fm = self.fontMetrics()

        return fm.horizontalAdvance("0" * digits) + self.BUTTON_PADDING

    def _calc_max_buttons(self) -> int:
        actual_min = min(self.MIN_BUTTONS, self.total_pages)
        actual_max = min(self.MAX_BUTTONS, self.total_pages)

        if self.width() <= 0:
            return actual_max

        available = max(0, self.width() - self.OTHER_WIDTH_ESTIMATE)
        btn_width = max(1, self._estimate_button_width())

        calc = available // btn_width

        return max(actual_min, min(actual_max, calc))

    def _calc_min_width(self) -> int:
        # 保证至少能放下 MIN_BUTTONS 个按钮，但不超 total_pages
        actual_buttons = min(self.MIN_BUTTONS, self.total_pages)

        return self.OTHER_WIDTH_ESTIMATE + actual_buttons * self._estimate_button_width()

    def get_contiguous_numbers(self):
        # 与原实现同样的三段逻辑，只是固定值换成 _max_buttons
        max_buttons = self._max_buttons
        half_before = (max_buttons - 1) // 2
        half_after = max_buttons - half_before - 1

        if self.current_page <= half_before:
            if self.total_pages <= max_buttons:
                return list(range(1, self.total_pages + 1))

            return list(range(1, max_buttons + 1))

        elif self.current_page > self.total_pages - half_after:
            if self.total_pages <= max_buttons:
                return list(range(1, self.total_pages + 1))

            return list(range(self.total_pages - max_buttons + 1, self.total_pages + 1))

        else:
            return list(range(self.current_page - half_before, self.current_page + half_after + 1))

    def update_data(self, data):
        self.total_pages = max(1, data.get("total_pages", 1) or 1)

        current_page = data.get("current_page", 1) or 1
        self.current_page = max(1, min(current_page, self.total_pages))

        total_items = data.get("total_items", 0)

        # 与解析页 Pager 一致的文案，放在页码列表与跳转按钮之间
        self.count_label.setText(
            self.tr("Page {pages} / {items} items").format(pages = self.total_pages, items = total_items)
        )

        # 页码位数可能变了（400 → 4000），按钮宽度估算随之变化，
        # 最小宽度要在 update_buttons 之前按新 total_pages 重算
        self.setMinimumWidth(self._calc_min_width())
        self._max_buttons = self._calc_max_buttons()

        self.update_buttons()

    def update_buttons(self):
        # 重建按钮期间阻止 resizeEvent 重入。num_layout 的 sizeHint 变化
        # 可能触发 Pager 自身的 resizeEvent，不加保护会递归
        self._updating_buttons = True
        try:
            super().update_buttons()
        finally:
            self._updating_buttons = False

    def resizeEvent(self, e):
        super().resizeEvent(e)

        if self._updating_buttons:
            return

        new_max = self._calc_max_buttons()

        if new_max != self._max_buttons:
            self._max_buttons = new_max
            self.update_buttons()


class PaginationBar(QWidget):
    """
    分页条：左侧 Pager（页码 · 共 X 页 / Y 个 · 跳转），右侧「[N] 条/页」。

    每页数量用 gui.component.widget.spinbox.SpinBox，单位用单独的 BodyLabel，
    与自动解析对话框里「解析间隔 + seconds」的结构一致。
    对外只暴露两个信号：pageChanged(目标页，0 起)、pageSizeChanged(新每页条数)。
    控件状态统一走 setState() 更新，内部 blockSignals，避免外部调用触发回环。
    """

    pageChanged = Signal(int)
    pageSizeChanged = Signal(int)

    MIN_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 2000
    DEFAULT_PAGE_SIZE = 100

    # 保留这个类属性，兼容 download.py 里可能仍在用的 PaginationBar.PAGE_SIZES[1]
    PAGE_SIZES = [50, 100, 200, 500]

    # 手动输入时 valueChanged 会逐字符触发（50 → 5 → 51），
    # 每次都发一次查询既浪费，又让多个查询并发返回、互相覆盖。
    # 这个窗口内只认最后一次输入
    PAGE_SIZE_DEBOUNCE_MS = 200

    def __init__(self, parent = None, parent_window = None):
        super().__init__(parent)

        self._page = 0
        self._total = 0
        self._page_size = self.DEFAULT_PAGE_SIZE
        self._pending_page_size = self._page_size

        # Pager 的 parent_window 用来挂跳转对话框，取顶层窗口
        self._parent_window = parent_window or self.window()

        self._page_size_timer = QTimer(self)
        self._page_size_timer.setSingleShot(True)
        self._page_size_timer.setInterval(self.PAGE_SIZE_DEBOUNCE_MS)
        self._page_size_timer.timeout.connect(self._emit_page_size_changed)

        self._init_ui()
        self._refresh()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(8)

        # Pager 靠左：页码 | 共 X 页 / Y 个 | 跳转
        self.pager = CompactPager(self._parent_window, self)
        self.pager.set_menu_actions(can_jump_page = True, can_auto_parse = False)
        self.pager.auto_parse_btn.hide()
        self.pager.pageChanged.connect(self._on_pager_page_changed)

        # 每页条数靠右
        self.per_page_label = BodyLabel("", self)

        # 与自动解析对话框里的「解析间隔」同一套控件：SpinBox + 单位 BodyLabel。
        # 不用 setFixedWidth：qfluentwidgets 的 SpinBox 内部有上下按钮，
        # 固定宽度会把数字区挤没，用 minimumWidth 让 sizeHint 决定实际宽度
        self.page_size_spin = SpinBox(self)
        self.page_size_spin.setMinimum(self.MIN_PAGE_SIZE)
        self.page_size_spin.setMaximum(self.MAX_PAGE_SIZE)
        self.page_size_spin.setValue(self._page_size)
        self.page_size_spin.setMinimumWidth(100)
        self.page_size_spin.valueChanged.connect(self._on_page_size_changed)

        self.page_size_unit_label = BodyLabel(self.tr("items / page"), self)

        layout.addWidget(self.pager)
        layout.addStretch(1)
        layout.addWidget(self.per_page_label)
        layout.addWidget(self.page_size_spin)
        layout.addWidget(self.page_size_unit_label)

    def setState(self, page: int, total: int, page_size: int = None):
        if page_size is not None and page_size != self._page_size:
            self._page_size = page_size
            self._pending_page_size = page_size

            # 同步输入框但屏蔽信号，避免触发 valueChanged 造成回环
            self.page_size_spin.blockSignals(True)
            try:
                self.page_size_spin.setValue(page_size)
            finally:
                self.page_size_spin.blockSignals(False)

        self._page = page
        self._total = total

        self._refresh()

    def page(self) -> int:
        return self._page

    def page_size(self) -> int:
        return self._page_size

    def _total_pages(self) -> int:
        return max(1, (self._total + self._page_size - 1) // self._page_size)

    def _refresh(self):
        # CompactPager.update_data 内部会设置 count_label 文本（与解析页一致）、
        # 重算最小宽度与按钮数、重建按钮
        self.pager.update_data({
            "current_page": self._page + 1,
            "total_pages": self._total_pages(),
            "total_items": self._total,
        })

    # ---------- 每页条数 ----------

    def _on_page_size_changed(self, value: int):
        # 只记下最新值，等防抖窗口结束后再发出去
        self._pending_page_size = value
        self._page_size_timer.start()

    def _emit_page_size_changed(self):
        value = self._pending_page_size

        if value == self._page_size:
            return

        self._page_size = value
        self.pageSizeChanged.emit(value)

    # ---------- 翻页 ----------

    def _on_pager_page_changed(self, page: int):
        # Pager 发 1 起页码，本控件对外发 0 起
        target = page - 1

        if target != self._page:
            self.pageChanged.emit(target)