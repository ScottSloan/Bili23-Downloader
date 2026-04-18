from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtCore import Qt, QSize

from qfluentwidgets import SubtitleLabel, BodyLabel, CommandBar, Action

from gui.component.setting import ParseActionWidget
from gui.component.widget import ColumnTreeWidget
from gui.component.dialog import DialogBase

from util.common import signal_bus, Translator, ExtendedFluentIcon
from util.misc import history_manager
from util.format import Time

class ParseHistoryDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_history_list()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Parse History"), self)

        tip_lab = BodyLabel(self.tr("Only the latest 100 records are kept."), self)

        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.command_bar.addAction(self._create_action(ExtendedFluentIcon.CLEAR, self.tr("Clear History"), self.on_clear_history))

        top_layout = QHBoxLayout()
        top_layout.addWidget(tip_lab)
        top_layout.addStretch()
        top_layout.addWidget(self.command_bar)

        self.history_list = ColumnTreeWidget(self)
        self.history_list.header().setStretchLastSection(False)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(top_layout)
        self.viewLayout.addWidget(self.history_list)

        self.hideCancelButton()

        self.adjust_widget_size()

    def init_history_list(self):
        self.history_list.setColumnHeaders(
            [
                self.tr("No."),
                self.tr("Title"),
                self.tr("Type"),
                self.tr("Parse Time"),
                self.tr("Actions")
            ],
            [
                60,
                280,
                120,
                150,
                75
            ]
        )

        for index, (history_id, title, url, type, created_time) in enumerate(history_manager.get_history(), start=1):
            type_str = Translator.EPISODE_TYPE(type)

            title = type_str if not title else title

            item = self.history_list.addRow(
                str(index),
                title,
                type_str,
                Time.format_timestamp(created_time, "%Y-%m-%d %H:%M:%S"),
            )

            widget = self._create_action_widget(index, url, history_id)

            self.history_list.setItemWidget(item, 4, widget)

        self.history_list.header().setSectionResizeMode(1, self.history_list.header().ResizeMode.Stretch)

    def on_parse(self, url: str):
        self.yesButton.click()

        signal_bus.parse.parse_url.emit(url)

    def on_delete(self, index: int, history_id: str):
        self.history_list.takeTopLevelItem(index - 1)

        history_manager.delete_history(history_id)

    def on_clear_history(self):
        self.history_list.clear()

        history_manager.clear_history()

    def _create_action_widget(self, index: int, url: str, history_id: str):
        action_widget = ParseActionWidget(self.history_list)
        action_widget.edit_btn.clicked.connect(lambda: self.on_parse(url))
        action_widget.delete_btn.clicked.connect(lambda: self.on_delete(index, history_id))

        return action_widget
    
    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)

        return action

    def adjust_widget_size(self):
        parent_size: QSize = self.parent().size()

        width = parent_size.width() * 0.6
        height = parent_size.height() * 0.65

        self.widget.setMinimumWidth(max(750, width))
        self.widget.setMinimumHeight(max(475, height))