from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QApplication
from PySide6.QtCore import Qt, QTimer, Signal

from qfluentwidgets import (
    BodyLabel, StrongBodyLabel, CaptionLabel, LineEdit, CheckBox, MessageBox, HyperlinkButton,
    RoundMenu, Action, FluentIcon, TransparentTogglePushButton
)

from gui.component.widget.combobox import DictComboBox
from gui.component.widget.tree_widget import ColumnTreeWidget
from gui.component.dialog import Base
from gui.component.rule_builder import RuleBuilderWidget

from util.common.data import convention_type_map, VariableListFactory
from util.common.data.naming_convention import SampleShape, SUPPORTED_SHAPES
from util.common.enum import ToastNotificationCategory
from util.common.translator import Translator
from util.format.file_name import FileNameFormatter
from util.format.rule_template import compile_rule, RuleSyntaxError

from pathlib import Path
import re
import os

# 预览的防抖间隔。规则要经过解析、渲染、路径规范化三步，
# 每敲一个字符跑一遍既浪费也会让输入发涩
PREVIEW_DELAY = 250

class RulePreviewPanel(QWidget):
    """
    实时预览

    三种条目形态**并排**显示而不是切页：一条规则同时吃下单P与多P正是可选段
    存在的全部理由，并排才看得出哪一段在哪种形态下会收缩。

    渲染一律走 FileNameFormatter.format()，不另写一套 —— 否则预览与真正落盘
    的结果会分叉，非法字符净化、路径规范化的效果也看不见。
    """

    def __init__(self, parent = None):
        super().__init__(parent)

        self.factory = VariableListFactory()
        self.type_id = None

        self.rows = {}

        self.caption_lab = StrongBodyLabel(self.tr("Preview"), self)

        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(12)
        self.grid_layout.setVerticalSpacing(4)
        self.grid_layout.setColumnStretch(1, 1)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.caption_lab)
        main_layout.addLayout(self.grid_layout)

    def set_type(self, type_id):
        self.type_id = type_id

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)

            if item.widget():
                # 先断开父子关系再 deleteLater：DeferredDelete 要等下一轮事件循环，
                # 这中间旧标签会继续画在原位，和新的一行叠在一起
                item.widget().setParent(None)
                item.widget().deleteLater()

        self.rows = {}

        for row, shape in enumerate(SUPPORTED_SHAPES.get(type_id, (SampleShape.SINGLE,))):
            name_lab = CaptionLabel(self.shape_label(shape), self)
            path_lab = BodyLabel("", self)
            path_lab.setWordWrap(True)

            self.grid_layout.addWidget(name_lab, row, 0, Qt.AlignmentFlag.AlignTop)
            self.grid_layout.addWidget(path_lab, row, 1)

            self.rows[shape] = path_lab

    def shape_label(self, shape):
        # 必须是本类的方法：tr() 的查表上下文取实例所属的类名，
        # 写成模块级 lambda 的话，上下文会变成 lambda 的参数名
        match shape:
            case SampleShape.MULTI:
                return self.tr("Multi-part video")

            case SampleShape.COLLECTION:
                return self.tr("Collection")

            case _:
                return self.tr("Single video")

    def update_preview(self, rule: str):
        for shape, label in self.rows.items():
            label.setText(self.render(rule, shape) or "—")

    def render(self, rule: str, shape):
        if not rule:
            return None

        formatter = FileNameFormatter()
        formatter.set_variable_data(self.factory.build_variable_data(self.type_id, shape))
        formatter.set_rule(rule)

        result = formatter.format()

        if not result:
            return None

        path = Path(result)

        # 目录与文件名分开显示，用户一眼能看出规则在哪里分的层
        return str(path) if str(path.parent) == "." else "{folder}{sep}{name}".format(
            folder = path.parent, sep = os.sep, name = path.name
        )

