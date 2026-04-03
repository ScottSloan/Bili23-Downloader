from qfluentwidgets import SubtitleLabel, BodyLabel

from gui.component.widget import ColumnTreeWidget
from gui.component.dialog import DialogBase

class ParseHistoryDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_history_list()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Parsing History"), self)

        self.history_list = ColumnTreeWidget(self)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addWidget(self.history_list)

        self.widget.setMinimumSize(700, 450)

        self.hideCancelButton()

    def init_history_list(self):
        self.history_list.setColumnHeaders(
            [self.tr("No."), self.tr("Title"), self.tr("URL"), self.tr("Parser Type"), self.tr("Parsed At")],
            [50, 150, 200, 100, 100]
        )
