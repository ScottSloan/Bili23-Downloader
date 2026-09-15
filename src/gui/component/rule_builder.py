from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics

from qfluentwidgets import (
    FlyoutViewBase, Flyout, FlyoutAnimationType, FluentIcon, ComboBox, LineEdit,
    BodyLabel, StrongBodyLabel, CaptionLabel, PushButton, TransparentPushButton,
    RoundMenu, Action
)

from .widget.button import TransparentToolButton

from util.common.data.naming_convention import VariableListFactory
from util.common.translator import Translator
from util.common.enum import VariableType

from util.format.rule_model import Fragment, Level, RuleModel, parse_rule, UnsupportedRule
from util.format.rule_format import presets_for, preview_spec

def variable_label(entry: dict) -> str:
    """
    变量在界面上的短标签

    直接复用变量表「含义」列的译文（「视频发布时间」「分P序号」这类），
    它们本来就是四到六个字，正好当芯片文字，不必再单独维护一套标签
    """
    if not entry:
        return ""

    return Translator.VARIABLE_DESCRIPTION(entry.get("description")) or entry.get("name", "")

class FragmentEditView(FlyoutViewBase):
    """点击芯片后弹出的片段编辑面板"""

    changed = Signal()
    removed = Signal()

    def __init__(self, fragment: Fragment, variables: dict, parent = None):
        super().__init__(parent)

        self.fragment = fragment
        self.variables = variables

        self.init_UI()

        self.init_data()

        self.connect_signals()

    def init_UI(self):
        self.variable_choice = ComboBox(self)
        self.variable_choice.setMinimumWidth(220)

        self.format_choice = ComboBox(self)
        self.format_box = LineEdit(self)
        self.format_box.setPlaceholderText(self.tr("Custom format"))

        self.prefix_box = LineEdit(self)
        self.suffix_box = LineEdit(self)
        self.text_box = LineEdit(self)

        self.tip_label = CaptionLabel(self.tr("The prefix and suffix disappear together with the variable"), self)
        self.tip_label.setWordWrap(True)

        self.remove_btn = PushButton(FluentIcon.DELETE, self.tr("Remove"), self)

        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(8)

        self.variable_row = self._add_row(self.tr("Variable"), self.variable_choice)
        self.format_row = self._add_row(self.tr("Format"), self.format_choice)
        self.custom_format_row = self._add_row("", self.format_box)
        self.prefix_row = self._add_row(self.tr("Prefix"), self.prefix_box)
        self.suffix_row = self._add_row(self.tr("Suffix"), self.suffix_box)
        self.text_row = self._add_row(self.tr("Text"), self.text_box)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.addLayout(self.form_layout)
        main_layout.addWidget(self.tip_label)
        main_layout.addSpacing(6)
        main_layout.addWidget(self.remove_btn)

    def _add_row(self, label: str, widget: QWidget):
        label_widget = BodyLabel(label, self)

        self.form_layout.addRow(label_widget, widget)

        return (label_widget, widget)

    def init_data(self):
        if self.fragment.is_text:
            self.text_box.setText(self.fragment.text)
        else:
            self._init_variable_choice()
            self._init_format_choice()

            self.prefix_box.setText(self.fragment.prefix)
            self.suffix_box.setText(self.fragment.suffix)

        self._update_visibility()

    def _init_variable_choice(self):
        for entry in self.variables.values():
            self.variable_choice.addItem(variable_label(entry), userData = entry["name"])

        index = self.variable_choice.findData(self.fragment.variable)

        if index != -1:
            self.variable_choice.setCurrentIndex(index)

    def _init_format_choice(self):
        self.format_choice.clear()

        presets = presets_for(self._variable_type())

        for spec in presets:
            example = preview_spec(self._variable_type(), spec)

            self.format_choice.addItem(
                "{spec} （{example}）".format(spec = spec or self.tr("As is"), example = example) if example else spec,
                userData = spec
            )

        self.format_choice.addItem(self.tr("Custom…"), userData = None)

        index = self.format_choice.findData(self.fragment.spec)

        if index == -1:
            # 规则里写的格式不在预设中（多半是手写或从高级模式带过来的），
            # 落到自定义，免得静默把它改成某个预设
            self.format_choice.setCurrentIndex(self.format_choice.count() - 1)
            self.format_box.setText(self.fragment.spec)
        else:
            self.format_choice.setCurrentIndex(index)

    def _variable_type(self):
        entry = self.variables.get(self.fragment.variable)

        return entry.get("type", VariableType.TEXT) if entry else VariableType.TEXT

    def _update_visibility(self):
        is_text = self.fragment.is_text
        has_format = bool(presets_for(self._variable_type()))
        is_custom = self.format_choice.currentData() is None

        self._set_row_visible(self.text_row, is_text)
        self._set_row_visible(self.variable_row, not is_text)
        self._set_row_visible(self.format_row, not is_text and has_format)
        self._set_row_visible(self.custom_format_row, not is_text and has_format and is_custom)
        self._set_row_visible(self.prefix_row, not is_text)
        self._set_row_visible(self.suffix_row, not is_text)

        self.tip_label.setVisible(not is_text)

        self.adjustSize()

    @staticmethod
    def _set_row_visible(row, visible: bool):
        for widget in row:
            widget.setVisible(visible)

    def connect_signals(self):
        self.variable_choice.currentIndexChanged.connect(self.on_variable_changed)
        self.format_choice.currentIndexChanged.connect(self.on_format_changed)

        self.format_box.textChanged.connect(self.on_edited)
        self.prefix_box.textChanged.connect(self.on_edited)
        self.suffix_box.textChanged.connect(self.on_edited)
        self.text_box.textChanged.connect(self.on_edited)

        self.remove_btn.clicked.connect(self.removed)

    def on_variable_changed(self):
        self.fragment.variable = self.variable_choice.currentData()

        # 换了变量，原来的格式多半不再适用（日期格式套到数字上会直接报错）
        self.fragment.spec = ""

        self._init_format_choice()
        self._update_visibility()

        self.changed.emit()

    def on_format_changed(self):
        self._update_visibility()
        self.on_edited()

    def on_edited(self):
        if self.fragment.is_text:
            self.fragment.text = self.text_box.text()
        else:
            spec = self.format_choice.currentData()

            self.fragment.spec = self.format_box.text() if spec is None else spec
            self.fragment.prefix = self.prefix_box.text()
            self.fragment.suffix = self.suffix_box.text()

        self.changed.emit()

