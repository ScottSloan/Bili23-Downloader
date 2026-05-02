from PySide6.QtWidgets import QStackedWidget, QWidget, QHBoxLayout, QGridLayout
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Signal

from qfluentwidgets import (
    PrimaryPushButton, PushButton, FluentIcon, FlyoutViewBase, BodyLabel, ComboBox, Flyout, FlyoutAnimationType,
    isDarkTheme
)

from gui.component.widget import ToolButton

from util.common import ExtendedFluentIcon, config, Directory, signal_bus

class SortFlyoutWidget(FlyoutViewBase):
    closed = Signal()

    def __init__(self, parent = None, sort_by_key_dict: dict = None, trigger_signal_func = None, sort_by_key = None):
        super().__init__(parent)

        self.sort_by_key_dict = sort_by_key_dict
        self.trigger_signal_func = trigger_signal_func
        self.sort_by_key = sort_by_key
        self.ascending = True

        self.init_UI()

    def init_UI(self):
        sort_by_lab = BodyLabel(self.tr("Sort By"), self)

        self.sort_by_choice = ComboBox(self)
        
        for label, key in self.sort_by_key_dict.items():
            self.sort_by_choice.addItem(label, userData = key)

            if key == self.sort_by_key:
                self.sort_by_choice.setCurrentIndex(self.sort_by_choice.count() - 1)

        sort_direction_lab = BodyLabel(self.tr("Sort Direction"), self)
        self.sort_ascending_btn = ToolButton(ExtendedFluentIcon.SORT, self)
        self.sort_ascending_btn.setToolTip(self.tr("Ascending"))
        self.sort_descending_btn = ToolButton(ExtendedFluentIcon.SORT_REVERSE, self)
        self.sort_descending_btn.setToolTip(self.tr("Descending"))

        sort_direction_layout = QHBoxLayout()
        sort_direction_layout.setContentsMargins(0, 0, 0, 0)
        sort_direction_layout.addWidget(self.sort_ascending_btn)
        sort_direction_layout.addWidget(self.sort_descending_btn)
        sort_direction_layout.addStretch()

        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(18, 12, 18, 12)
        main_layout.addWidget(sort_by_lab, 0, 0)
        main_layout.addWidget(self.sort_by_choice, 0, 2)
        main_layout.addWidget(sort_direction_lab, 1, 0)
        main_layout.addLayout(sort_direction_layout, 1, 2)

        main_layout.setColumnMinimumWidth(1, 12)

        self.connect_signals()

    def connect_signals(self):
        self.sort_by_choice.currentIndexChanged.connect(self.on_sort_by_changed)
        self.sort_ascending_btn.clicked.connect(self.on_sort_ascending)
        self.sort_descending_btn.clicked.connect(self.on_sort_descending)

    def on_sort_by_changed(self, index):
        self.sort_by_key = self.sort_by_choice.itemData(index)

        self.trigger_signal()

    def on_sort_ascending(self):
        self.ascending = True

        self.trigger_signal()

    def on_sort_descending(self):
        self.ascending = False

        self.trigger_signal()

    def trigger_signal(self):
        if self.trigger_signal_func:
            self.trigger_signal_func(self.sort_by_key, self.ascending)

        self.closed.emit()

