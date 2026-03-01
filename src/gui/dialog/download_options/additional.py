from PySide6.QtWidgets import QVBoxLayout

from gui.component.setting.card import DanmakuSettingCard, SubtitleSettingCard, CoverSettingCard, MetadataSettingCard
from gui.component.widget import ScrollArea

class AdditionalSettingsPage(ScrollArea):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.init_UI()

    def init_UI(self):
        danmaku_card = DanmakuSettingCard(full_mode = False, parent = self)
        subtitle_card = SubtitleSettingCard(full_mode = False, parent = self)
        cover_card = CoverSettingCard(parent = self)
        metadata_card = MetadataSettingCard(parent = self)

        main_layout = QVBoxLayout()
        main_layout.addWidget(danmaku_card)
        main_layout.addWidget(subtitle_card)
        main_layout.addWidget(cover_card)
        main_layout.addWidget(metadata_card)
        main_layout.addStretch()

        self.setScrollLayout(main_layout)
