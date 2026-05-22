from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout

from qfluentwidgets import BodyLabel, SubtitleLabel, RadioButton, CheckBox

from gui.component.widget.spinbox import CompactSpinBox
from gui.component.dialog import DialogBase

class AutoParseDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("自动解析分页"), self)

        tip_lab = BodyLabel(self.tr("请选择解析范围和后续处理方式"), self)

        self.auto_parse_all_radio = RadioButton(self.tr("解析全部分页"), self)
        self.auto_parse_all_radio.setChecked(True)
        self.parse_specified_radio = RadioButton(self.tr("仅解析第 X 页到第 Y 页"), self)

        from_lab = BodyLabel(self.tr("从"), self)
        to_lab = BodyLabel(self.tr("到"), self)

        self.from_spin = CompactSpinBox(parent = self)
        self.to_spin = CompactSpinBox(parent = self)

        self.auto_add_to_download_list_check = CheckBox(self.tr("解析每页后自动加入下载列表"), self)

        warn_lab = BodyLabel(self.tr("警告：由于B站风控机制，当分页过多时会导致解析失败，并封禁IP，请谨慎使用"), self)
        warn_lab.setWordWrap(True)

        range_layout = QHBoxLayout()
        range_layout.addWidget(from_lab)
        range_layout.addWidget(self.from_spin)
        range_layout.addWidget(to_lab)
        range_layout.addWidget(self.to_spin)
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

        self.yesButton.setText("开始解析")

        self.widget.setFixedWidth(400)
