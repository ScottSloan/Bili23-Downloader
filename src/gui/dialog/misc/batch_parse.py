from PySide6.QtWidgets import QHBoxLayout

from qfluentwidgets import SubtitleLabel, BodyLabel, TextEdit, PushButton, CheckBox

from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory, ParserType
from util.common.data.auto_parse import AutoParsePayload
from util.common.config import config

class BatchParseDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Batch Parse"), parent = self)

        self.count_lab = BodyLabel(self.tr("Link Count: 0"), parent = self)
        self.clear_btn = PushButton(self.tr("Clear"), parent = self)

        self.lines_box = TextEdit(parent = self)
        self.lines_box.setPlaceholderText(self.tr("Paste video links here, one per line. Currently only av and BV links are supported."))

        self.auto_add_to_download_list_check = CheckBox(self.tr("Automatically add to download list after parsing each link"), self)
        self.auto_add_to_download_list_check.setChecked(config.get(config.auto_add_to_download_list))

        count_layout = QHBoxLayout()
        count_layout.addWidget(self.count_lab)
        count_layout.addStretch()
        count_layout.addWidget(self.clear_btn)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(count_layout)
        self.viewLayout.addWidget(self.lines_box)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.auto_add_to_download_list_check)

        self.widget.setMinimumWidth(550)

        self.yesButton.setText(self.tr("Start Parsing"))

        self.connect_signals()

    def connect_signals(self):
        self.clear_btn.clicked.connect(self.on_clear)
        self.lines_box.textChanged.connect(self.on_lines_changed)

    def on_lines_changed(self):
        lines = self.lines_box.toPlainText().splitlines()
        count = len([line for line in lines if line.strip() != ""])

        self.count_lab.setText(self.tr("Link Count: {count}").format(count = count))

    def on_clear(self):
        self.lines_box.clear()

    def accept(self):
        # 检查链接是否属于 av 号或 BV 号链接，并去除空行
        lines = self.lines_box.toPlainText().splitlines()
        self.url_list = [line.strip() for line in lines if line.strip() != ""]

        if not self.url_list:
            self.show_top_toast_message(
                ToastNotificationCategory.ERROR,
                self.tr("No Links Provided"),
                self.tr("Please paste video links in the text box.")
            )
            return False

        for line in self.url_list:
            if not "av" in line and not "BV" in line:
                self.show_top_toast_message(
                    ToastNotificationCategory.ERROR,
                    self.tr("Invalid Link Format"),
                    self.tr("Currently only av or BV links are supported.")
                )
                return False
            
        self.payload = self.get_data()

        self.save_config()

        return super().accept()
    
    def get_data(self):
        return AutoParsePayload(
            url = self.url_list[0],
            url_list = self.url_list,
            parser_type = ParserType.BATCH
        )
    
    def save_config(self):
        config.set(config.auto_add_to_download_list, self.auto_add_to_download_list_check.isChecked())