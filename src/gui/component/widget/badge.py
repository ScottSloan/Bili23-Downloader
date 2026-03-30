from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout

from qfluentwidgets import InfoBadge



class Tag(QLabel):
    def __init__(self, text: str, parent = None):
        super().__init__(text, parent)
        self.setStyleSheet("background-color: #E0E0E0; border-radius: 5px; padding: 2px 5px;")
        self.setFixedHeight(20)

