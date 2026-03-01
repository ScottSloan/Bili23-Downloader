from qfluentwidgets import SubtitleLabel, RadioButton

from gui.component.widget import CheckListView
from gui.component.dialog import DialogBase

from util.common.data import subtitles_language_list
from util.common.config import config

class SubtitlesLanguageDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_language_list()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize Subtitle Languages"), self)

        self.download_all_btn = RadioButton(self)
        self.download_all_btn.setText(self.tr("Download all available subtitles"))

        self.download_specified_btn = RadioButton(self)
        self.download_specified_btn.setText(self.tr("Download only selected subtitles"))

        self.language_list = CheckListView(self)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.download_all_btn)
        self.viewLayout.addWidget(self.download_specified_btn)
        self.viewLayout.addWidget(self.language_list)

        self.widget.setMinimumWidth(650)

    def init_language_list(self):
        self.language_list.setColumnHeaders([self.tr("No."), self.tr("Language"), self.tr("Code")], [80, 250, 150])

        subtitle_language: dict = config.get(config.subtitle_language).copy()

        if subtitle_language.get("download_specified"):
            self.download_specified_btn.setChecked(True)
        else:
            self.download_all_btn.setChecked(True)

        for index, entry in enumerate(subtitles_language_list):
            lan = entry["lan"]

            self.language_list.appendCheckableRow(str(index + 1), entry["doc_zh"], lan, data = lan, checked = lan in subtitle_language.get("specified_language"))

    def accept(self):
        subtitle_language = {
            "download_specified": self.download_specified_btn.isChecked(),
            "specified_language": self.language_list.getCheckedItemsData()
        }

        config.set(config.subtitle_language, subtitle_language)

        return super().accept()
        
