from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from qfluentwidgets import FluentWidget, ComboBox, LineEdit, PushButton

from gui.component.log_list.list_view import LogListView

from util.common.io.directory import Directory
from util.common.config import appdata_path

from pathlib import Path
import re

LOG_PATTERN = re.compile(
    r'\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] - '
    r'(?P<name>.+?) - '
    r'(?P<level>\w+): '
    r'(?P<message>.*)'
)

class LogViewerDialog(FluentWidget):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setWindowTitle(self.tr("Log Viewer"))
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))
        self.setMinimumSize(800, 500)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.category_choice = ComboBox(self)
        self.category_choice.setMinimumWidth(150)
        self.category_choice.addItems([
            self.tr("All"),
            self.tr("Info"),
            self.tr("Warning"),
            self.tr("Error"),
        ])

        self.search_box = LineEdit(self)
        self.search_box.setPlaceholderText(self.tr("Search logs..."))

        self.clear_btn = PushButton(self.tr("Clear Logs"), self)
        self.open_dir_btn = PushButton(self.tr("Open Logs Directory"), self)

        self.log_list = LogListView(self)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.category_choice)
        top_layout.addWidget(self.search_box)
        top_layout.addWidget(self.clear_btn)
        top_layout.addWidget(self.open_dir_btn)
        top_layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 38, 15, 15)
        main_layout.addLayout(top_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.log_list)

        self.connect_signals()

    def showEvent(self, event):
        parent_rect = self.parent().geometry()

        new_left = parent_rect.left() + (parent_rect.width() - self.size().width()) // 2
        new_top = parent_rect.top() + (parent_rect.height() - self.size().height()) // 2

        self.move(new_left, new_top)

        super().showEvent(event)

    def connect_signals(self):
        self.clear_btn.clicked.connect(self.clear_logs)
        self.open_dir_btn.clicked.connect(self.open_logs_directory)

    def init_data(self):
        self.log_path = Path(appdata_path) / "Bili23 Downloader" / "logs" / "app.log"

        log_records = self.parse_log_file(self.log_path)

        self.log_list._model.appendRows(log_records)

    def parse_log_file(self, filepath: Path) -> list[dict]:
        records = []

        with open(filepath, "r", encoding = "utf-8") as f:
            for line in f:
                line = line.rstrip('\n')
                match = LOG_PATTERN.match(line)

                if match:
                    record = match.groupdict()
                    records.append(record)
                else:
                    if records:
                        records[-1]['message'] += '\n' + line

        return records

    def clear_logs(self):
        # 清空日志文件内容
        self.log_path.write_text("", encoding = "utf-8")
        self.log_list._model.clearData()

    def open_logs_directory(self):
        Directory.open_directory_in_explorer(self.log_path.parent)

