from PySide6.QtGui import QIntValidator

from qfluentwidgets import SubtitleLabel, LineEdit

from gui.component.dialog import DialogBase

class JumpToPageDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Jump To Page"), self)

        self.page_box = LineEdit(self)
        self.page_box.setPlaceholderText(self.tr("Enter page number"))
        self.page_box.setValidator(QIntValidator(1, 9999, self))

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.page_box)

        self.widget.setMinimumWidth(300)
