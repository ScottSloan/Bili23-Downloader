from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QSize, Signal

from qfluentwidgets import BodyLabel, PushButton, FluentIcon

from .button import ToolButton

from util.common import ExtendedFluentIcon, signal_bus

class SearchWidget(QWidget):
    scrollToItem = Signal(object)
    checkMatches = Signal(list)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.matches_index_list = []
        self.current_match_index = -1
        self.init_UI()

    def init_UI(self):
        self.setContentsMargins(0, 0, 0, 0)

        self.matches_label = BodyLabel(self.tr("No matches found"), parent = self)

        self.prev_btn = ToolButton(FluentIcon.CARE_UP_SOLID, parent = self)
        self.prev_btn.setIconSize(QSize(9, 9))
        self.prev_btn.setFixedSize(28, 28)

        self.next_btn = ToolButton(FluentIcon.CARE_DOWN_SOLID, parent = self)
        self.next_btn.setIconSize(QSize(9, 9))
        self.next_btn.setFixedSize(28, 28)

        self.check_all_btn = PushButton(icon = ExtendedFluentIcon.SELECT_ALL, text = self.tr("Select All"), parent = self)
        self.check_all_btn.setFixedHeight(28)

        self.clear_all_btn = PushButton(icon = ExtendedFluentIcon.CLEAR, text = self.tr("Clear All"), parent = self)
        self.clear_all_btn.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.addWidget(self.matches_label)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.check_all_btn, alignment = Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.clear_all_btn, alignment = Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()

        self.connect_signals()

    def connect_signals(self):
        self.prev_btn.clicked.connect(self.on_prev)
        self.next_btn.clicked.connect(self.on_next)
        self.check_all_btn.clicked.connect(self.on_select_all)
        self.clear_all_btn.clicked.connect(self.on_clear_all)

    def on_prev(self):
        if not self.matches_index_list:
            return
            
        self.current_match_index -= 1

        if self.current_match_index < 0:
            self.current_match_index = len(self.matches_index_list) - 1
            
        self._update_label_and_scroll()

    def on_next(self):
        if not self.matches_index_list:
            return
            
        self.current_match_index += 1
        if self.current_match_index >= len(self.matches_index_list):
            self.current_match_index = 0
            
        self._update_label_and_scroll()
    
    def on_select_all(self):
        if not self.matches_index_list:
            return
        
        self.checkMatches.emit(self.matches_index_list)

    def on_clear_all(self):
        self.update_data([])

        signal_bus.parse.search_keyword.emit("")  # 发送空字符串表示清除搜索结果
        
    def _update_label_and_scroll(self):
        count = len(self.matches_index_list)
        if count == 0:
            return
            
        self.matches_label.setText(self.tr("{index} of {count}").format(
            index = self.current_match_index + 1,
            count = count
        ))
        
        index = self.matches_index_list[self.current_match_index]

        self.scrollToItem.emit(index)

    def update_data(self, search_data: list):
        count = len(search_data)

        self.matches_index_list = search_data

        if count == 0:
            self.current_match_index = -1
            self.matches_label.setText(self.tr("No matches found"))
        else:
            self.current_match_index = 0
            self._update_label_and_scroll()
