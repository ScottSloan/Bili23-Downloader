from PySide6.QtWidgets import QHBoxLayout, QWidget

from qfluentwidgets import BodyLabel, IndeterminateProgressRing, PushButton

class ProgressTipWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.progress_ring = IndeterminateProgressRing(self, start = False)
        self.progress_ring.setFixedSize(28, 28)

        self.tip_lab = BodyLabel(parent = self)

        self.stop_btn = PushButton(self.tr("Stop"), self)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.progress_ring)
        layout.addSpacing(5)
        layout.addWidget(self.tip_lab)
        layout.addStretch()
        layout.addWidget(self.stop_btn)

        self.setLayout(layout)

        self.stop_btn.clicked.connect(lambda: self._trigger_stop_callback())

    def show_tip(self):
        self.progress_ring.start()
        self.tip_lab.setText("")

        self.show()

    def hide_tip(self):
        self.progress_ring.stop()
        self.tip_lab.setText("")

        self.hide()

    def update_text(self, text: str):
        self.tip_lab.setText(text)

    def _trigger_stop_callback(self):
        pass
