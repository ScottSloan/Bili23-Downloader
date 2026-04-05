from qfluentwidgets import SubtitleLabel, BodyLabel

from gui.component.setting.widget import ParseActionWidget
from gui.component.widget import ColumnTreeWidget
from gui.component.dialog import DialogBase

from util.common import signal_bus, Translator
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

        self.history_list = ColumnTreeWidget(self)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(tip_lab)
        self.viewLayout.addWidget(self.history_list)

        self.widget.setMinimumSize(750, 475)

        self.hideCancelButton()

    def init_history_list(self):
        self.history_list.setColumnHeaders(
            [self.tr("No."), self.tr("Title"), self.tr("Type"), self.tr("Parse Time"), self.tr("Actions")],
            [60, 280, 120, 150, 50]
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

            widget = self.create_action_widget(index, url, history_id)

            self.history_list.setItemWidget(item, 4, widget)

    def on_parse(self, url: str):
        self.yesButton.click()

        signal_bus.parse.parse_url.emit(url)

    def on_delete(self, index: int, history_id: str):
        self.history_list.takeTopLevelItem(index - 1)

        history_manager.delete_history(history_id)

    def create_action_widget(self, index: int, url: str, history_id: str):
        action_widget = ParseActionWidget(self.history_list)
        action_widget.edit_btn.clicked.connect(lambda: self.on_parse(url))
        action_widget.delete_btn.clicked.connect(lambda: self.on_delete(index, history_id))

        return action_widget

