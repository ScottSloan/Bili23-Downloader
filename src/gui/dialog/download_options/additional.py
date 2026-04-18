from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import QTimer

from gui.component.setting import DanmakuSettingCard, SubtitleSettingCard, CoverSettingCard, MetadataSettingCard
from gui.component.widget import ScrollArea

class AdditionalSettingsPage(ScrollArea):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.init_UI()

        QTimer.singleShot(0, self.expand_all)

    def init_UI(self):
        self.danmaku_card = DanmakuSettingCard(full_mode = False, parent = self)
        self.subtitle_card = SubtitleSettingCard(full_mode = False, parent = self)
        self.cover_card = CoverSettingCard(parent = self)
        self.metadata_card = MetadataSettingCard(parent = self)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.danmaku_card)
        main_layout.addWidget(self.subtitle_card)
        main_layout.addWidget(self.cover_card)
        main_layout.addWidget(self.metadata_card)
        main_layout.addStretch()

        self.setScrollLayout(main_layout)

    def expand_all(self):
        self.danmaku_card.toggleExpand()
        self.subtitle_card.toggleExpand()
        self.cover_card.toggleExpand()
        self.metadata_card.toggleExpand()

    def has_file_to_download(self):
        return (
            self.danmaku_card.download_switch.isChecked() or
            self.subtitle_card.download_switch.isChecked() or
            self.cover_card.download_switch.isChecked() or
            self.metadata_card.download_switch.isChecked()
        )
