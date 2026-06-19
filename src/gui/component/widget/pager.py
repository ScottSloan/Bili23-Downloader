from PySide6.QtWidgets import QWidget, QHBoxLayout, QApplication
from PySide6.QtCore import QSize, Signal

from qfluentwidgets import FluentIcon, BodyLabel, RoundMenu, Action

from .button import PagerNumberButton, TransparentToolButton, ToolButton

from util.common.enum import ToastNotificationCategory
from util.common.icon import ExtendedFluentIcon
from util.common.signal_bus import signal_bus

from typing import List

class Pager(QWidget):
    pageChanged = Signal(int)

    def __init__(self, parent_window: QWidget, parent = None):
        super().__init__(parent)

        self.parent_window = parent_window

        self.total_pages = 1
        self.current_page = 1

        self.can_jump_page = False
        self.can_auto_parse = False

        self.btn_list: List[PagerNumberButton] = []

        self.init_UI()

        self.update_buttons()

        self.menu_btn.clicked.connect(self.on_show_more_menu)

    def init_UI(self):
        self.prev_btn = TransparentToolButton(FluentIcon.CARE_LEFT_SOLID)
        self.prev_btn.setIconSize(QSize(9, 9))
        self.prev_btn.setToolTip(self.tr("Previous page"))

        self.next_btn = TransparentToolButton(FluentIcon.CARE_RIGHT_SOLID)
        self.next_btn.setIconSize(QSize(9, 9))
        self.next_btn.setToolTip(self.tr("Next page"))

        self.count_label = BodyLabel(parent = self)

        self.menu_btn = ToolButton(FluentIcon.MORE)
        self.menu_btn.setFixedSize(28, 28)

        self.num_layout = QHBoxLayout()
        self.num_layout.setContentsMargins(0, 0, 0, 0)
        self.num_layout.setSpacing(5)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.main_layout.addWidget(self.prev_btn)
        self.main_layout.addLayout(self.num_layout)
        self.main_layout.addWidget(self.next_btn)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(self.count_label)
        self.main_layout.addSpacing(5)
        self.main_layout.addWidget(self.menu_btn)
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

        self.count_label.setText(self.tr("{total_pages} total / {total_items} items").format(
            total_pages = self.total_pages,
            total_items = data.get("total_items", 0)
        ))

        self.update_buttons()

    def on_show_more_menu(self):
        menu = RoundMenu(parent = self)

        if self.can_jump_page:
            menu.addAction(self._create_action(FluentIcon.DOCUMENT, self.tr("Jump to page"), self.on_jump_to_page))

        if self.can_auto_parse:
            menu.addAction(self._create_action(ExtendedFluentIcon.AUTOMATION, self.tr("Auto-parse pagination"), self.parent_window.on_auto_parse))

        pos = self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft())

        menu.exec(pos)

    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)

        return action
    
    def on_jump_to_page(self):
        from ...dialog.misc.jump_to_page import JumpToPageDialog

        dialog = JumpToPageDialog(self.parent_window)

        if dialog.exec():
            page_number = dialog.page

            if 1 <= page_number <= self.total_pages:
                self.on_change_page(page_number)

            else:
                signal_bus.toast.show.emit(ToastNotificationCategory.WARNING, self.tr("Invalid page number"), self.tr("Please enter a number between 1 and {total_pages}").format(total_pages = self.total_pages))
    
    def set_menu_actions(self, can_jump_page: bool, can_auto_parse: bool):
        self.can_jump_page = can_jump_page
        self.can_auto_parse = can_auto_parse
