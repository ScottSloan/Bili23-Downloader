from qfluentwidgets import SubtitleLabel, LineEdit

from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory

class EditHostDialog(DialogBase):
    def __init__(self, cdn_node: str, parent = None):
        super().__init__(parent)

        self.cdn_node = cdn_node

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Edit CDN Node"), self)
        
        self.cdn_node_box = LineEdit(self)
        self.cdn_node_box.setPlaceholderText(self.tr("Please enter a CDN node"))
        self.cdn_node_box.setClearButtonEnabled(True)
        self.cdn_node_box.setText(self.cdn_node)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.cdn_node_box)

        self.widget.setMinimumWidth(400)

    def validate(self):
        is_valid = self.cdn_node_box.text() != ""

        self.cdn_node_box.setError(not is_valid)
        self.cdn_node_box.setFocus()

        if not is_valid:
            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", self.tr("CDN node cannot be empty"))

        return is_valid

    def accept(self):
        self.cdn_node = self.cdn_node_box.text()

        return super().accept()
