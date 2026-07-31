from qfluentwidgets import SubtitleLabel

from gui.component.widget import CheckListView
from gui.component.dialog import DialogBase

class MultiPartListsDialog(DialogBase):
    def __init__(self, item: dict, parent = None):
        super().__init__(parent)

        self.item = item

        self.init_UI()

        self.init_multi_part_list()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Multi-part video list"), self)

        self.part_list = CheckListView(self)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.part_list)

        self.widget.setMinimumWidth(600)

        self.yesButton.setText(self.tr("Download Selected Items"))

    def init_multi_part_list(self):
        self.part_list.setColumnHeaders([self.tr("No."), self.tr("Title"), self.tr("Duration")], [90, 350, 100])

        # for index, entry in enumerate(self.item.get("part_list", [])):
        #     self.part_list.appendCheckableRow(str(index + 1), entry["title"], entry["duration"], data = entry)
    