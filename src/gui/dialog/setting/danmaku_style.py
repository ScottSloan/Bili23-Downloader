from PySide6.QtWidgets import QVBoxLayout

from qfluentwidgets import SubtitleLabel, ScrollArea

from gui.component.setting import FontGroup, BorderGroup, AdvancedGroup, ResolutionGroup
from gui.component.dialog import DialogBase
from gui.component.widget import ScrollArea

from util.common import config

class ContentWidget(ScrollArea):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize Danmaku Style"), self)

        self.font_group = FontGroup(self)
        self.border_group = BorderGroup(self)
        self.advanced_group = AdvancedGroup(self)
        self.resolution_group = ResolutionGroup(self)

        self.expand_layout = QVBoxLayout()
        self.expand_layout.setContentsMargins(24, 0, 24, 0)
        self.expand_layout.addWidget(self.caption_lab)
        self.expand_layout.addSpacing(10)
        self.expand_layout.addWidget(self.font_group)
        self.expand_layout.addSpacing(25)
        self.expand_layout.addWidget(self.border_group)
        self.expand_layout.addSpacing(25)
        self.expand_layout.addWidget(self.advanced_group)
        self.expand_layout.addSpacing(25)
        self.expand_layout.addWidget(self.resolution_group)
        self.expand_layout.addSpacing(25)

        self.setScrollLayout(self.expand_layout)

class DanmakuStyleDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.content_widget = ContentWidget(self)

        self.viewLayout.addWidget(self.content_widget)
        self.viewLayout.setContentsMargins(0, 24, 0, 8)

        self.widget.setMinimumWidth(450)
        self.widget.setMaximumHeight(500)

    def init_data(self):
        data = config.get(config.danmaku_style).copy()

        self.content_widget.font_group.init_data(data.get("font"))
        self.content_widget.border_group.init_data(data.get("border"))
        self.content_widget.advanced_group.init_data(data.get("advanced"))
        self.content_widget.resolution_group.init_data(data.get("resolution"))

    def accept(self):
        data = {
            "font": self.content_widget.font_group.get_data(),
            "border": self.content_widget.border_group.get_data(),
            "advanced": self.content_widget.advanced_group.get_data(),
            "resolution": self.content_widget.resolution_group.get_data()
        }

        config.set(config.danmaku_style, data.copy())

        return super().accept()
