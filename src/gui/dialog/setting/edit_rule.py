from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QApplication
from PySide6.QtCore import Qt, QSize

from qfluentwidgets import SubtitleLabel, BodyLabel, LineEdit, CheckBox, PushButton, MessageBox, HyperlinkButton, RoundMenu, Action, FluentIcon

from gui.component.widget import ColumnTreeWidget, DictComboBox
from gui.component.setting import InsertActionWidget
from gui.component.dialog import DialogBase

from util.common.data import convention_type_map, VariableListFactory
from util.common.enum import ToastNotificationCategory
from util.format import FileNameFormatter
from util.common import Translator

from functools import wraps
from pathlib import Path
import re

def check_result(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        validate, result = func(self, *args, **kwargs)

        if not validate:
            self.show_top_toast_message(
                ToastNotificationCategory.ERROR, "", result
            )

            self.rule_box.setError(True)
            self.rule_box.setFocus()

        return validate, result
    return wrapper

class EditRuleDialog(DialogBase):
    def __init__(self, rule_data: dict, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.rule_data = rule_data.copy()

        self.init_data()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Edit Naming Rule"), self)

        name_lab = BodyLabel(self.tr("Rule Name"), self)
        self.name_box = LineEdit(self)

        type_lab = BodyLabel(self.tr("Rule Type"), self)
        self.type_choice = DictComboBox(self)
        self.type_choice.setFixedWidth(250)

        rule_lab = BodyLabel(self.tr("Naming Rule"), self)
        self.rule_box = LineEdit(self)

        self.preview_btn = PushButton(self.tr("Preview"), self)

        rule_layout = QHBoxLayout()
        rule_layout.setContentsMargins(0, 0, 0, 0)
        rule_layout.addWidget(self.rule_box)
        rule_layout.addWidget(self.preview_btn)

        self.set_default_chk = CheckBox(self.tr("Set as default rule for this type"), self)

        self.guide_btn = HyperlinkButton(url = "", text = self.tr("Guide"), parent = self)
        self.help_btn = HyperlinkButton(
            url = "https://bili23.scott-sloan.cn/doc/advanced-usage.html",
            text = self.tr("Open help page"),
            parent = self
        )

        link_layout = QHBoxLayout()
        link_layout.setContentsMargins(0, 0, 0, 0)
        link_layout.addWidget(self.set_default_chk)
        link_layout.addStretch()
        link_layout.addWidget(self.guide_btn)
        link_layout.addWidget(self.help_btn)

        self.variable_list = ColumnTreeWidget(self)
        self.variable_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.variable_list.setTooltipEnabled(True)

        name_layout = QGridLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.addWidget(name_lab, 0, 0)
        name_layout.addWidget(type_lab, 0, 1)
        name_layout.addWidget(self.name_box, 1, 0)
        name_layout.addWidget(self.type_choice, 1, 1)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addLayout(name_layout)
        self.viewLayout.addWidget(rule_lab)
        self.viewLayout.addLayout(rule_layout)
        self.viewLayout.addLayout(link_layout)
        self.viewLayout.addWidget(self.variable_list)

        self.adjust_widget_size()

        self.connect_signals()

        self.variable_list.header().setStretchLastSection(False)

    def connect_signals(self):
        self.type_choice.currentIndexChanged.connect(self.on_type_changed)
        self.preview_btn.clicked.connect(self.on_preview)
        self.guide_btn.clicked.connect(self.on_guide)

        self.variable_list.customContextMenuRequested.connect(self.on_context_menu)

    def init_data(self):
        self.file_name_formatter = FileNameFormatter()

        self.variable_list_factory = VariableListFactory()
        self.variable_list.setColumnHeaders(
            [
                self.tr("Variable"),
                self.tr("Description"),
                self.tr("Example"),
                self.tr("Actions")
            ],
            [
                150,
                200,
                150,
                60
            ]
        )

        self.name_box.setText(self.rule_data.get("name"))
        self.rule_box.setText(self.rule_data.get("rule"))
        self.type_choice.init_dict_data(convention_type_map, Translator.CONVENTION_TYPE(), self.rule_data.get("type"))

        if self.rule_data.get("default"):
            # 已经是默认规则，不能取消设置默认，也不能修改规则类型
            self.set_default_chk.setChecked(True)
            self.set_default_chk.setEnabled(False)

            self.type_choice.setEnabled(False)

        self.init_variable_list()

    def init_variable_list(self):
        self.variable_list.clear()

        variable_list = self.variable_list_factory.build(self.type_choice.currentData())

        for entry in variable_list:
            desc = entry.get("description")

            variable_description = Translator.VARIABLE_DESCRIPTION()

            if desc in variable_description.keys():
                desc_str = variable_description.get(desc)
            else:
                desc_str = desc

            self._add_item(entry["variable"], desc_str, entry["example"])
            
        self.file_name_formatter.set_variable_data(variable_list)

        self.variable_list.header().setSectionResizeMode(0, self.variable_list.header().ResizeMode.Stretch)

    def validate(self):
        if not self.name_box.text():
            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", self.tr("Rule name cannot be empty"))

            self.name_box.setError(True)
            self.name_box.setFocus()

            return False
        
        else:
            validate, _ = self.get_format_result()

            return validate

    def accept(self):
        self.rule_data = {
            "id": self.rule_data.get("id"),
            "name": self.name_box.text(),
            "type": self.type_choice.currentData(),
            "rule": self.rule_box.text(),
            "default": self.set_default_chk.isChecked()
        }

        return super().accept()

    def on_type_changed(self):
        self.init_variable_list()

    def on_preview(self):
        validate, result = self.get_format_result()

        if validate:
            dialog = MessageBox(
                self.tr("Preview"),
                self.tr("Folder: {folder}\nFile name: {filename}").format(
                    folder = result.parent,
                    filename = result.stem
                ),
                self
            )
            dialog.hideCancelButton()

            dialog.exec()

    def on_guide(self):
        dialog = MessageBox(
            self.tr("Naming Rule Guide"),
            Translator.NAMING_RULE_GUIDE(),
            self
        )
        dialog.hideCancelButton()

        dialog.exec()

    @check_result
    def get_format_result(self):
        # 对用户输入的规则进行校验
        rule = self.rule_box.text()

        if not rule:
            return False, self.tr("Naming rule cannot be empty")

        elif rule.startswith(("/", ".", "..")) or rule.endswith(("/", ".")):
            return False, self.tr("""Rule must not start or end with '/' or '.'""")
        
        self.file_name_formatter.set_rule(rule)

        result = self.file_name_formatter.format()

        if result:

            if re.search(r'[<>:\\"|?*\x00-\x1f]', result):
                return False, self.tr("""Rule contains illegal characters: <>:\\"|?* or control characters""")
            
            else:
                self.rule_box.setError(False)

                return True, Path(result)
        
        else:
            return False, self.tr("Invalid naming rule")

    def on_context_menu(self, pos):
        menu = RoundMenu(parent = self)

        copy_action = Action(icon = FluentIcon.COPY, text = self.tr("Copy Variable"), parent = self)
        copy_action.triggered.connect(self.on_copy_variable)

        insert_action = Action(icon = FluentIcon.ADD, text = self.tr("Insert Variable"), parent = self)
        insert_action.triggered.connect(self.on_insert_variable)

        menu.addAction(copy_action)
        menu.addAction(insert_action)

        menu.exec(self.variable_list.viewport().mapToGlobal(pos))

    def on_copy_variable(self):
        variable = self.get_current_variable()

        if variable:
            clipboard = QApplication.clipboard()
            clipboard.setText(variable)

    def on_insert_variable(self):
        variable = self.get_current_variable()

        self.rule_box.insert(variable)

    def get_current_variable(self):
        item = self.variable_list.currentItem()

        if item:
            variable = item.text(0)

            return variable
        
        else:
            return None

    def adjust_widget_size(self):
        parent_size: QSize = self.parent().size()

        width = parent_size.width() * 0.5
        height = parent_size.height() * 0.7

        self.widget.setMinimumWidth(max(675, width))
        self.widget.setMinimumHeight(max(550, height))

    def _add_item(self, variable: str, description: str, example: str):
        item = self.variable_list.addRow(variable, description, example)

        widget = InsertActionWidget(self.variable_list)
        widget.edit_btn.clicked.connect(lambda: self.rule_box.insert(variable))

        self.variable_list.setItemWidget(item, 3, widget)