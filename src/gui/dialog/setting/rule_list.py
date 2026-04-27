from PySide6.QtCore import Qt, QSize

from qfluentwidgets import SubtitleLabel, MessageBox, CommandBar, Action, FluentIcon

from gui.component.setting import EditActionWidget
from gui.component.widget import ColumnTreeWidget
from gui.dialog.setting import EditRuleDialog
from gui.component.dialog import DialogBase

from util.common import config, Translator, ExtendedFluentIcon, DefaultValue
from util.common.data import reversed_convention_type_map

from uuid import uuid4
import webbrowser

class RuleListDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.main_window = parent

        self.rule_data_list = config.get(config.naming_rule_list).copy()

        self.init_rule_list()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Naming Rules"), self)

        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.command_bar.addAction(self._create_action(FluentIcon.ADD, self.tr("Add"), self.on_add_rule))
        self.command_bar.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Reset to Default"), self.on_reset_to_default))
        self.command_bar.addAction(self._create_action(FluentIcon.HELP, self.tr("Help"), self.on_help))

        self.rule_list = ColumnTreeWidget(self)
        self.rule_list.header().setStretchLastSection(False)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addWidget(self.command_bar)
        self.viewLayout.addWidget(self.rule_list)

        self.adjust_widget_size()

    def init_rule_list(self):
        self.rule_list.clear()

        self.rule_list.setColumnHeaders(
            [
                self.tr("Rule Name"),
                self.tr("Rule Type"),
                self.tr("Default"),
                self.tr("Actions")
            ],
            [
                275,
                200,
                75,
                75
            ]
        )

        for index, entry in enumerate(self.rule_data_list):
            name_key = entry.get("name")
            type_key = reversed_convention_type_map.get(entry.get("type"))

            default_rule_names = Translator.DEFAULT_RULE_NAMES()

            if name_key in default_rule_names:
                entry["name"] = Translator.DEFAULT_RULE_NAMES(name_key)

            self._add_row(
                entry.get("name"),
                Translator.CONVENTION_TYPE(type_key),
                index,
                userData = entry.copy()
            )

        self.rule_list.header().setSectionResizeMode(0, self.rule_list.header().ResizeMode.Stretch)

    def _create_action_widget(self, index: int):
        action_widget = EditActionWidget(self.rule_list)
        action_widget.edit_btn.clicked.connect(lambda: self.on_edit_rule(index))
        action_widget.delete_btn.clicked.connect(lambda: self.on_delete_rule(index))

        return action_widget

    def on_add_rule(self):
        entry = {
            "id": str(uuid4()),
            "name": "",
            "type": 11,
            "rule": "",
            "default": False
        }

        dialog = EditRuleDialog(entry, self.main_window)

        if dialog.exec():
            new_entry = dialog.rule_data

            self.rule_data_list.append(new_entry)

            index = len(self.rule_data_list) - 1

            self._add_row(
                new_entry.get("name"),
                self._get_type_str(new_entry.get("type")),
                index,
                userData = new_entry
            )

    def on_edit_rule(self, index: int):
        entry = self.rule_data_list[index]

        dialog = EditRuleDialog(entry, self.main_window)

        if dialog.exec():
            new_entry = dialog.rule_data

            row = self.rule_list.topLevelItem(index)

            row.setText(0, new_entry.get("name"))
            row.setText(1, self._get_type_str(new_entry.get("type")))
            row.setData(0, Qt.ItemDataRole.UserRole, new_entry)

            self._set_default_rule(new_entry.get("id"), new_entry.get("type"))

            self.rule_data_list[index] = new_entry

    def on_delete_rule(self, index: int):
        entry = self.rule_data_list[index]

        # 不允许删除默认规则
        if entry.get("default"):
            dialog = MessageBox(self.tr("Cannot delete default rule"), self.tr("Only non-default naming rules can be deleted."), self.main_window)
            dialog.hideCancelButton()
            dialog.exec()

            return
        
        self.rule_list.takeTopLevelItem(index)

        self.rule_data_list.pop(index)

    def on_reset_to_default(self):
        self.rule_data_list = DefaultValue.naming_rule_list.copy()

        self.init_rule_list()

    def on_help(self):
        webbrowser.open("https://bili23.scott-sloan.cn/doc/advanced-usage.html")

    def accept(self):
        config.set(config.naming_rule_list, self.rule_data_list)

        return super().accept()
    
    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)

        return action

    def _add_row(self, name: str, type: str, index: int, userData = None):
        row = self.rule_list.addRow(
            name,
            type,
            "✓" if userData.get("default") else "",
            "",
            userData = userData
        )

        widget = self._create_action_widget(index)

        self.rule_list.setItemWidget(row, 3, widget)

    def _get_type_str(self, type_value: int):
        return Translator.CONVENTION_TYPE(reversed_convention_type_map.get(type_value))

    def _set_default_rule(self, rule_id: str, rule_type: int):
        for entry in self.rule_data_list:
            if entry.get("type") == rule_type:
                entry["default"] = (entry.get("id") == rule_id)

        for i in range(self.rule_list.topLevelItemCount()):
            row = self.rule_list.topLevelItem(i)
            data = row.data(0, Qt.ItemDataRole.UserRole)

            if data.get("type") == rule_type:
                row.setText(2, "✓" if data.get("id") == rule_id else "")

    def adjust_widget_size(self):
        parent_size: QSize = self.parent().size()

        width = parent_size.width() * 0.55
        height = parent_size.height() * 0.65

        self.widget.setMinimumWidth(max(700, width))
        self.widget.setMinimumHeight(max(450, height))