from PySide6.QtWidgets import QVBoxLayout

from qfluentwidgets import SwitchSettingCard

from gui.component.download_options.card import NamingConventionCard
from gui.component.setting.card import DownloadPathSettingCard
from gui.component.widget import ScrollArea

from util.common.icon import ExtendedFluentIcon
from util.common.config import config

class DownloadSettingsPage(ScrollArea):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.options_dialog = parent

        self.init_UI()

    def init_UI(self):
        self.download_path_card = DownloadPathSettingCard(self.options_dialog, save = False, parent = self)
        self.naming_convention_card = NamingConventionCard(self)
        self.show_dialog_card = SwitchSettingCard(ExtendedFluentIcon.OPTIONS, self.tr("Show download options dialog"), self.tr("Show a dialog before starting the download to customize settings for this task"), config.show_download_options_dialog, self)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.download_path_card)
        main_layout.addWidget(self.naming_convention_card)
        main_layout.addWidget(self.show_dialog_card)

        main_layout.addStretch()

        self.setScrollLayout(main_layout)

    def on_save(self):
        config.set(config.download_path, self.download_path_card.path)

        config.naming_rule_id = self.naming_convention_card.rule_choice.currentData()
