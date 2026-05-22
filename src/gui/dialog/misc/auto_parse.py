from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout

from qfluentwidgets import BodyLabel, SubtitleLabel, RadioButton, CheckBox

from gui.component.widget.spinbox import CompactSpinBox
from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory

class AutoParseDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Auto-parse Pagination"), self)

        tip_lab = BodyLabel(self.tr("Please select the parsing range and subsequent processing method"), self)

        self.auto_parse_all_radio = RadioButton(self.tr("Parse all pages"), self)
        self.auto_parse_all_radio.setChecked(True)
        self.parse_specified_radio = RadioButton(self.tr("Parse only pages X to Y"), self)

        from_lab = BodyLabel(self.tr("From"), self)
        to_lab = BodyLabel(self.tr("To"), self)

        self.start_spin = CompactSpinBox(parent = self)
        self.start_spin.setMinimum(1)
        
        self.end_spin = CompactSpinBox(parent = self)
        self.end_spin.setMinimum(1)

        self.auto_add_to_download_list_check = CheckBox(self.tr("Automatically add to download list after parsing each page"), self)

        warn_lab = BodyLabel(self.tr("Warning: Due to Bilibili's anti-abuse mechanism, parsing too many pages may cause failure and IP ban. Use with caution."), self)
        warn_lab.setWordWrap(True)

        range_layout = QHBoxLayout()
        range_layout.addWidget(from_lab)
        range_layout.addWidget(self.start_spin)
        range_layout.addWidget(to_lab)
        range_layout.addWidget(self.end_spin)
        range_layout.addStretch()

        radio_layout = QVBoxLayout()
        radio_layout.addWidget(self.auto_parse_all_radio)
        radio_layout.addWidget(self.parse_specified_radio)
        radio_layout.addLayout(range_layout)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(tip_lab)
        self.viewLayout.addSpacing(5)
        self.viewLayout.addLayout(radio_layout)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.auto_add_to_download_list_check)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(warn_lab)

        self.yesButton.setText(self.tr("Start Parsing"))

        self.widget.setFixedWidth(400)

    def accept(self):
        if self.parse_specified_radio.isChecked():
            self.start_page = self.start_spin.value()
            self.end_page = self.end_spin.value()

            if self.start_page > self.end_page:
                self.show_top_toast_message(ToastNotificationCategory.ERROR, self.tr("Invalid Range"), self.tr("The starting page cannot be greater than the ending page"))

        return super().accept()

