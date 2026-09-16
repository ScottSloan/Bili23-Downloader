from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QApplication
from PySide6.QtCore import Qt

from qfluentwidgets import (
    MessageBox, CommandBar, Action, FluentIcon, PrimaryPushButton, PushButton
)

from gui.component.widget.tree_widget import ColumnTreeWidget
from gui.component.dialog import Base, FluentWidget
from .edit_rule import EditRuleDialog

from util.common.data import reversed_convention_type_map
from util.common.naming_rules import load_rules, load_default_rules, save_rules, display_name
from util.common.enum import ToastNotificationCategory
from util.common.translator import Translator
from util.common.icon import ExtendedFluentIcon

from uuid import uuid4
from copy import deepcopy
import webbrowser

class RuleListDialog(Base, FluentWidget):
    """
    命名规则窗口

    名字里的 Dialog 是历史包袱：这里的界面文本以 RuleListDialog 为 Qt 翻译
    上下文存在两份 .ts 里，改类名要先手改 zh_CN / zh_TW 的 <name> 再跑
    scripts/translate.py，否则旧译文会全变孤儿。

    做成独立窗口而不是对话框，是因为可视化编辑器加上三行并排预览，对话框的
    高度根本不够摆。
    """

    def __init__(self, parent = None):
        Base.__init__(self)
        FluentWidget.__init__(self, parent_window = parent)

        self.setWindowTitle(self.tr("Naming Rules"))
        # 高度给 720 而不是 700：右栏是可视化编辑器 + 预览 + 变量表三块叠在一起，
        # 700 的时候各块的最小高度之和正好卡在临界，多一行红色错误提示就会挤出重叠
        self.setMinimumSize(1060, 720)

        self.rule_data_list = load_rules()
        self.current_index = None
        self.dirty = False

        # 程序性地改选中项时不要触发提交流程，否则校验失败会和「挪回原选中」
        # 互相递归
        self.suppress_selection = False

        self.init_UI()

        self.connect_signals()

        self.init_rule_list()

        self.resize_to_screen()

        self._init_common()

    def init_UI(self):
        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.command_bar.addAction(self._create_action(FluentIcon.ADD, self.tr("Add"), self.on_add_rule))
        self.command_bar.addAction(self._create_action(FluentIcon.COPY, self.tr("Duplicate"), self.on_duplicate_rule))
        self.command_bar.addAction(self._create_action(FluentIcon.DELETE, self.tr("Delete"), self.on_delete_rule))
        self.command_bar.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Reset to Default"), self.on_reset_to_default))
        self.command_bar.addAction(self._create_action(FluentIcon.HELP, self.tr("Help"), self.on_help))

        self.rule_list = ColumnTreeWidget(self)
        self.rule_list.header().setStretchLastSection(False)

        left_widget = QWidget(self)
        left_widget.setFixedWidth(300)

        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.command_bar)
        left_layout.addWidget(self.rule_list)

        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)

        self.editor = EditRuleDialog(self)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.addWidget(left_widget)
        body_layout.addWidget(separator)
        body_layout.addSpacing(8)
        body_layout.addWidget(self.editor, 1)

        self.save_btn = PrimaryPushButton(self.tr("Save"), self)
        self.close_btn = PushButton(self.tr("Close"), self)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.close_btn)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, self.titleBar.height(), 15, 15)
        main_layout.addLayout(body_layout, 1)
        main_layout.addSpacing(10)
        main_layout.addLayout(button_layout)

    def resize_to_screen(self):
        """
        按屏幕大小给一个宽裕些的初始尺寸

        可视化编辑器、三行并排预览、变量表叠在一栏里，最小尺寸只够勉强摆下，
        一打开就得手动拉大。屏幕摆不下时 resize 会被最小尺寸接住，不会把窗口
        撑到屏幕外面去
        """
        available = QApplication.primaryScreen().availableGeometry()

        self.resize(min(1280, available.width() - 80), min(880, available.height() - 80))

    def connect_signals(self):
        self.rule_list.currentItemChanged.connect(self.on_current_changed)

        self.editor.changed.connect(self.on_editor_changed)

        self.save_btn.clicked.connect(self.on_save)
        self.close_btn.clicked.connect(self.close)

    def init_rule_list(self):
        self.suppress_selection = True

        self.rule_list.clear()

        self.rule_list.setColumnHeaders(
            [
                self.tr("Rule Name"),
                self.tr("Rule Type"),
                self.tr("Default")
            ],
            [150, 100, 50]
        )

        for entry in self.rule_data_list:
            self._add_row(entry)

        self.rule_list.header().setSectionResizeMode(0, self.rule_list.header().ResizeMode.Stretch)

        self.suppress_selection = False

        self.current_index = None

        self._select_row(0 if self.rule_data_list else None)

    def _add_row(self, entry: dict):
        return self.rule_list.addRow(
            display_name(entry),
            self._get_type_str(entry.get("type")),
            "✓" if entry.get("default") else ""
        )

    def _refresh_row(self, index: int):
        entry = self.rule_data_list[index]
        row = self.rule_list.topLevelItem(index)

        row.setText(0, display_name(entry))
        row.setText(1, self._get_type_str(entry.get("type")))
        row.setText(2, "✓" if entry.get("default") else "")

    def _select_row(self, index):
        self.suppress_selection = True

        if index is None or not self.rule_data_list:
            self.rule_list.setCurrentItem(None)

            self.current_index = None
            self.editor.setEnabled(False)

        else:
            index = max(0, min(index, len(self.rule_data_list) - 1))

            self.rule_list.setCurrentItem(self.rule_list.topLevelItem(index))

            self.current_index = index
            self.editor.setEnabled(True)
            self.editor.load(self.rule_data_list[index])

        self.suppress_selection = False

    def on_current_changed(self, current, _previous):
        if self.suppress_selection:
            return

        if self.current_index is not None and not self._commit_editor():
            # 校验没过，把选中项挪回原处，不让用户带着一条无效规则走开
            self._select_row(self.current_index)

            return

        index = self.rule_list.indexOfTopLevelItem(current) if current else -1

        self._select_row(index if index >= 0 else None)

    def _commit_editor(self):
        """把编辑区的内容写回工作副本，校验不通过时提示并返回 False"""
        valid, widget, message = self.editor.validate()

        if not valid:
            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", message)

            widget.setError(True)
            widget.setFocus()

            return False

        entry = self.editor.dump()

        self.rule_data_list[self.current_index] = entry

        if entry.get("default"):
            self._set_default_rule(entry.get("id"), entry.get("type"))

        self._refresh_row(self.current_index)

        return True

    def on_editor_changed(self):
        self.dirty = True

    def on_add_rule(self):
        self._append_rule({
            "id": str(uuid4()),
            "name": self.tr("New rule"),
            "type": 11,
            "rule": "{leaf_title}",
            "default": False
        })

    def on_duplicate_rule(self):
        if self.current_index is None:
            return

        if not self._commit_editor():
            return

        entry = deepcopy(self.rule_data_list[self.current_index])

        entry["id"] = str(uuid4())
        entry["name"] = self.tr("{name} (copy)").format(name = display_name(entry))
        entry["default"] = False

        self._append_rule(entry)

    def _append_rule(self, entry: dict):
        if self.current_index is not None and not self._commit_editor():
            return

        self.rule_data_list.append(entry)

        self.suppress_selection = True
        self._add_row(entry)
        self.suppress_selection = False

        self.dirty = True

        self._select_row(len(self.rule_data_list) - 1)

    def on_delete_rule(self):
        if self.current_index is None:
            return

        entry = self.rule_data_list[self.current_index]

        # 不允许删除默认规则：删掉之后该类型就没有规则可用了
        if entry.get("default"):
            dialog = MessageBox(
                self.tr("Cannot delete default rule"),
                self.tr("Only non-default naming rules can be deleted."),
                self
            )
            dialog.hideCancelButton()
            dialog.exec()

            return

        index = self.current_index

        self.suppress_selection = True
        self.rule_list.takeTopLevelItem(index)
        self.suppress_selection = False

        self.rule_data_list.pop(index)

        self.current_index = None
        self.dirty = True

        self._select_row(min(index, len(self.rule_data_list) - 1) if self.rule_data_list else None)

    def on_reset_to_default(self):
        dialog = MessageBox(
            self.tr("Reset to Default"),
            self.tr("All custom naming rules will be discarded. Continue?"),
            self
        )

        if not dialog.exec():
            return

        self.rule_data_list = load_default_rules()
        self.current_index = None
        self.dirty = True

        self.init_rule_list()

    def on_help(self):
        webbrowser.open("https://bili23.scott-sloan.cn/doc/naming-rule.html")

    def on_save(self):
        if self.current_index is not None and not self._commit_editor():
            return

        save_rules(self.rule_data_list)

        self.dirty = False

        self.show_top_toast_message(
            ToastNotificationCategory.SUCCESS, "", self.tr("Naming rules saved")
        )

    def closeEvent(self, event):
        if self.dirty:
            dialog = MessageBox(
                self.tr("Discard changes?"),
                self.tr("The naming rules have been modified but not saved."),
                self
            )

            if not dialog.exec():
                event.ignore()

                return

        super().closeEvent(event)

    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)

        return action

    def _get_type_str(self, type_value: int):
        return Translator.CONVENTION_TYPE(reversed_convention_type_map.get(type_value))

    def _set_default_rule(self, rule_id: str, rule_type: int):
        for index, entry in enumerate(self.rule_data_list):
            if entry.get("type") == rule_type:
                entry["default"] = (entry.get("id") == rule_id)

                self._refresh_row(index)
