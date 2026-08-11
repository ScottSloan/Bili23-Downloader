from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import QTimer, Signal

from gui.component.setting import DanmakuSettingCard, SubtitleSettingCard, CoverSettingCard, ChapterSettingCard, MetadataSettingCard
from gui.component.widget.scroll import ScrollArea

class AdditionalSettingsPage(ScrollArea):
    # 下载内容发生变化时发出，用于刷新下载内容预览
    preview_changed = Signal()

    def __init__(self, parent_window, parent = None):
        super().__init__(parent = parent)

        self.parent_window = parent_window

        self.init_UI()

        self.connect_signals()

        QTimer.singleShot(0, self.expand_all)

    def init_UI(self):
        self.danmaku_card = DanmakuSettingCard(parent = self)
        self.subtitle_card = SubtitleSettingCard(parent = self)
        self.cover_card = CoverSettingCard(parent = self)
        self.chapter_card = ChapterSettingCard(parent = self)
        self.metadata_card = MetadataSettingCard(parent = self)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.danmaku_card)
        main_layout.addWidget(self.subtitle_card)
        main_layout.addWidget(self.cover_card)
        main_layout.addWidget(self.chapter_card)
        main_layout.addWidget(self.metadata_card)
        main_layout.addStretch()

        self.setScrollLayout(main_layout)

    def connect_signals(self):
        for card in (self.danmaku_card, self.subtitle_card, self.cover_card, self.chapter_card, self.metadata_card):
            card.download_switch.checkedChanged.connect(self.preview_changed)

        self.danmaku_card.custom_style_btn.clicked.connect(self.on_custom_danmaku_style)
        self.subtitle_card.language_btn.clicked.connect(self.on_custom_subtitles_language)
        self.subtitle_card.custom_style_btn.clicked.connect(self.on_custom_subtitles_style)

    def expand_all(self):
        self.danmaku_card.toggleExpand()
        self.subtitle_card.toggleExpand()
        self.cover_card.toggleExpand()
        self.chapter_card.toggleExpand()
        self.metadata_card.toggleExpand()

    def on_custom_danmaku_style(self):
        from ..setting.danmaku_style import DanmakuStyleDialog

        dialog = DanmakuStyleDialog(self.parent_window)
        dialog.exec()
    
    def on_custom_subtitles_language(self):
        from ..setting.subtitles_language import SubtitlesLanguageDialog

        dialog = SubtitlesLanguageDialog(self.parent_window)
        dialog.exec()

    def on_custom_subtitles_style(self):
        from ..setting.subtitles_style import SubtitlesStyleDialog

        dialog = SubtitlesStyleDialog(self.parent_window)
        dialog.exec()

    def has_file_to_download(self):
        return (
            self.danmaku_card.download_switch.isChecked() or
            self.subtitle_card.download_switch.isChecked() or
            self.cover_card.download_switch.isChecked() or
            self.metadata_card.download_switch.isChecked()
        )

    def get_download_preview(self):
        return {
            "danmaku": self.danmaku_card.download_switch.isChecked(),
            "subtitle": self.subtitle_card.download_switch.isChecked(),
            "cover": self.cover_card.download_switch.isChecked(),
            "chapter": self.chapter_card.download_switch.isChecked(),
            "metadata": self.metadata_card.download_switch.isChecked()
        }
