from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize

from qfluentwidgets import FluentWidget

class LogViewerDialog(FluentWidget):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setWindowTitle(self.tr("Log Viewer"))
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))

        self.setMinimumSize(800, 500)

        self.init_UI()

    def init_UI(self):
        pass

    def showEvent(self, event):
        parent_rect = self.parent().geometry()

        new_left = parent_rect.left() + (parent_rect.width() - self.size().width()) // 2
        new_top = parent_rect.top() + (parent_rect.height() - self.size().height()) // 2

        self.move(new_left, new_top)

        super().showEvent(event)