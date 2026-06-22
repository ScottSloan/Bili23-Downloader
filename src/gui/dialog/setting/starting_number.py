from gui.component.dialog import DialogBase

from qfluentwidgets import SubtitleLabel, SpinBox

class StartingNumberDialog(DialogBase):
    def __init__(self, title: str, value: int, parent = None):
        super().__init__(parent)

        self.title = title
        self.value = value
        self.starting_number = None

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.title)

        self.starting_number_spin = SpinBox(self)
        self.starting_number_spin.setRange(1, 100_000_000)    # ichi oku
        self.starting_number_spin.setValue(self.value)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.starting_number_spin)

        self.widget.setMinimumWidth(350)

    def accept(self):
        self.starting_number = self.starting_number_spin.value()

        return super().accept()
