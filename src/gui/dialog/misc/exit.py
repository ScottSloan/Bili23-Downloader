from PySide6.QtWidgets import QHBoxLayout

from qfluentwidgets import SubtitleLabel, BodyLabel, RadioButton, CheckBox

from gui.component.dialog import DialogBase

from util.common.enum import WhenClose
from util.common.config import config

class ExitDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("提示"), self)

        tip_lab = BodyLabel(self.tr("When closing the window, you would like the program to:"), self)

        self.exit_radio = RadioButton(self.tr("Exit the program"), self)
        self.exit_radio.setChecked(True)
        self.minimize_radio = RadioButton(self.tr("Minimize to system tray"), self)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.exit_radio)
        radio_layout.addWidget(self.minimize_radio)
        radio_layout.addStretch()

        self.never_ask_check = CheckBox(self.tr("Don’t ask again"), self)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(tip_lab)
        self.viewLayout.addSpacing(5)
        self.viewLayout.addLayout(radio_layout)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.never_ask_check)

        self.widget.setMinimumWidth(350)

    def accept(self):
        if self.never_ask_check.isChecked():
            if self.exit_radio.isChecked():
                config.set(config.when_close_window, WhenClose.EXIT)

            elif self.minimize_radio.isChecked():
                config.set(config.when_close_window, WhenClose.MINIMIZE)

        return super().accept()
