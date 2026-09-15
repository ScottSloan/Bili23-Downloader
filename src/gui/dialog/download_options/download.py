from PySide6.QtWidgets import QVBoxLayout

from qfluentwidgets import SwitchSettingCard

from gui.component.setting import DownloadPathSettingCard, NumberSettingCard, DownloadFormatCard
from gui.component.widget.scroll import ScrollArea
from .card import NamingConventionCard, MultiTypeNamingConventionCard

from util.common.icon import ExtendedFluentIcon
from util.common.config import config
from util.common.runtime import runtime

class DownloadSettingsPage(ScrollArea):
    def __init__(self, parent = None, type_ids = None):
        super().__init__(parent = parent)

        self.options_dialog = parent
        self.type_ids = type_ids or set()

        self.init_UI()

    def init_UI(self):
        self.download_path_card = DownloadPathSettingCard(self.options_dialog, save = False, parent = self)
        self.download_format_card = DownloadFormatCard(parent = self)
        self.naming_convention_card = self._create_naming_convention_card()
        self.show_dialog_card = SwitchSettingCard(ExtendedFluentIcon.OPTIONS, self.tr("Automatically show this dialog"), self.tr("Automatically show this dialog before downloading to customize settings"), config.show_download_options_dialog, self)
        self.numbering_settings_card = NumberSettingCard(self.options_dialog, self)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.download_path_card)
        main_layout.addWidget(self.download_format_card)
        main_layout.addWidget(self.naming_convention_card)
        main_layout.addWidget(self.show_dialog_card)
        main_layout.addWidget(self.numbering_settings_card)

        main_layout.addStretch()

        self.setScrollLayout(main_layout)

    def _create_naming_convention_card(self):
        # 绝大多数解析结果只有一种内容类型，保持原先的单行外观；
        # 混有多种类型时才展开成逐类型选择
        if len(self.type_ids) > 1:
            return MultiTypeNamingConventionCard(self.type_ids, self)

        return NamingConventionCard(next(iter(self.type_ids), None), self)

    def on_save(self):
        config.set(config.download_path, self.download_path_card.path)

        runtime.naming.target_rule_ids = self.naming_convention_card.rule_ids
