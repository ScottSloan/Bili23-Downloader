from qfluentwidgets import SubtitleLabel, BodyLabel, CheckBox

from gui.component.dialog import DialogBase

from util.common.enum import DuplicateDownloadResolution
from util.common.config import config

class DuplicateDownloadDialog(DialogBase):
    def __init__(self, episode_info: dict, result_info: dict, parent = None):
        super().__init__(parent)

        self.episode_info = episode_info
        self.result_info = result_info

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Duplicate Download Detected"), parent = self)

        desc_lab = BodyLabel(self.tr("A duplicate download task already exists in the download list. Do you want to continue downloading?"), parent = self)
        name_lab = BodyLabel(self.tr("Task Name: {task_title}").format(task_title = self.episode_info.get("title", "")), parent = self)
        name_lab.setWordWrap(True)

        self.never_ask_check = CheckBox(self.tr("Don't ask again"), parent = self)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addWidget(desc_lab)
        self.viewLayout.addWidget(name_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.never_ask_check)

        self.yesButton.setText(self.tr("Continue"))
        self.cancelButton.setText(self.tr("Skip"))

        self.widget.setMinimumWidth(350)

    def accept(self):
        self.result_info["skip"] = False
        self._check_never_ask()

        return super().accept()
    
    def reject(self):
        self.result_info["skip"] = True
        self._check_never_ask()

        return super().reject()
    
    def _check_never_ask(self):
        self.result_info["not_ask_again"] = self.never_ask_check.isChecked()

        if self.never_ask_check.isChecked():
            config.set(config.duplicate_download_resolution, DuplicateDownloadResolution.SKIP if self.result_info["skip"] else DuplicateDownloadResolution.CONTINUE)
