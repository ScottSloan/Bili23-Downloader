from PySide6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget

from qfluentwidgets import SegmentedToolWidget, FluentIcon

from gui.component.widget.search import SearchWidget
from gui.component.widget.pager import Pager

from util.common import ExtendedFluentIcon

class SegmentedWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setFixedHeight(32)

        self.init_UI()

    def init_UI(self):
        self.setContentsMargins(0, 0, 0, 0)

        self.stack_widget = QStackedWidget(self)
        self.stack_widget.setContentsMargins(0, 0, 0, 0)
        self.stack_widget.setFixedHeight(32)

        self.search_widget = SearchWidget(self)
        self.pager_widget = Pager(self)

        self.stack_widget.addWidget(self.search_widget)
        self.stack_widget.addWidget(self.pager_widget)

        self.segmented_widget = SegmentedToolWidget(self)
        self.segmented_widget.setFixedSize(60, 32)

        self.segmented_widget.addItem("search", FluentIcon.SEARCH, lambda: self.stack_widget.setCurrentIndex(0))
        self.segmented_widget.addItem("pager", ExtendedFluentIcon.CHOOSE_PAGE, lambda: self.stack_widget.setCurrentIndex(1))

        self.segmented_widget.setCurrentItem("search")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.segmented_widget)
        layout.addWidget(self.stack_widget)
        layout.addStretch()

    def show_search(self, search_data: dict):
        self.make_visible()
    
        self.segmented_widget.setCurrentItem("search")
        self.stack_widget.setCurrentWidget(self.search_widget)

        self.search_widget.update_data(search_data)

    def show_pager(self, pagination_data: dict):
        self.make_visible()
    
        self.segmented_widget.setCurrentItem("pager")
        self.stack_widget.setCurrentWidget(self.pager_widget)

        self.pager_widget.update_data(pagination_data)

    def hide_search(self):
        self.search_widget.update_data([])

        self.hide()

    def hide_pager(self):
        self.pager_widget.update_data({})

        self.hide()

    def make_visible(self):
        # 如果分段组件本身没有显示，就先显示分段组件
        if not self.isVisible():
            self.show()
