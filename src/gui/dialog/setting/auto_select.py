from copy import deepcopy

from qfluentwidgets import SubtitleLabel, BodyLabel, ComboBox

from gui.component.dialog import DialogBase

from util.common.config import config, DefaultValue
from util.common.enum import ParseAutoCheckMode


class ParseAutoSelectDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()
        self.init_data()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Automatic Selection Rules"), self)

        intro_lab = BodyLabel(
            self.tr("Choose how parsed items are auto-checked after parsing. The current item is always selected; these rules only add extra selections for multi-item results."),
            self
        )
        intro_lab.setWordWrap(True)

        self.video_title_lab = BodyLabel(self.tr("User uploads (videos)"), self)
        self.video_desc_lab = BodyLabel(self.tr("Use this when a video contains multiple pages or a collection."), self)
        self.video_desc_lab.setWordWrap(True)
        self.video_mode_choice = ComboBox(self)
        self.video_mode_choice.setFixedWidth(300)
        self._setup_combo(self.video_mode_choice, [
            (self.tr("Keep the current page only"), ParseAutoCheckMode.CURRENT.value),
            (self.tr("Check all pages and collection items"), ParseAutoCheckMode.ALL.value),
        ])

        self.episode_title_lab = BodyLabel(self.tr("Series and courses"), self)
        self.episode_desc_lab = BodyLabel(self.tr("Use this for bangumi or course results. You can keep only the linked episode, or select every main episode in the result."), self)
        self.episode_desc_lab.setWordWrap(True)
        self.episode_mode_choice = ComboBox(self)
        self.episode_mode_choice.setFixedWidth(300)
        self._setup_combo(self.episode_mode_choice, [
            (self.tr("Keep the linked episode only"), ParseAutoCheckMode.CURRENT.value),
            (self.tr("Check all main episodes"), ParseAutoCheckMode.MAIN.value),
        ])

        self.list_title_lab = BodyLabel(self.tr("Other list-style results"), self)
        self.list_desc_lab = BodyLabel(self.tr("Use this for favorites, profile pages, collection lists, watch later, history, and similar results."), self)
        self.list_desc_lab.setWordWrap(True)
        self.list_mode_choice = ComboBox(self)
        self.list_mode_choice.setFixedWidth(300)
        self._setup_combo(self.list_mode_choice, [
            (self.tr("Keep the current item only"), ParseAutoCheckMode.CURRENT.value),
            (self.tr("Check all parsed items"), ParseAutoCheckMode.ALL.value),
        ])

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(intro_lab)
        self.viewLayout.addSpacing(12)
        self.viewLayout.addWidget(self.video_title_lab)
        self.viewLayout.addWidget(self.video_desc_lab)
        self.viewLayout.addWidget(self.video_mode_choice)
        self.viewLayout.addSpacing(12)
        self.viewLayout.addWidget(self.episode_title_lab)
        self.viewLayout.addWidget(self.episode_desc_lab)
        self.viewLayout.addWidget(self.episode_mode_choice)
        self.viewLayout.addSpacing(12)
        self.viewLayout.addWidget(self.list_title_lab)
        self.viewLayout.addWidget(self.list_desc_lab)
        self.viewLayout.addWidget(self.list_mode_choice)

        self.yesButton.setText(self.tr("Save"))
        self.widget.setMinimumWidth(560)

    def init_data(self):
        rules = deepcopy(config.get(config.parse_auto_check_rules))

        if config.get(config.auto_check_all) and rules == DefaultValue.parse_auto_check_rules:
            rules = {
                "video": ParseAutoCheckMode.ALL.value,
                "episode": ParseAutoCheckMode.ALL.value,
                "list": ParseAutoCheckMode.ALL.value,
            }

        self._set_combo_value(self.video_mode_choice, rules.get("video", ParseAutoCheckMode.CURRENT.value))
        self._set_combo_value(self.episode_mode_choice, rules.get("episode", ParseAutoCheckMode.CURRENT.value))
        self._set_combo_value(self.list_mode_choice, rules.get("list", ParseAutoCheckMode.CURRENT.value))

    def accept(self):
        rules = {
            "video": self.video_mode_choice.currentData(),
            "episode": self.episode_mode_choice.currentData(),
            "list": self.list_mode_choice.currentData(),
        }

        config.set(config.parse_auto_check_rules, rules)
        config.set(config.auto_check_all, False)

        return super().accept()

    def _setup_combo(self, combo: ComboBox, options: list[tuple[str, str]]):
        for text, value in options:
            combo.addItem(text, value)

    def _set_combo_value(self, combo: ComboBox, value: str):
        index = combo.findData(value)

        combo.setCurrentIndex(index if index >= 0 else 0)