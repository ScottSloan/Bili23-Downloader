from gui.component.dialog import DialogBase

from qfluentwidgets import SubtitleLabel, SpinBox

class StartingNumberDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize Starting Number"))
        self.starting_number_spin = SpinBox(self)
        self.starting_number_spin.setRange(1, 100_000_000)    # ichi oku

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.starting_number_spin)

        self.widget.setMaximumWidth(350)
