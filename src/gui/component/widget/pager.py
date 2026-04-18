from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import QSize, Signal

from qfluentwidgets import TransparentToolButton, FluentIcon

from .button import PagerNumberButton

from typing import List

class Pager(QWidget):
    pageChanged = Signal(int)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.total_pages = 1
        self.current_page = 1

        self.btn_list: List[PagerNumberButton] = []

        self.init_UI()

        self.update_buttons()

    def init_UI(self):
        self.prev_btn = TransparentToolButton(FluentIcon.CARE_LEFT_SOLID)
        self.prev_btn.setIconSize(QSize(9, 9))
        self.next_btn = TransparentToolButton(FluentIcon.CARE_RIGHT_SOLID)
        self.next_btn.setIconSize(QSize(9, 9))

        self.num_layout = QHBoxLayout()
        self.num_layout.setContentsMargins(0, 0, 0, 0)
        self.num_layout.setSpacing(5)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.main_layout.addWidget(self.prev_btn)
        self.main_layout.addLayout(self.num_layout)
        self.main_layout.addWidget(self.next_btn)
        self.main_layout.addStretch()

        self.prev_btn.clicked.connect(lambda: self.on_change_page(self.current_page - 1))
        self.next_btn.clicked.connect(lambda: self.on_change_page(self.current_page + 1))

    def get_contiguous_numbers(self):
        # 左侧
        if self.current_page <= 4:
            if self.total_pages < 9:
                return list(range(1, self.total_pages + 1))
            else:
                return list(range(1, 10))
            
        # 右侧
        elif self.current_page > self.total_pages - 4:
            if self.total_pages < 9:
                return list(range(1, self.total_pages + 1))
            else:
                return list(range(self.total_pages - 8, self.total_pages + 1))

        # 中间
        else:
            return list(range(self.current_page - 4, self.current_page + 5))

    def get_pager_range(self):
        contiguous_numbers = self.get_contiguous_numbers()

        if contiguous_numbers[0] > 1:
            contiguous_numbers[0] = 1
            contiguous_numbers[1] = "...L"

        if contiguous_numbers[-1] < self.total_pages:
            contiguous_numbers[-2] = "...R"
            contiguous_numbers[-1] = self.total_pages

        return contiguous_numbers

    def update_buttons(self):
        # 清空之前的按钮
        self.blockSignals(True)

        for btn in self.btn_list:
            btn.deleteLater()

        self.btn_list.clear()

        # 生成新的按钮
        for item in self.get_pager_range():
            if item == "...L":
                number = self.current_page - 5
                btn = PagerNumberButton("...", number, self)
            elif item == "...R":
                number = self.current_page + 5
                btn = PagerNumberButton("...", number, self)
            else:
                number = item
                btn = PagerNumberButton(str(item), number, self)

            btn.setChecked(item == self.current_page)
            btn.setCheckable(item == self.current_page)
            btn.clicked.connect(lambda checked, num = number: self.on_change_page(num))
            
            self.num_layout.addWidget(btn)
            self.btn_list.append(btn)

        self.prev_btn.setEnabled(not self.current_page == 1)
        self.next_btn.setEnabled(not self.current_page == self.total_pages)

        self.blockSignals(False)

    def on_change_page(self, page: int):
        self.current_page = page

        self.update_buttons()

        self.pageChanged.emit(page)

    def update_data(self, data: dict):
        self.total_pages = data.get("total_pages", 1)
        self.current_page = 1

        # 空数据时仍显示一个按钮，但不可点击
        if self.total_pages == 0:
            self.total_pages = 1

        if current_page := data.get("current_page", 1):
            self.current_page = current_page

        self.update_buttons()
