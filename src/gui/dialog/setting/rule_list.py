from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from qfluentwidgets import (
    MessageBox, CommandBar, Action, FluentIcon, LineEdit, PrimaryPushButton, PushButton, RoundMenu
)

from gui.component.widget.separator import Separator
from gui.component.widget.tree_widget import DragColumnTreeWidget
from gui.component.dialog import Base, FluentWidget
from .edit_rule import EditRuleDialog

from util.common.data import reversed_convention_type_map
from util.common.naming_rules import load_rules, load_default_rules, save_rules, display_name
from util.common.enum import ConventionType, ToastNotificationCategory
from util.common.translator import Translator
from util.common.icon import ExtendedFluentIcon

from uuid import uuid4
from copy import deepcopy

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

        # 工具栏只放「针对当前选中项」的动作。左栏固定 300px，实测五个带文字的
        # 动作摆不下 —— 后两个会被收进「…」，用户根本看不见。整表级的「重置为
        # 默认值」与「帮助」因此挪到了右键菜单和编辑区
        self.add_action = self._create_action(FluentIcon.ADD, self.tr("Add"), self.on_add_rule)
        self.duplicate_action = self._create_action(FluentIcon.COPY, self.tr("Duplicate"), self.on_duplicate_rule)
        self.delete_action = self._create_action(FluentIcon.DELETE, self.tr("Delete"), self.on_delete_rule)

        self.command_bar.addAction(self.add_action)
        self.command_bar.addAction(self.duplicate_action)
        self.command_bar.addAction(self.delete_action)

        self.search_box = LineEdit(self)
        self.search_box.setPlaceholderText(self.tr("Search rules..."))
        self.search_box.setClearButtonEnabled(True)

        self.rule_list = DragColumnTreeWidget(self)
        self.rule_list.header().setStretchLastSection(False)
        self.rule_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        left_widget = QWidget(self)
        left_widget.setFixedWidth(300)

        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.command_bar)
        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self.rule_list)

        separator = Separator(self)

        self.editor = EditRuleDialog(self)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.addWidget(left_widget)
        body_layout.addWidget(separator)
        body_layout.addSpacing(8)
        body_layout.addWidget(self.editor, 1)

        self.save_btn = PrimaryPushButton(self.tr("Save"), self)
        # 「关闭」实际行为是取消：有未保存改动会先问是否丢弃。按钮上写「取消」，
        # 才不会让人以为改动已经生效
        self.close_btn = PushButton(self.tr("Cancel"), self)
        self.save_btn.setShortcut(QKeySequence.StandardKey.Save)

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
        self.rule_list.itemMoved.connect(self.on_item_moved)
        self.rule_list.customContextMenuRequested.connect(self.on_context_menu)

        self.search_box.textChanged.connect(self.apply_filter)

        self.editor.changed.connect(self.refresh_rows)

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
        row = self.rule_list.addRow("", "", "")

        self._render_row(row, entry)

        return row

    def _render_row(self, row, entry: dict):
        """
        列表行的唯一渲染入口

        提交后的刷新与编辑中的实时回显共用这一个函数：分成两套的话，「默认」列的
        ✓ 会有两条互相打架的写入路径，提交后跳回去这类不一致极难查
        """
        row.setText(0, display_name(entry))
        row.setText(1, self._get_type_str(entry.get("type")))
        row.setText(2, "✓" if entry.get("default") else "")

        # 列宽不够时长名字会被省略，而规则串在列表里根本看不到 —— 都挂进 tooltip，
        # 否则用户只能靠逐个选中来确认哪条是哪条
        row.setToolTip(0, "{name}\n{rule}".format(name = display_name(entry), rule = entry.get("rule", "")))
        row.setToolTip(2, self.tr("Chosen by default when downloading this type of media"))

    def _display_entries(self) -> list:
        """
        行的显示数据：工作副本，叠加编辑器中尚未提交的那三项

        **只用于显示，不回写工作副本** —— 写回仍然只发生在切行或保存时。
        必须整张表一起算而不是只更新当前行：默认勾选是排他的，勾了当前行就意味着
        同类型的另一行不再是默认，只改一行会让两行同时带着 ✓
        """
        entries = [entry.copy() for entry in self.rule_data_list]

        if self.current_index is None:
            return entries

        live = self.editor.dump()

        # 名字被删空时保留原名。列表行显示成空白只会让人以为规则丢了，
        # 何况校验本来就拦着空名字不让提交
        if not live.get("name"):
            live["name"] = entries[self.current_index].get("name")

        entries[self.current_index] = live

        if live.get("default"):
            for index, entry in enumerate(entries):
                if index != self.current_index and entry.get("type") == live.get("type"):
                    entry["default"] = False

        return entries

    def refresh_rows(self):
        """按当前显示数据重画所有行。编辑器的每次改动都会走到这里"""
        if len(self.rule_data_list) != self.rule_list.topLevelItemCount():
            return

        for index, entry in enumerate(self._display_entries()):
            self._render_row(self.rule_list.topLevelItem(index), entry)

    def apply_filter(self, text: str):
        """
        按关键词隐藏不匹配的行

        匹配规则名、类型名与规则串三项 —— 规则串不在任何一列里，但用户找规则时
        记得住的往往正是它

        用 hide() 而不是删行：行号必须与工作副本始终一一对应，选中、提交、拖拽
        全按全量行号走。也正因如此，筛选期间要关掉拖拽 —— 隐藏的行不参与视觉
        顺序，两者一错位，落回数据的顺序就是错的

        当前选中项被筛掉时**不动选中也不动编辑区**：用户是在找别的东西，
        不是想关掉手里这条。清空搜索框它就回来了
        """
        keywords = (text or "").strip().casefold()

        for index, entry in enumerate(self.rule_data_list):
            self.rule_list.topLevelItem(index).setHidden(
                bool(keywords) and not self._matches(entry, keywords)
            )

        self.rule_list.set_drag_enabled(not keywords)

    def _matches(self, entry: dict, keywords: str) -> bool:
        fields = (
            display_name(entry),
            self._get_type_str(entry.get("type")),
            entry.get("rule", "")
        )

        return any(keywords in str(field).casefold() for field in fields)

    def _select_row(self, index):
        self.suppress_selection = True

        if index is None or not self.rule_data_list:
            self.rule_list.setCurrentItem(None)

            self.current_index = None
            self.editor.setEnabled(False)

        else:
            index = max(0, min(index, len(self.rule_data_list) - 1))

            # 必须先比后赋值：下面这几行会把 current_index 改成新值，照抄顺序写出来的
            # `if index != self.current_index` 恒为假，守卫就废了
            changed = index != self.current_index

            self.rule_list.setCurrentItem(self.rule_list.topLevelItem(index))

            self.current_index = index
            self.editor.setEnabled(True)

            # 只在真的换了条目时才重载编辑器。重复 load 同一份数据本身是无损的，
            # 但校验没过时「把选中挪回原处」走的也是这条路径 —— 那时 load 读到的是
            # 上一次提交的内容，用户敲到一半的东西会被无声抹掉
            if changed:
                self.editor.load(self.rule_data_list[index])

        self.suppress_selection = False

        self._update_actions()

    def _update_actions(self):
        """
        工具栏按钮跟着选中项走

        默认规则删不得（删掉之后该类型就没有规则可用了），按钮就该是灰的 ——
        点下去再弹一个「不能删除默认规则」的对话框，是在惩罚用户的试探
        """
        entry = self.rule_data_list[self.current_index] if self.current_index is not None else None

        self.duplicate_action.setEnabled(entry is not None)
        self.delete_action.setEnabled(entry is not None and not entry.get("default"))

    def on_current_changed(self, current, _previous):
        if self.suppress_selection:
            return

        if self.current_index is not None and not self._commit_editor():
            # 校验没过，把选中项挪回原处，不让用户带着一条无效规则走开
            self._select_row(self.current_index)

            return

        index = self.rule_list.indexOfTopLevelItem(current) if current else -1

        self._select_row(index if index >= 0 else None)

    def _other_names(self) -> set:
        """
        与编辑器当前所选类型相同、但不是这一条的其余规则名，供重名校验使用

        取编辑器里的类型而不是工作副本里的：用户可能刚把类型改掉，重名该按改后的判
        """
        type_id = self.editor.type_choice.currentData()

        return {
            display_name(entry) for index, entry in enumerate(self.rule_data_list)
            if index != self.current_index and entry.get("type") == type_id
        }

    def _commit_editor(self):
        """把编辑区的内容写回工作副本，校验不通过时提示并返回 False"""
        valid, widget, message = self.editor.validate(self._other_names())

        if not valid:
            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", message)

            widget.setError(True)
            widget.setFocus()

            return False

        entry = self.editor.dump()

        self.rule_data_list[self.current_index] = entry

        if entry.get("default"):
            self._set_default_rule(entry.get("id"), entry.get("type"))

        self.refresh_rows()

        return True

    @property
    def dirty(self) -> bool:
        """
        工作副本与已保存的配置有没有出入

        用算的、不用标志位攒：改了又改回去、或是编辑完点「放弃修改」，标志位都会
        停在 True 上 —— 用户什么都没留下，关窗时却被问「是否丢弃修改」
        """
        return self.rule_data_list != load_rules()

    def on_add_rule(self):
        type_id = self._new_rule_type()

        # 名字存的是翻译键而不是当场的译文：存译名的话界面语言一换，这条规则的
        # 名字就固定在旧语言上了（display_name 本来就支持查键）
        self._append_rule({
            "id": str(uuid4()),
            "name": "NEW_RULE",
            "type": type_id,
            "rule": self._new_rule_seed(type_id),
            "default": False
        })

    def _new_rule_type(self):
        """
        新建规则跟随当前选中的那一条

        正在给剧集写规则时点「添加」，得到的却是一条单视频规则，还得手动改一次类型
        """
        if self.current_index is None:
            return ConventionType.NORMAL

        return self.rule_data_list[self.current_index].get("type", ConventionType.NORMAL)

    @staticmethod
    def _new_rule_seed(type_id) -> str:
        """
        新规则的初始规则串，取该类型内置默认规则的内容

        不能一律套 {leaf_title}：剧集、课程这几类的变量清单里没有它，预览会渲染成
        一个字面量下划线（实测就是「_」），用户对着一条新建出来的规则发愣，还得
        自己猜这个类型能用哪些变量。拿内置默认规则当种子，新建出来就是一条能用
        的规则，改起来也有个参照
        """
        default = next(
            (entry for entry in load_default_rules() if entry.get("type") == type_id), None
        )

        return default["rule"] if default else "{leaf_title}"

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

        # 清掉搜索词：新规则多半不匹配当前的筛选条件，而它马上就会成为选中项 ——
        # 留着筛选，用户会对着一条「不在筛选结果里」的规则编辑
        self.search_box.clear()

        self.rule_data_list.append(entry)

        self.suppress_selection = True
        self._add_row(entry)
        self.suppress_selection = False

        self._select_row(len(self.rule_data_list) - 1)

    def on_delete_rule(self):
        if self.current_index is None:
            return

        entry = self.rule_data_list[self.current_index]

        # 不允许删除默认规则：删掉之后该类型就没有规则可用了。
        # 工具栏那个删除按钮已经按这条置灰，这里是兜底 —— 挡住将来从别的入口
        # （快捷键、右键菜单）调进来的情况
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

        self._select_row(min(index, len(self.rule_data_list) - 1) if self.rule_data_list else None)

    def on_context_menu(self, pos):
        item = self.rule_list.itemAt(pos)

        if item is None:
            return

        index = self.rule_list.indexOfTopLevelItem(item)

        # 走与左键点选同一条路径，顺带提交上一条的编辑
        self.rule_list.setCurrentItem(item)

        # 提交没过时选中会被挪回原来那条，此时菜单里的动作会落到别的规则上，不弹了
        if self.current_index != index:
            return

        self._build_context_menu().exec(self.rule_list.viewport().mapToGlobal(pos))

    def _build_context_menu(self) -> RoundMenu:
        """
        列表的右键菜单

        收着两个同族的恢复动作：一个只作用于当前这条，一个作用于整张表。
        摆在一起，各自的适用范围才说得清 —— 工具栏上那个「重置为默认值」跟
        增删改挤在一排，看着像是只影响选中的那一条
        """
        entry = self.rule_data_list[self.current_index]

        restore_action = Action(
            icon = ExtendedFluentIcon.RETRY, text = self.tr("Restore to Built-in Default"), parent = self
        )
        # 自建规则没有出厂值可恢复。置灰而不是点了没反应
        restore_action.setEnabled(self.get_builtin_default(entry) is not None)
        restore_action.triggered.connect(self.on_restore_default_rule)

        reset_action = Action(
            icon = ExtendedFluentIcon.CLEAR, text = self.tr("Reset to Default"), parent = self
        )
        reset_action.triggered.connect(self.on_reset_to_default)

        menu = RoundMenu(parent = self)
        menu.addAction(restore_action)
        menu.addSeparator()
        menu.addAction(reset_action)

        return menu

    @staticmethod
    def get_builtin_default(entry: dict):
        """
        取这条规则的内置版本，自建规则返回 None

        内置规则的 id 是 DefaultValue 里写死的固定 UUID，自建规则的 id 是当场
        生成的 uuid4，按 id 匹配即可，不必额外加字段
        """
        rule_id = entry.get("id")

        return next((item for item in load_default_rules() if item.get("id") == rule_id), None)

    def on_restore_default_rule(self):
        """
        把当前这一条恢复成出厂值

        只动这一条。整表重置在同一个菜单里另有一项 —— 预设被改坏了却要连自己写的
        规则一起陪葬，是这类窗口最招人骂的设计
        """
        if self.current_index is None:
            return

        default = self.get_builtin_default(self.rule_data_list[self.current_index])

        if default is None:
            return

        # load_default_rules() 给的是深拷贝，塞进工作副本不会牵动 DefaultValue
        self.rule_data_list[self.current_index] = default

        # 先让编辑器读回新值，再重画列表 —— refresh_rows 会叠加编辑器里的现场
        self.editor.load(default)

        self.refresh_rows()

        self.show_top_toast_message(
            ToastNotificationCategory.SUCCESS, "", self.tr("Restored to the built-in default")
        )

    def on_item_moved(self, current_row: int, target_row: int):
        """
        拖拽换位后把顺序同步进工作副本

        列表本身已经被控件挪好了。顺序会随保存写进配置，而它正是下载选项下拉框里
        规则的呈现次序，所以这个动作是有实际后果的

        编辑器的现场必须**在动数据之前**提交：此刻 current_index 还指着拖动前选中的
        那一条，顺序一改，那个行号就再也对不上任何规则了
        """
        if self.current_index is not None and not self._commit_editor():
            # 提交没过，把列表挪回去。数据与视图一旦错位，后面所有行号都不作数
            self._move_row_back(target_row, current_row)

            return

        entry = self.rule_data_list.pop(current_row)
        self.rule_data_list.insert(target_row, entry)

        self._select_row(target_row)
        self.refresh_rows()

    def _move_row_back(self, from_row: int, to_row: int):
        self.suppress_selection = True

        try:
            item = self.rule_list.takeTopLevelItem(from_row)
            self.rule_list.insertTopLevelItem(to_row, item)

            self.rule_list.setCurrentItem(self.rule_list.topLevelItem(self.current_index))

        finally:
            self.suppress_selection = False

    def on_reset_to_default(self):
        # 文案要说明内置规则也会被还原：用户很可能只是想重置某一类，而这条会把
        # 他对预设的改名、改规则一并抹掉
        dialog = MessageBox(
            self.tr("Reset to Default"),
            self.tr("All custom naming rules will be discarded, and the built-in rules will be restored. Continue?"),
            self
        )

        if not dialog.exec():
            return

        self.rule_data_list = load_default_rules()
        self.current_index = None

        self.init_rule_list()

    def on_save(self):
        if self.current_index is not None and not self._commit_editor():
            return

        save_rules(self.rule_data_list)

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
        key = reversed_convention_type_map.get(type_value)

        # Translator 的取键方法在 key 为 None 时会把整张映射表还回来，不能直接
        # 当字符串用。类型值不在表里只有配置被手工改过才会出现
        return Translator.CONVENTION_TYPE(key) if key else ""

    def _set_default_rule(self, rule_id: str, rule_type: int):
        """把该类型的默认规则收敛到指定的那一条。显示交给 refresh_rows 统一负责"""
        for entry in self.rule_data_list:
            if entry.get("type") == rule_type:
                entry["default"] = (entry.get("id") == rule_id)
