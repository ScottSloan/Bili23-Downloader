from PySide6.QtWidgets import QStackedWidget, QWidget, QHBoxLayout

from qfluentwidgets import PrimaryPushButton, PushButton, FluentIcon

from util.common.icon import ExtendedFluentIcon
from util.common.config import config
from util.common.io import Directory

class TopStackedWidget(QStackedWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setFixedHeight(32)

        self.init_UI()

    def init_UI(self):
        downloading_widget = QWidget()
        downloading_widget.setContentsMargins(0, 0, 0, 0)

        self.start_all_btn = PrimaryPushButton(FluentIcon.PLAY, self.tr("Start All"), self)
        self.pause_all_btn = PushButton(FluentIcon.PAUSE, self.tr("Pause All"), self)
        self.delete_all_btn = PushButton(FluentIcon.DELETE, self.tr("Delete All"), self)

        downloading_layout = QHBoxLayout(downloading_widget)
        downloading_layout.setContentsMargins(0, 0, 0, 0)
        downloading_layout.addStretch()
        downloading_layout.addWidget(self.start_all_btn)
        downloading_layout.addWidget(self.pause_all_btn)
        downloading_layout.addWidget(self.delete_all_btn)

        completed_widget = QWidget()
        completed_widget.setContentsMargins(0, 0, 0, 0)

        self.open_directory_btn = PushButton(FluentIcon.FOLDER, self.tr("Open Directory"), self)
        self.clear_all_btn = PushButton(ExtendedFluentIcon.CLEAR, self.tr("Clear All"))

        completed_layout = QHBoxLayout(completed_widget)
        completed_layout.setContentsMargins(0, 0, 0, 0)
        completed_layout.addStretch()
        completed_layout.addWidget(self.open_directory_btn)
        completed_layout.addWidget(self.clear_all_btn)

        self.addWidget(downloading_widget)
        self.addWidget(completed_widget)

        self.open_directory_btn.clicked.connect(self.on_open_directory)

    def on_open_directory(self):    
        Directory.open_directory_in_explorer(config.get(config.download_path))