class EditRuleDialog(Base, QWidget):
    """
    规则编辑面板

    名字里的 Dialog 是历史包袱：这里的界面文本以 EditRuleDialog 为 Qt 翻译
    上下文存在两份 .ts 里，改类名要先手改 zh_CN / zh_TW 的 <name> 再跑
    scripts/translate.py，否则 lupdate 会另建一个空上下文、旧译文全变孤儿，
    test_i18n_context.py 直接挂。留名换译文，划算。

    混入 Base 只为拿 show_top_toast_message：复制变量这种没有视觉结果的操作，
    不给反馈用户不知道到底复制上没有。
    """

    changed = Signal()

    def __init__(self, parent = None):
        Base.__init__(self)
        QWidget.__init__(self, parent)

        self.rule_data = {}
        self._loading = False

        self.init_UI()

        self.init_data()

        self.connect_signals()

    def init_UI(self):
        name_lab = BodyLabel(self.tr("Rule Name"), self)
        self.name_box = LineEdit(self)

        type_lab = BodyLabel(self.tr("Rule Type"), self)
        self.type_choice = DictComboBox(self)
        self.type_choice.setFixedWidth(250)

        header_layout = QGridLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(name_lab, 0, 0)
        header_layout.addWidget(type_lab, 0, 1)
        header_layout.addWidget(self.name_box, 1, 0)
        header_layout.addWidget(self.type_choice, 1, 1)

        self.builder = RuleBuilderWidget(self)

        self.advanced_btn = TransparentTogglePushButton(FluentIcon.CODE, self.tr("Advanced"), self)
        self.advanced_btn.setChecked(False)

        self.rule_box = LineEdit(self)
        self.rule_box.setPlaceholderText(self.tr("Naming Rule"))

        self.error_lab = CaptionLabel("", self)
        self.error_lab.setWordWrap(True)
        self.error_lab.setTextColor("#c42b1c", "#ff99a4")
        self.error_lab.hide()

        self.advanced_widget = QWidget(self)

        advanced_layout = QVBoxLayout(self.advanced_widget)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.addWidget(self.rule_box)
        advanced_layout.addWidget(self.error_lab)

        self.advanced_widget.hide()

        self.preview_panel = RulePreviewPanel(self)

        self.set_default_chk = CheckBox(self.tr("Set as default rule for this type"), self)

        self.guide_btn = HyperlinkButton(url = "", text = self.tr("Instructions"), parent = self)
        self.help_btn = HyperlinkButton(
            url = "https://bili23.scott-sloan.cn/doc/naming-rule.html",
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
        self.variable_list.header().setStretchLastSection(False)
        # 不给硬性最小高度，让它自己的 minimumSizeHint 说了算：整栏的最小高度之和
        # 一旦超过窗口能给的，Qt 会无视最小值继续压，多出来的那几像素就会变成重叠
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(8)
        main_layout.addWidget(self.builder, 3)
        main_layout.addSpacing(4)
        main_layout.addWidget(self.advanced_btn, 0, Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(self.advanced_widget)
        main_layout.addSpacing(4)
        main_layout.addWidget(self.preview_panel)
        main_layout.addSpacing(4)
        main_layout.addLayout(link_layout)
        main_layout.addWidget(self.variable_list, 2)

    def init_data(self):
        self.variable_list_factory = VariableListFactory()

        # 这张表是**参考表**，不是操作面板：插入变量的唯一入口是可视化编辑器里
        # 每一层的「＋」。以前最后一列的插入按钮插的是高级区的规则串，还会顺手把
        # 折叠着的高级区展开，用户在可视化界面里点它，完全看不出东西插到哪去了
        self.variable_list.setColumnHeaders(
            [
                self.tr("Variable"),
                self.tr("Description"),
                self.tr("Example")
            ],
            [150, 200, 150]
        )

        self.type_choice.init_dict_data(convention_type_map, Translator.CONVENTION_TYPE())

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(PREVIEW_DELAY)

    def connect_signals(self):
        self.type_choice.currentIndexChanged.connect(self.on_type_changed)

        self.advanced_btn.toggled.connect(self.advanced_widget.setVisible)

        self.guide_btn.clicked.connect(self.on_guide)

        self.builder.ruleChanged.connect(self.on_builder_changed)
        self.rule_box.textChanged.connect(self.on_rule_box_changed)

        self.name_box.textChanged.connect(self.on_edited)
        self.set_default_chk.toggled.connect(self.on_edited)

        self.preview_timer.timeout.connect(self.refresh_preview)

        self.variable_list.customContextMenuRequested.connect(self.on_context_menu)
        self.variable_list.itemDoubleClicked.connect(self.on_copy_variable)

    def load(self, rule_data: dict):
        """载入一条规则。载入期间的信号一律吞掉，免得被当成用户改动"""
        self._loading = True

        try:
            self.rule_data = rule_data

            self.name_box.setText(self.display_name())
            self.name_box.setError(False)

            self.type_choice.set_current_data(rule_data.get("type"))

            # 已经是默认规则的话，不能取消设置默认，也不能改规则类型
            is_default = bool(rule_data.get("default"))

            self.set_default_chk.setChecked(is_default)
            self.set_default_chk.setEnabled(not is_default)
            self.type_choice.setEnabled(not is_default)

            self.refresh_type_context()

            self.rule_box.setText(rule_data.get("rule", ""))
            self.builder.set_rule(rule_data.get("rule", ""))

        finally:
            self._loading = False

        self.refresh_preview()

    def display_name(self):
        from util.common.naming_rules import display_name

        return display_name(self.rule_data)

    def dump(self):
        """取出编辑结果，不改动传入的那份数据"""
        return {
            "id": self.rule_data.get("id"),
            "name": self.resolve_name(),
            "type": self.type_choice.currentData(),
            "rule": self.rule_box.text(),
            "default": self.set_default_chk.isChecked()
        }

    def resolve_name(self):
        # 用户没有改动名称时，内置规则要把翻译键原样存回去。
        # 存译名的话，界面语言一换，这条规则的名字就固定在旧语言上了
        name = self.name_box.text()

        return self.rule_data.get("name") if name == self.display_name() else name

    def refresh_type_context(self):
        type_id = self.type_choice.currentData()

        self.builder.set_type(type_id)
        self.preview_panel.set_type(type_id)

        self.init_variable_list(type_id)

    def init_variable_list(self, type_id):
        self.variable_list.clear()

        group = None

        # 推荐变量在前、其余在后，但清单本身是完整的：按类型裁剪只是界面上的
        # 「推荐」，键空间恒等于运行期，否则编辑器会拒绝一条运行期可用的规则
        for entry in self.variable_list_factory.build(type_id):
            if entry.get("group") != group:
                group = entry.get("group")

                self._add_group_item(group)

            description = Translator.VARIABLE_DESCRIPTION(entry["description"]) or entry["description"]

            self._add_item(entry["variable"], description, str(entry["example"]))

        self.variable_list.header().setSectionResizeMode(0, self.variable_list.header().ResizeMode.Stretch)

    def _add_group_item(self, group: str):
        """
        分组标题行

        三十来条变量平铺成一张表，用户分不出哪些是这个类型真正用得上的。
        标题行只是个视觉分隔，不可选中、不可复制
        """
        text = self.tr("Recommended for this type") if group == "PRIMARY" else self.tr("Other available variables")

        item = self.variable_list.addRow(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setFirstColumnSpanned(True)

    def on_type_changed(self):
        if self._loading:
            return

        self.refresh_type_context()
        self.on_edited()

    def on_builder_changed(self, rule: str):
        if self._loading:
            return

        # 可视化的改动写回高级区，用户能看见自己的操作对应什么语法
        self._loading = True
        self.rule_box.setText(rule)
        self._loading = False

        self.on_edited()

    def on_rule_box_changed(self):
        if self._loading:
            return

        self.builder.set_rule(self.rule_box.text())

        self.on_edited()

    def on_edited(self):
        if self._loading:
            return

        self.preview_timer.start()

        self.changed.emit()

    def refresh_preview(self):
        rule = self.rule_box.text()

        valid, message = self.validate_rule(rule)

        if valid:
            self.error_lab.hide()
            self.rule_box.setError(False)

            self.preview_panel.update_preview(rule)

        else:
            self.error_lab.setText(message)
            self.error_lab.show()
            self.rule_box.setError(True)

            self.preview_panel.update_preview("")

    def validate_rule(self, rule: str):
        """纯校验，无界面副作用。输入时走这个，保存时由窗口决定怎么提示"""
        if not rule:
            return False, self.tr("Naming rule cannot be empty")

        if rule.startswith(("/", ".")) or rule.endswith(("/", ".")):
            return False, self.tr("""Rule must not start or end with '/' or '.'""")

        try:
            template = compile_rule(rule, True)

        except RuleSyntaxError as error:
            return False, self.tr("Unmatched '<' or '>' at position {position}").format(position = error.position)

        # 定界符已被解析器吃掉，节点文本里再出现 <> 就确实是非法字符
        for literal in template.literal_texts():
            if re.search(r'[<>:\\"|?*\x00-\x1f]', literal):
                return False, self.tr("""Rule contains illegal characters: <>:\\"|?* or control characters""")

        unknown = template.field_names() - set(self.preview_panel.factory.build_variable_data(
            self.type_choice.currentData(), SampleShape.SINGLE
        ))

        if unknown:
            # 以前一律报「命名规则无效」，用户根本不知道错在哪个变量上
            return False, self.tr("Unknown variable: {name}").format(name = sorted(unknown)[0])

        if template.has_empty_optional_segment():
            return False, self.tr("An optional segment must contain at least one variable")

        if self.preview_panel.render(rule, SampleShape.SINGLE) is None:
            return False, self.tr("Invalid naming rule")

        return True, None

    def validate(self):
        """保存前的整体校验，返回 (是否通过, 出错的控件, 提示文案)"""
        if not self.name_box.text():
            return False, self.name_box, self.tr("Rule name cannot be empty")

        valid, message = self.validate_rule(self.rule_box.text())

        if not valid:
            # 语法问题只在高级区看得见，展开它，免得用户对着可视化区发愣
            self.advanced_btn.setChecked(True)

            return False, self.rule_box, message

        return True, None, None

    def on_guide(self):
        dialog = MessageBox(
            self.tr("Naming Rule Guide"),
            Translator.NAMING_RULE_GUIDE(),
            self.window()
        )
        dialog.hideCancelButton()

        dialog.exec()

    def on_context_menu(self, pos):
        if not self.get_current_variable():
            return

        menu = RoundMenu(parent = self)

        copy_action = Action(icon = FluentIcon.COPY, text = self.tr("Copy Variable"), parent = self)
        copy_action.triggered.connect(self.on_copy_variable)

        menu.addAction(copy_action)

        menu.exec(self.variable_list.viewport().mapToGlobal(pos))

    def on_copy_variable(self, *_):
        variable = self.get_current_variable()

        if not variable:
            return

        QApplication.clipboard().setText(variable)

        self.show_top_toast_message(ToastNotificationCategory.SUCCESS, "", self.tr("Copied: {variable}").format(variable = variable))

    def get_current_variable(self):
        item = self.variable_list.currentItem()

        # 分组标题行没有第二列，据此把它和真正的变量行区分开
        return item.text(0) if item and item.text(1) else None

    def _add_item(self, variable: str, description: str, example: str):
        self.variable_list.addRow(variable, description, example)
