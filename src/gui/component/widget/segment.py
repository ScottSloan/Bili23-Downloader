from PySide6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget

from qfluentwidgets import FluentIcon, RoundMenu, Action

from .button import ToolButton
from .search import SearchWidget
from .pager import Pager

from util.common import ExtendedFluentIcon

class SegmentedWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setFixedHeight(32)

        self.init_UI()

    def init_UI(self):
        self.setContentsMargins(0, 0, 0, 0)

        self.choice_btn = ToolButton(ExtendedFluentIcon.SINGLE_CHOICE, self)

        self.stack_widget = QStackedWidget(self)
        self.stack_widget.setContentsMargins(0, 0, 0, 0)
        self.stack_widget.setFixedHeight(32)

        self.search_widget = SearchWidget(self)
        self.pager_widget = Pager(self)

        self.stack_widget.addWidget(self.search_widget)
        self.stack_widget.addWidget(self.pager_widget)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.choice_btn)
        layout.addWidget(self.stack_widget)
        layout.addStretch()

        self.choice_btn.clicked.connect(self.on_show_choice_menu)

    def on_show_choice_menu(self):
        menu = RoundMenu(parent = self)

        menu.addAction(self._create_action(FluentIcon.SEARCH, self.tr("Search"), self.switch_to_search))
        menu.addAction(self._create_action(ExtendedFluentIcon.CHOOSE_PAGE, self.tr("Page"), self.switch_to_pager))

        menu.exec(self.choice_btn.mapToGlobal(self.choice_btn.rect().bottomLeft()))

    def show_search(self, search_data: dict):
        self.ensure_visible()
    
        self.stack_widget.setCurrentWidget(self.search_widget)

        self.search_widget.update_data(search_data)

    def show_pager(self, pagination_data: dict):
        self.ensure_visible()
    
        self.stack_widget.setCurrentWidget(self.pager_widget)

        self.pager_widget.update_data(pagination_data)

    def hide_search(self):
        self.search_widget.update_data([])

        self.hide()

    def hide_pager(self):
        self.pager_widget.update_data({})

        self.hide()

    def ensure_visible(self):
        # 如果分段组件本身没有显示，就先显示分段组件
        if not self.isVisible():
            self.show()

    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)

        return action
    
    def switch_to_search(self):
        self.stack_widget.setCurrentIndex(0)
    
    def switch_to_pager(self):
        self.stack_widget.setCurrentIndex(1)
