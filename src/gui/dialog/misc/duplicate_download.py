from qfluentwidgets import SubtitleLabel, BodyLabel

from gui.component.dialog import DialogBase

class DuplicateDownloadDialog(DialogBase):
    def __init__(self, episode_info: dict, parent = None):
        super().__init__(parent)

        self.episode_info = episode_info

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Duplicate Download Detected"), parent = self)

        desc_lab = BodyLabel(self.tr("A duplicate download task already exists in the download list. Do you want to continue downloading?"), parent = self)
        name_lab = BodyLabel(self.tr("Task Name: {task_title}").format(task_title = self.episode_info.get("title", "")), parent = self)
        name_lab.setWordWrap(True)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addWidget(desc_lab)
        self.viewLayout.addWidget(name_lab)

        self.yesButton.setText(self.tr("Continue"))
        self.cancelButton.setText(self.tr("Skip"))

        self.widget.setMinimumWidth(350)
