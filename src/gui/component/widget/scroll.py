from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from qfluentwidgets import ScrollArea as _ScrollArea

from util.common import StyleSheet

class ScrollArea(_ScrollArea):
    def __init__(self, parent = None):
        super().__init__(parent)

    def setScrollLayout(self, layout, resizable = True):
        scroll_widget = QWidget()
        scroll_widget.setObjectName("scrollWidget")
        scroll_widget.setLayout(layout)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidget(scroll_widget)
        self.setWidgetResizable(resizable)

        StyleSheet.SCROLLABLE_DIALOG.apply(self)
        