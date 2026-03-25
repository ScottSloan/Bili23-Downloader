from qfluentwidgets import SubtitleLabel, LineEdit

from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory

class SearchDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Search"))

        self.keywords_box = LineEdit(self)
        self.keywords_box.setPlaceholderText(self.tr("Enter keywords to search"))
        self.keywords_box.setClearButtonEnabled(True)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.keywords_box)

        self.widget.setMinimumWidth(400)

    def validate(self):
        if self.keywords_box.text().strip() == "":
            self.keywords_box.setFocus()
            self.keywords_box.setError(True)

            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", self.tr("Please enter search keywords"))

            return False
        
        return True

    def accept(self):
        self.keywords = self.keywords_box.text().strip()

        return super().accept()