from qfluentwidgets import SubtitleLabel, BodyLabel, ComboBox, RadioButton
from PySide6.QtWidgets import QVBoxLayout

from gui.component.dialog import DialogBase

from util.common.enum import AutoSelectMode
from util.common.config import config

class AutoSelectDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Auto-select Download Items Settings"), self)
        self.desc_lab = BodyLabel(self.tr("Set how items in the parsed list are automatically selected after parsing is complete."), self)

        self.manual_radio = RadioButton(self.tr("Let me choose manually"), self)
        self.select_all_radio = RadioButton(self.tr("Automatically select all items"), self)
        self.conditional_selection_radio = RadioButton(self.tr("Automatically select based on conditions"), self)
        self.manual_radio.setChecked(True)

        self.custom_hint_lab = BodyLabel(self.tr('The following rules can only be modified when "Automatically select based on conditions" is selected.'), self)

        self.user_uploads_lab = BodyLabel(self.tr("When parsing user-uploaded videos"), self)
        self.user_uploads_choice = ComboBox(self)
        self.user_uploads_choice.addItems([
            self.tr("Select only the single video corresponding to the link"),
            self.tr("Select all videos in the multi-part or collection")
        ])

        self.bangumi_lab = BodyLabel(self.tr("When parsing episodic or course-type videos"), self)
        self.bangumi_choice = ComboBox(self)
        self.bangumi_choice.addItems([
            self.tr("Select only the single episode corresponding to the link"),
            self.tr("Select all main episodes in the series")
        ])

        self.other_lab = BodyLabel(self.tr("When parsing other types of videos"), self)
        self.other_choice = ComboBox(self)
        self.other_choice.addItems([
            self.tr("Choose manually"),
            self.tr("Automatically select all items")
        ])

        self.user_uploads_choice.setFixedWidth(240)
        self.bangumi_choice.setFixedWidth(240)
        self.other_choice.setFixedWidth(240)

        self.custom_layout = QVBoxLayout()
        self.custom_layout.setSpacing(8)
        self.custom_layout.setContentsMargins(0, 0, 0, 0)

        self.custom_layout.addWidget(self.user_uploads_lab)
        self.custom_layout.addWidget(self.user_uploads_choice)
        self.custom_layout.addSpacing(4)
        self.custom_layout.addWidget(self.bangumi_lab)
        self.custom_layout.addWidget(self.bangumi_choice)
        self.custom_layout.addSpacing(4)
        self.custom_layout.addWidget(self.other_lab)
        self.custom_layout.addWidget(self.other_choice)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addWidget(self.desc_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.manual_radio)
        self.viewLayout.addWidget(self.select_all_radio)
        self.viewLayout.addWidget(self.conditional_selection_radio)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.custom_hint_lab)
        self.viewLayout.addLayout(self.custom_layout)

        self.widget.setMinimumWidth(400)

        self.conditional_selection_radio.toggled.connect(self.on_custom_options_enabled)
        
    def init_data(self):
        match config.get(config.auto_select_mode):
            case AutoSelectMode.MANUAL:
                self.manual_radio.setChecked(True)

            case AutoSelectMode.SELECT_ALL:
                self.select_all_radio.setChecked(True)

            case AutoSelectMode.CONDITIONAL:
                self.conditional_selection_radio.setChecked(True)

        self.on_custom_options_enabled()

    def accept(self):
        if self.manual_radio.isChecked():
            config.set(config.auto_select_mode, AutoSelectMode.MANUAL)

        elif self.select_all_radio.isChecked():
            config.set(config.auto_select_mode, AutoSelectMode.SELECT_ALL)

        elif self.conditional_selection_radio.isChecked():
            config.set(config.auto_select_mode, AutoSelectMode.CONDITIONAL)

        return super().accept()

    def on_custom_options_enabled(self):
        enabled = self.conditional_selection_radio.isChecked()

        for widget in (
            self.custom_hint_lab,
            self.user_uploads_lab,
            self.user_uploads_choice,
            self.bangumi_lab,
            self.bangumi_choice,
            self.other_lab,
            self.other_choice,
        ):
            widget.setEnabled(enabled)
