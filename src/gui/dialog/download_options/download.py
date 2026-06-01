from PySide6.QtWidgets import QVBoxLayout

from qfluentwidgets import SwitchSettingCard

from gui.component.setting import DownloadPathSettingCard, NumberSettingCard
from gui.component.widget import ScrollArea
from .card import NamingConventionCard

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
        self.show_dialog_card = SwitchSettingCard(ExtendedFluentIcon.OPTIONS, self.tr("Automatically show this dialog"), self.tr("Automatically show this dialog before downloading to customize settings"), config.show_download_options_dialog, self)
        self.numbering_settings_card = NumberSettingCard(self.options_dialog, self)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.download_path_card)
        main_layout.addWidget(self.naming_convention_card)
        main_layout.addWidget(self.show_dialog_card)
        main_layout.addWidget(self.numbering_settings_card)

        main_layout.addStretch()

        self.setScrollLayout(main_layout)

        self.numbering_settings_card.starting_number_btn.clicked.connect(self.on_custom_starting_number)

    def on_save(self):
        config.set(config.download_path, self.download_path_card.path)

        config.target_naming_rule_id = self.naming_convention_card.rule_choice.currentData()

    def on_custom_starting_number(self):
        from gui.dialog.setting.starting_number import StartingNumberDialog

        dialog = StartingNumberDialog(self.options_dialog)

        if dialog.exec():
            self.numbering_settings_card.set_current_starting_number(dialog.starting_number)