class FragmentChip(TransparentPushButton):
    """规则里的一个片段，点击弹出编辑面板"""

    changed = Signal()
    removed = Signal(object)

    def __init__(self, fragment: Fragment, variables: dict, parent = None):
        super().__init__(parent)

        self.fragment = fragment
        self.variables = variables

        self.setFixedHeight(30)

        self.refresh()

        self.clicked.connect(self.on_edit)

    # 芯片是一排横向排布的按钮，标签过长会把整行挤散，超出就省略
    MAX_LABEL_WIDTH = 200

    def refresh(self):
        text = self.display_text()

        self.setText(QFontMetrics(self.font()).elidedText(text, Qt.TextElideMode.ElideRight, self.MAX_LABEL_WIDTH))

        entry = self.variables.get(self.fragment.variable)

        self.setToolTip("\n".join([text, entry["variable"]]) if entry else text)

    def display_text(self):
        if self.fragment.is_text:
            return self.fragment.text or self.tr("(empty)")

        label = variable_label(self.variables.get(self.fragment.variable)) or self.fragment.variable

        return "{prefix}〈{label}〉{suffix}".format(
            prefix = self.fragment.prefix, label = label, suffix = self.fragment.suffix
        )

    def on_edit(self):
        view = FragmentEditView(self.fragment, self.variables, self)

        view.changed.connect(self.on_changed)
        view.removed.connect(lambda: self.removed.emit(self.fragment))

        Flyout.make(view, self, self.window(), FlyoutAnimationType.DROP_DOWN)

    def on_changed(self):
        self.refresh()
        self.changed.emit()

