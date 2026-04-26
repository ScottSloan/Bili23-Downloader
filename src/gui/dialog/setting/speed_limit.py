from qfluentwidgets import SubtitleLabel, DoubleSpinBox, SwitchButton, BodyLabel

from gui.component.dialog import DialogBase

from util.common import config

class SpeedLimitSettingDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.speed_limit_rate = config.get(config.speed_limit_rate)

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Speed Limit Settings"), self)

        enable_lab = BodyLabel(self.tr("Enable Speed Limit"), self)

        self.enable_switch = SwitchButton(self)
        self.enable_switch.setChecked(config.get(config.speed_limit_enabled))

        rate_lab = BodyLabel(self.tr("Speed limit (MB/s, 0 = unlimited)"), self)

        self.rate_spin = DoubleSpinBox(self)
        self.rate_spin.setRange(0.0, 1000.0)  # 0.1 MB/s to 1000MB/s
        self.rate_spin.setSingleStep(1.0)
        self.rate_spin.setDecimals(1)
        self.rate_spin.setValue(self.speed_limit_rate)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(enable_lab)
        self.viewLayout.addWidget(self.enable_switch)
        self.viewLayout.addSpacing(5)
        self.viewLayout.addWidget(rate_lab)
        self.viewLayout.addWidget(self.rate_spin)

        self.widget.setMinimumWidth(350)

    def accept(self):
        config.set(config.speed_limit_enabled, self.enable_switch.isChecked())
        config.set(config.speed_limit_rate, self.rate_spin.value())

        return super().accept()