class FilterFlyoutWidget(FlyoutViewBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        pass

class Separator(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setFixedWidth(5)

        self.setContentsMargins(10, 5, 10, 5)

        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)

        c = 255 if isDarkTheme() else 0

        pen = QPen(QColor(c, c, c, 50))
        pen.setCosmetic(True)

        painter.setPen(pen)

        painter.drawLine(2, 0, 2, self.height())

class TopStackedWidget(QStackedWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.download_interface = parent

        self.setFixedHeight(32)

        self.init_UI()

    def init_UI(self):
        downloading_widget = QWidget()
        downloading_widget.setContentsMargins(0, 0, 0, 0)

        self.sort_downloading_list_btn = ToolButton(ExtendedFluentIcon.SORT, self)
        self.sort_downloading_list_btn.setToolTip(self.tr("Sort"))

        separator_1 = Separator(self)

        self.start_all_btn = PrimaryPushButton(FluentIcon.PLAY, self.tr("Start All"), self)
        self.pause_all_btn = PushButton(FluentIcon.PAUSE, self.tr("Pause All"), self)
        self.delete_all_btn = PushButton(FluentIcon.DELETE, self.tr("Delete All"), self)

        downloading_layout = QHBoxLayout(downloading_widget)
        downloading_layout.setContentsMargins(0, 0, 0, 0)
        downloading_layout.addStretch()
        downloading_layout.addWidget(self.sort_downloading_list_btn)
        downloading_layout.addWidget(separator_1)
        downloading_layout.addWidget(self.start_all_btn)
        downloading_layout.addWidget(self.pause_all_btn)
        downloading_layout.addWidget(self.delete_all_btn)

        completed_widget = QWidget()
        completed_widget.setContentsMargins(0, 0, 0, 0)

        self.sort_completed_list_btn = ToolButton(ExtendedFluentIcon.SORT, self)
        self.sort_completed_list_btn.setToolTip(self.tr("Sort"))

        separator_2 = Separator(self)

        self.open_directory_btn = PushButton(FluentIcon.FOLDER, self.tr("Open Directory"), self)
        self.open_directory_btn.setMinimumWidth(110)
        self.clear_all_btn = PushButton(ExtendedFluentIcon.CLEAR, self.tr("Clear All"))
        self.clear_all_btn.setMinimumWidth(110)

        completed_layout = QHBoxLayout(completed_widget)
        completed_layout.setContentsMargins(0, 0, 0, 0)
        completed_layout.addStretch()
        completed_layout.addWidget(self.sort_completed_list_btn)
        completed_layout.addWidget(separator_2)
        completed_layout.addWidget(self.open_directory_btn)
        completed_layout.addWidget(self.clear_all_btn)

        self.addWidget(downloading_widget)
        self.addWidget(completed_widget)

        self.connect_signals()

    def connect_signals(self):
        self.open_directory_btn.clicked.connect(self.on_open_directory)

        self.sort_downloading_list_btn.clicked.connect(self.on_show_downloading_list_sort_flyout)
        self.sort_completed_list_btn.clicked.connect(self.on_show_completed_list_sort_flyout)

    def on_show_downloading_list_sort_flyout(self):
        sort_by_key_dict = {
            self.tr("Creation Time"): "created_time",
            self.tr("Title"): "show_title",
            self.tr("File Size"): "file_size",
            self.tr("Download Progress"): "progress"
        }

        self._show_sort_flyout(
            sort_by_key_dict,
            signal_bus.download.sort_downloading_list.emit,
            self.download_interface.downloading_list_view.sort_by_key,
            self.sort_downloading_list_btn
        )

    def on_show_completed_list_sort_flyout(self):
        sort_by_key_dict = {
            self.tr("Completion Time"): "completed_time",
            self.tr("Title"): "show_title",
            self.tr("File Size"): "file_size"
        }

        self._show_sort_flyout(
            sort_by_key_dict,
            signal_bus.download.sort_completed_list.emit,
            self.download_interface.completed_list_view.sort_by_key,
            self.sort_completed_list_btn
        )

    def _show_sort_flyout(self, sort_by_key_dict, trigger_signal_func, sort_by_key, target):
        view = SortFlyoutWidget(self, sort_by_key_dict, trigger_signal_func, sort_by_key)

        flyout = Flyout.make(
            view = view,
            target = target,
            parent = self,
            aniType = FlyoutAnimationType.DROP_DOWN,
            isDeleteOnClose = False
        )

        view.closed.connect(flyout.fadeOut)

    def on_open_directory(self):    
        Directory.open_directory_in_explorer(config.get(config.download_path))