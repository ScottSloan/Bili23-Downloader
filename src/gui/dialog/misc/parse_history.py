from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtCore import Qt, QSize

from qfluentwidgets import SubtitleLabel, BodyLabel, CommandBar, Action, LineEdit, ComboBox

from gui.component.setting import ParseActionWidget
from gui.component.widget.tree_widget import ColumnTreeWidget
from gui.component.dialog import DialogBase

from util.common.icon import ExtendedFluentIcon
from util.common.signal_bus import signal_bus
from util.common.translator import Translator
from util.misc.history import history_manager
from util.format.time import Time

class ParseHistoryDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_history_list()

        self.connect_signals()

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

        self.search_box = LineEdit(self)
        self.search_box.setPlaceholderText(self.tr("Search title or URL..."))
        self.search_box.setClearButtonEnabled(True)

        self.type_choice = ComboBox(self)
        self.type_choice.setMinimumWidth(150)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.search_box, 1)
        filter_layout.addWidget(self.type_choice)

        self.history_list = ColumnTreeWidget(self)
        self.history_list.header().setStretchLastSection(False)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(top_layout)
        self.viewLayout.addLayout(filter_layout)
        self.viewLayout.addWidget(self.history_list)

        self.hideCancelButton()

        self.adjust_widget_size()

    def connect_signals(self):
        self.search_box.textChanged.connect(self.apply_filter)
        self.type_choice.currentIndexChanged.connect(self.apply_filter)

    def init_history_list(self):
        self.history_list.clear()

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

            # 筛选要用的原始字段挂在行上：URL 不在任何一列里，类型下拉框按键名而不是
            # 译文比对 —— 译文随界面语言变，键名不变
            item = self.history_list.addRow(
                str(index),
                title,
                type_str,
                Time.format_timestamp(created_time, "%Y-%m-%d %H:%M:%S"),
                userData = {
                    "title": title,
                    "url": url,
                    "type": type
                }
            )

            widget = self._create_action_widget(url, history_id)

            self.history_list.setItemWidget(item, 4, widget)

        self.history_list.header().setSectionResizeMode(1, self.history_list.header().ResizeMode.Stretch)

        self.update_type_choice()

    def update_type_choice(self):
        """
        按列表里现存的类型重建下拉框

        只列出真有记录的类型：全量十几种类型摆出来，大半选了是空列表，等于让用户白试。
        删除、清空之后也要重建，否则会留下已经没有记录的类型

        重建期间屏蔽信号，原先选中的类型若还在就保留选中，不在了回落到“全部类型”，
        最后统一走一次筛选
        """
        current_type = self.type_choice.currentData()

        existing_types = {entry["type"] for entry in self._iter_entries()}

        blocked = self.type_choice.blockSignals(True)

        try:
            self.type_choice.clear()
            self.type_choice.addItem(self.tr("All Types"), userData = None)

            # 按 EPISODE_TYPE 的定义顺序排列，不按出现顺序：后者每次打开都可能不同
            for key, label in Translator.EPISODE_TYPE().items():
                if key in existing_types:
                    self.type_choice.addItem(label, userData = key)

                    if key == current_type:
                        self.type_choice.setCurrentIndex(self.type_choice.count() - 1)

        finally:
            self.type_choice.blockSignals(blocked)

        self.apply_filter()

    def apply_filter(self, *args):
        """
        按关键词与类型隐藏不匹配的行

        用 setHidden() 而不是重建列表：每行都挂着操作按钮控件，重建要把它们全部重新创建一遍
        """
        keywords = self.search_box.text().strip().casefold()
        type_key = self.type_choice.currentData()

        for row in range(self.history_list.topLevelItemCount()):
            item = self.history_list.topLevelItem(row)
            entry = item.data(0, Qt.ItemDataRole.UserRole)

            item.setHidden(not self._matches(entry, keywords, type_key))

    def on_parse(self, url: str):
        self.yesButton.click()

        signal_bus.parse.parse_url.emit(url)

    def on_delete(self, history_id: str):
        history_manager.delete_history(history_id)

        # 从列表中查找 history_id 对应的项并删除
        for row in range(self.history_list.topLevelItemCount()):
            item = self.history_list.topLevelItem(row)
            widget = self.history_list.itemWidget(item, 4)

            if widget and widget.history_id == history_id:
                self.history_list.takeTopLevelItem(row)
                break

        self.update_type_choice()

    def on_clear_history(self):
        self.history_list.clear()

        history_manager.clear_history()

        self.update_type_choice()

    def _matches(self, entry: dict, keywords: str, type_key: str | None) -> bool:
        if type_key is not None and entry["type"] != type_key:
            return False

        if not keywords:
            return True

        fields = (entry["title"], entry["url"])

        return any(keywords in str(field).casefold() for field in fields if field)

    def _iter_entries(self):
        for row in range(self.history_list.topLevelItemCount()):
            yield self.history_list.topLevelItem(row).data(0, Qt.ItemDataRole.UserRole)

    def _create_action_widget(self, url: str, history_id: str):
        action_widget = ParseActionWidget(history_id, self.history_list)
        action_widget.edit_btn.clicked.connect(lambda: self.on_parse(url))
        action_widget.delete_btn.clicked.connect(lambda: self.on_delete(history_id))

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
