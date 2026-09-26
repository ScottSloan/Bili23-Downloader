from qfluentwidgets import SubtitleLabel, BodyLabel, CheckBox

from gui.component.dialog import DialogBase

from util.common.config import config

class DownloadAsSingleVideoDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Download as Single Video"), self)

        desc_lab = BodyLabel(self.tr("This will save the file directly using the video's title as its name, without applying your configured file naming rules."), self)
        desc_lab.setWordWrap(True)

        self.never_show_check = CheckBox(self.tr("Don't show this again"), self)

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addWidget(desc_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.never_show_check)

        self.widget.setMinimumWidth(350)

        self.hideCancelButton()

    def accept(self):
        config.set(config.show_download_as_single_video_dialog, not self.never_show_check.isChecked())

        return super().accept()
