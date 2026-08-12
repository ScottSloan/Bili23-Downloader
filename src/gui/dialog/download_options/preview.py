from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtGui import QColor

from gui.component.widget.label import TagLabel, TipCaptionLabel

class DownloadPreviewBar(QWidget):
    """
    DownloadPreviewBar 以彩色标签的形式，实时预览当前将要下载的内容。
    """

    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.tip_label = TipCaptionLabel(self.tr("Will download:"), self)

        # 每一项对应一种可下载的内容，颜色用于区分不同类型
        tag_info = [
            ("video", self.tr("Video"), "#0078D4"),
            ("audio", self.tr("Audio"), "#13A10E"),
            ("danmaku", self.tr("Danmaku"), "#8764B8"),
            ("subtitle", self.tr("Subtitles"), "#DA6A1E"),
            ("cover", self.tr("Cover"), "#00B7C3"),
            ("chapter", self.tr("Chapters"), "#EF6950"),
            ("metadata", self.tr("Metadata"), "#C239B3")
        ]

        self.tag_map = {key: TagLabel(text, QColor(color), self) for key, text, color in tag_info}

        # 未选择任何内容时的占位标签，使用灰色以示区别
        self.empty_tag = TagLabel(self.tr("Nothing selected"), QColor("#8A8A8A"), self)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        main_layout.addWidget(self.tip_label)

        for tag in self.tag_map.values():
            main_layout.addWidget(tag)

        main_layout.addWidget(self.empty_tag)
        main_layout.addStretch()

    def update_preview(self, state: dict):
        for key, tag in self.tag_map.items():
            tag.setVisible(state.get(key, False))

        self.empty_tag.setVisible(not any(state.values()))