class RuleLevelRow(QWidget):
    """一个目录层级，或者（作为最后一行）文件名"""

    changed = Signal()
    removeRequested = Signal(object)
    moveRequested = Signal(object, int)

    def __init__(self, level: Level, variables: dict, movable: bool = True, parent = None):
        super().__init__(parent)

        self.level = level
        self.variables = variables
        self.movable = movable

        self.init_UI()

        self.refresh()

    def init_UI(self):
        self.chip_layout = QHBoxLayout()
        self.chip_layout.setContentsMargins(0, 0, 0, 0)
        self.chip_layout.setSpacing(4)

        self.add_btn = TransparentToolButton(FluentIcon.ADD, self)
        self.add_btn.setToolTip(self.tr("Add fragment"))
        self.add_btn.clicked.connect(self.on_add)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)
        main_layout.addLayout(self.chip_layout)
        main_layout.addWidget(self.add_btn)
        main_layout.addStretch()

        if self.movable:
            self.up_btn = self._tool_button(FluentIcon.UP, self.tr("Move up"), lambda: self.moveRequested.emit(self.level, -1))
            self.down_btn = self._tool_button(FluentIcon.DOWN, self.tr("Move down"), lambda: self.moveRequested.emit(self.level, 1))
            self.delete_btn = self._tool_button(FluentIcon.DELETE, self.tr("Delete level"), lambda: self.removeRequested.emit(self.level))

            main_layout.addWidget(self.up_btn)
            main_layout.addWidget(self.down_btn)
            main_layout.addWidget(self.delete_btn)

    def _tool_button(self, icon, tooltip: str, slot):
        button = TransparentToolButton(icon, self)
        button.setToolTip(tooltip)
        button.clicked.connect(slot)

        return button

    def refresh(self):
        while self.chip_layout.count():
            item = self.chip_layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        for fragment in self.level.fragments:
            chip = FragmentChip(fragment, self.variables, self)
            chip.changed.connect(self.changed)
            chip.removed.connect(self.on_remove_fragment)

            self.chip_layout.addWidget(chip)

        if not self.level.fragments:
            self.chip_layout.addWidget(CaptionLabel(self.tr("Empty, will be skipped"), self))

    def on_add(self):
        menu = RoundMenu(parent = self)

        variable_action = Action(icon = FluentIcon.TAG, text = self.tr("Insert variable"), parent = self)
        variable_action.triggered.connect(lambda: self.add_fragment(Fragment(variable = self.default_variable())))

        text_action = Action(icon = FluentIcon.FONT, text = self.tr("Insert text"), parent = self)
        text_action.triggered.connect(lambda: self.add_fragment(Fragment(text = "")))

        menu.addAction(variable_action)
        menu.addAction(text_action)

        menu.exec(self.add_btn.mapToGlobal(self.add_btn.rect().bottomLeft()))

    def default_variable(self):
        return next(iter(self.variables), None)

    def add_fragment(self, fragment: Fragment):
        self.level.fragments.append(fragment)

        self.refresh()
        self.changed.emit()

    def on_remove_fragment(self, fragment: Fragment):
        if fragment in self.level.fragments:
            self.level.fragments.remove(fragment)

            self.refresh()
            self.changed.emit()

