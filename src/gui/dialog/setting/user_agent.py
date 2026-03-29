from gui.component.dialog import DialogBase

from qfluentwidgets import LineEdit, SubtitleLabel

from util.common.enum import ToastNotificationCategory
from util.common import config

class UserAgentDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize User-Agent"), self)

        self.user_agent_box = LineEdit(self)
        self.user_agent_box.setPlaceholderText(self.tr("Please enter a User-Agent"))
        self.user_agent_box.setClearButtonEnabled(True)
        self.user_agent_box.setText(config.get(config.user_agent))

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.user_agent_box)

        self.widget.setMinimumWidth(500)

    def validate(self):
        is_valid = self.user_agent_box.text() != ""

        self.user_agent_box.setError(not is_valid)
        self.user_agent_box.setFocus()

        if not is_valid:
            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", self.tr("User-Agent cannot be empty"))

        return is_valid
    
    def accept(self):
        config.set(config.user_agent, self.user_agent_box.text())

        return super().accept()
