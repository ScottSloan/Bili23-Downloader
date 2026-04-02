from qfluentwidgets import SubtitleLabel, DoubleSpinBox

from gui.component.dialog import DialogBase

from util.common import config

class SpeedLimitSettingDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.speed_limit_rate = config.get(config.speed_limit_rate)

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize Speed Limit Rate"), self)

        self.rate_spin = DoubleSpinBox(self)
        self.rate_spin.setRange(0.1, 1000.0)  # 0.1 MB/s to 1000MB/s
        self.rate_spin.setSingleStep(1.0)
        self.rate_spin.setDecimals(1)
        self.rate_spin.setSuffix(" MB/s")
        self.rate_spin.setValue(self.speed_limit_rate)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addWidget(self.rate_spin)

        self.widget.setMinimumWidth(300)

    def accept(self):
        self.speed_limit_rate = self.rate_spin.value()

        return super().accept()