class RuleBuilderWidget(QWidget):
    """
    命名规则的可视化编辑器

    规则在这里被看成「若干目录层级 + 一个文件名」，每层由若干片段组成。
    片段的前后缀会随变量一起消失，序列化出去就是 <P{p:02d}-> 这样的可选段 ——
    换句话说 `<>` 只是存储形式，用户在这里根本不必看见它。

    目录层为空时会被路径规范化自动丢掉，因此层级本身不需要任何「可选」开关。
    """

    ruleChanged = Signal(str)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.factory = VariableListFactory()

        self.variables = {}
        self.model = RuleModel(levels = [Level()])
        self.rows = []

        self.init_UI()

    def init_UI(self):
        self.directory_label = StrongBodyLabel(self.tr("Directory structure"), self)

        self.level_layout = QVBoxLayout()
        self.level_layout.setContentsMargins(0, 0, 0, 0)
        self.level_layout.setSpacing(2)

        self.add_level_btn = TransparentPushButton(FluentIcon.ADD, self.tr("Add level"), self)
        self.add_level_btn.clicked.connect(self.on_add_level)

        add_layout = QHBoxLayout()
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.addWidget(self.add_level_btn)
        add_layout.addStretch()

        self.file_name_label = StrongBodyLabel(self.tr("File name"), self)

        self.file_name_layout = QVBoxLayout()
        self.file_name_layout.setContentsMargins(0, 0, 0, 0)

        self.unsupported_label = BodyLabel(self)
        self.unsupported_label.setWordWrap(True)
        self.unsupported_label.hide()

        self.body = QFrame(self)

        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.addWidget(self.directory_label)
        body_layout.addLayout(self.level_layout)
        body_layout.addLayout(add_layout)
        body_layout.addSpacing(6)
        body_layout.addWidget(self.file_name_label)
        body_layout.addLayout(self.file_name_layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.unsupported_label)
        main_layout.addWidget(self.body)

    def set_type(self, type_id):
        """切换规则类型，变量清单随之变化"""
        self.variables = {entry["name"]: entry for entry in self.factory.build(type_id)}

        self.rebuild()

    def set_rule(self, rule: str) -> bool:
        """
        载入一条规则，返回是否能用可视化表示

        表达不了时禁用可视化区并给出原因，由高级模式接手 —— 绝不静默丢掉
        解析不了的部分，那会让用户以为自己的规则被改坏了
        """
        model = parse_rule(rule) if rule else RuleModel(levels = [Level()])

        if isinstance(model, UnsupportedRule):
            self.body.setEnabled(False)

            self.unsupported_label.setText(
                self.tr("This rule cannot be shown in the visual editor ({reason}). Edit it in the advanced section below.").format(
                    reason = model.reason
                )
            )
            self.unsupported_label.show()

            return False

        self.body.setEnabled(True)
        self.unsupported_label.hide()

        self.model = model

        self.rebuild()

        return True

    def rule(self) -> str:
        return self.model.to_rule()

    def rebuild(self):
        self._clear_layout(self.level_layout)
        self._clear_layout(self.file_name_layout)

        self.rows = []

        if not self.model.levels:
            self.model.levels.append(Level())

        *directories, file_name = self.model.levels

        for index, level in enumerate(directories):
            self.level_layout.addLayout(self._level_row(level, index + 1, movable = True))

        self.file_name_layout.addWidget(self._build_row(file_name, movable = False))

    def _level_row(self, level: Level, number: int, movable: bool):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(BodyLabel(self.tr("Level {number}").format(number = number), self))
        layout.addSpacing(8)
        layout.addWidget(self._build_row(level, movable), 1)

        return layout

    def _build_row(self, level: Level, movable: bool):
        row = RuleLevelRow(level, self.variables, movable, self)

        row.changed.connect(self.on_changed)
        row.removeRequested.connect(self.on_remove_level)
        row.moveRequested.connect(self.on_move_level)

        self.rows.append(row)

        return row

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

            elif item.layout():
                RuleBuilderWidget._clear_layout(item.layout())

    def on_add_level(self):
        # 新层级插在文件名之前 —— 最后一层永远是文件名
        self.model.levels.insert(max(len(self.model.levels) - 1, 0), Level())

        self.rebuild()
        self.on_changed()

    def on_remove_level(self, level: Level):
        if level in self.model.levels and len(self.model.levels) > 1:
            self.model.levels.remove(level)

            self.rebuild()
            self.on_changed()

    def on_move_level(self, level: Level, offset: int):
        index = self.model.levels.index(level)
        target = index + offset

        # 不能越过文件名那一层
        if 0 <= target < len(self.model.levels) - 1:
            self.model.levels[index], self.model.levels[target] = self.model.levels[target], self.model.levels[index]

            self.rebuild()
            self.on_changed()

    def on_changed(self):
        self.ruleChanged.emit(self.rule())
