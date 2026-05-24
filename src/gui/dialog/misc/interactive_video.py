from PySide6.QtWidgets import QVBoxLayout

from qfluentwidgets import SubtitleLabel, BodyLabel, RadioButton, CheckBox

from gui.component.dialog import DialogBase

from util.common.data.auto_parse import AutoParsePayload
from util.common.enum import ParserType

class InteractiveVideoDialog(DialogBase):
    def __init__(self, data: dict, parent = None):
        super().__init__(parent)

        self.data = data

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Interactive Video"), self)

        tip_lab = BodyLabel(self.tr("Detection of interactive video, please select an operation"), self)

        self.auto_radio = RadioButton(self.tr("Automatically parse all nodes"), self)
        self.auto_radio.setChecked(True)
        #self.manual_radio = RadioButton(self.tr("Manually select nodes"), self)

        radio_layout = QVBoxLayout()
        radio_layout.addWidget(self.auto_radio)
        #radio_layout.addWidget(self.manual_radio)
        radio_layout.addStretch()

        self.never_ask_check = CheckBox(self.tr("Don't ask again"), self)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(tip_lab)
        self.viewLayout.addSpacing(5)
        self.viewLayout.addLayout(radio_layout)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.never_ask_check)

        self.widget.setMinimumWidth(350)

    def accept(self):
        self.payload = self.get_data()
        
        return super().accept()

    def get_data(self):
        return AutoParsePayload(
            data = self.data,
            auto_parse = self.auto_radio.isChecked(),
            parser_type = ParserType.INTERACTIVE_VIDEO
        )