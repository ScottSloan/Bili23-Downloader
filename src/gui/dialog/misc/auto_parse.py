from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout

from qfluentwidgets import BodyLabel, SubtitleLabel, RadioButton, CheckBox

from gui.component.widget.spinbox import SpinBox
from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory, ParserType
from util.parse.auto_parse import AutoParsePayload

class AutoParseDialog(DialogBase):
    def __init__(self, url: str, total_pages: int, current_page: int, parent = None):
        super().__init__(parent)

        self.url = url
        self.total_pages = total_pages
        self.current_page = current_page

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Auto-parse Pagination"), self)

        tip_lab = BodyLabel(self.tr("Please select the parsing range and subsequent processing method"), self)

        self.auto_parse_all_radio = RadioButton(self.tr("Parse all pages"), self)
        self.auto_parse_all_radio.setChecked(True)
        self.parse_specified_radio = RadioButton(self.tr("Parse only pages X to Y"), self)

        self.start_lab = BodyLabel(self.tr("From"), self)
        self.end_lab = BodyLabel(self.tr("To"), self)

        self.start_spin = SpinBox(parent = self)
        self.start_spin.setMinimum(1)
        self.start_spin.setValue(self.current_page)
        self.start_spin.setEnabled(False)
        
        self.end_spin = SpinBox(parent = self)
        self.end_spin.setMinimum(1)
        self.end_spin.setValue(self.total_pages)
        self.end_spin.setEnabled(False)

        self.auto_add_to_download_list_check = CheckBox(self.tr("Automatically add to download list after parsing each page"), self)

        #self.follow_up_action_check = CheckBox(self.tr("解析分页都自动弹出此对话框"), self)

        warn_lab = BodyLabel(self.tr("Warning: Due to Bilibili's anti-abuse mechanism, parsing too many pages may cause failure and IP ban. Use with caution."), self)
        warn_lab.setWordWrap(True)

        range_layout = QHBoxLayout()
        range_layout.addWidget(self.start_lab)
        range_layout.addWidget(self.start_spin)
        range_layout.addWidget(self.end_lab)
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

        self.widget.setFixedWidth(450)

        self.parse_specified_radio.toggled.connect(self.enable_range_selection)

    def accept(self):
        if self.parse_specified_radio.isChecked():
            start_page = self.start_spin.value()
            end_page = self.end_spin.value()

            if start_page > end_page:
                self.show_top_toast_message(ToastNotificationCategory.ERROR, self.tr("Invalid Range"), self.tr("The starting page cannot be greater than the ending page"))

                return
            
        self.payload = self.get_data()

        return super().accept()

    def get_data(self):
        if self.auto_parse_all_radio.isChecked():
            start_page = self.current_page
            end_page = self.total_pages
        else:
            start_page = self.start_spin.value()
            end_page = self.end_spin.value()

        return AutoParsePayload(
            url = self.url,
            start_page = start_page,
            end_page = end_page,
            parser_type = ParserType.DYNAMIC,
        )
    
    def enable_range_selection(self, enabled: bool):
        self.start_lab.setEnabled(enabled)
        self.start_spin.setEnabled(enabled)
        self.end_lab.setEnabled(enabled)
        self.end_spin.setEnabled(enabled)

