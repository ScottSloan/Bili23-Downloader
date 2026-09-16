from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFontMetrics

from qfluentwidgets import (
    FlyoutViewBase, Flyout, FlyoutAnimationType, FluentIcon, ComboBox, LineEdit,
    BodyLabel, StrongBodyLabel, CaptionLabel, PushButton, TransparentPushButton,
    RoundMenu, Action
)

from .widget.button import TransparentToolButton
from .widget.scroll import ScrollArea

from util.common.data.naming_convention import VariableListFactory
from util.common.translator import Translator
from util.common.enum import VariableType

from util.format.rule_model import Fragment, Level, RuleModel, parse_rule, UnsupportedRule
from util.format.rule_format import presets_for, preview_spec

def _discard(widget: QWidget):
    """
    丢弃一个不再需要的控件

    光调 deleteLater 不够：控件从布局里 takeAt 出来之后父子关系还在，DeferredDelete
    要等下一轮事件循环才处理，这中间它会**继续画在原来的位置上**。层级一多，重建
    赶上同一轮事件，界面就会出现上下重影。先断开父子关系，当场从画面上消失。
    """
    widget.setParent(None)
    widget.deleteLater()

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
    """
    点击芯片后弹出的片段编辑面板

    面板里有哪几行，在构造时就按片段种类定死，之后只切换可用状态，**绝不增删行**：
    Flyout 是 Qt.Popup 顶层窗口，本视图躺在它的布局里，行一显一隐之后窗口并不会跟着
    resize（adjustSize 对布局内的子控件是无效调用），新冒出来的那一行会被裁在窗口
    之外 —— 看得见、点不着。尺寸恒定就从根上绕开了这件事。
    """

    changed = Signal()
    removed = Signal()
    moved = Signal(int)

    def __init__(self, fragment: Fragment, variables: dict, parent = None):
        super().__init__(parent)

        self.fragment = fragment
        self.variables = variables

        self.init_UI()

        self.init_data()

        self.connect_signals()

    def init_UI(self):
        self.title_lab = StrongBodyLabel(self.tr("Edit fragment"), self)

        self.left_btn = self._tool_button(FluentIcon.LEFT_ARROW, self.tr("Move left"))
        self.right_btn = self._tool_button(FluentIcon.RIGHT_ARROW, self.tr("Move right"))

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addWidget(self.title_lab)
        title_layout.addSpacing(20)
        title_layout.addStretch()
        title_layout.addWidget(self.left_btn)
        title_layout.addWidget(self.right_btn)

        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(8)

        self.remove_btn = PushButton(FluentIcon.DELETE, self.tr("Remove"), self)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.addLayout(title_layout)
        main_layout.addSpacing(6)
        main_layout.addLayout(self.form_layout)

        if self.fragment.is_text:
            self._init_text_rows()
        else:
            self._init_variable_rows(main_layout)

        main_layout.addSpacing(6)
        main_layout.addWidget(self.remove_btn)

    def _init_text_rows(self):
        self.text_box = LineEdit(self)
        self.text_box.setMinimumWidth(240)

        self.form_layout.addRow(BodyLabel(self.tr("Text"), self), self.text_box)

    def _init_variable_rows(self, main_layout: QVBoxLayout):
        self.variable_choice = ComboBox(self)
        self.variable_choice.setMinimumWidth(240)

        self.format_choice = ComboBox(self)
        self.format_choice.setMinimumWidth(240)

        self.format_box = LineEdit(self)
        self.format_box.setPlaceholderText(self.tr("Custom format"))

        self.prefix_box = LineEdit(self)
        self.suffix_box = LineEdit(self)

        self.tip_label = CaptionLabel(self.tr("The prefix and suffix disappear together with the variable"), self)
        self.tip_label.setWordWrap(True)

        self.form_layout.addRow(BodyLabel(self.tr("Variable"), self), self.variable_choice)
        self.form_layout.addRow(BodyLabel(self.tr("Format"), self), self.format_choice)
        self.form_layout.addRow(BodyLabel("", self), self.format_box)
        self.form_layout.addRow(BodyLabel(self.tr("Prefix"), self), self.prefix_box)
        self.form_layout.addRow(BodyLabel(self.tr("Suffix"), self), self.suffix_box)

        main_layout.addWidget(self.tip_label)

    def _tool_button(self, icon, tooltip: str):
        button = TransparentToolButton(icon, self)
        button.setToolTip(tooltip)

        return button

    def init_data(self):
        if self.fragment.is_text:
            self.text_box.setText(self.fragment.text)
        else:
            self._init_variable_choice()
            self._init_format_choice()

            self.prefix_box.setText(self.fragment.prefix)
            self.suffix_box.setText(self.fragment.suffix)

        self._update_state()

    def set_move_state(self, can_left: bool, can_right: bool):
        """首末位的片段挪不动，按钮置灰 —— 点了没反应比按钮变灰更让人困惑"""
        self.left_btn.setEnabled(can_left)
        self.right_btn.setEnabled(can_right)

    def _init_variable_choice(self):
        self.variable_choice.blockSignals(True)

        try:
            for entry in self.variables.values():
                self.variable_choice.addItem(variable_label(entry), userData = entry["name"])

            index = self.variable_choice.findData(self.fragment.variable)

            if index != -1:
                self.variable_choice.setCurrentIndex(index)

        finally:
            self.variable_choice.blockSignals(False)

    def _init_format_choice(self):
        """
        重填格式下拉框

        重填期间必须屏蔽信号：qfluentwidgets 的 ComboBox 在加入第一项时会自行
        setCurrentIndex(0) 并发出 currentIndexChanged，换变量时它会把刚刚重置过的
        spec 又写成第一个预设，还要连带触发好几次规则重渲染。
        """
        self.format_choice.blockSignals(True)

        try:
            self.format_choice.clear()

            presets = presets_for(self._variable_type())

            if not presets:
                # 没有格式可选的变量也保留这一行，只是禁用 —— 行忽隐忽现会改变面板
                # 尺寸，而 Flyout 不会跟着 resize
                self.format_choice.addItem(self.tr("Not available for this variable"), userData = "")
                self.format_choice.setCurrentIndex(0)

                return

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

                self._set_format_text(self.fragment.spec)
            else:
                self.format_choice.setCurrentIndex(index)

        finally:
            self.format_choice.blockSignals(False)

    def _set_format_text(self, text: str):
        self.format_box.blockSignals(True)

        try:
            self.format_box.setText(text)

        finally:
            self.format_box.blockSignals(False)

    def _variable_type(self):
        entry = self.variables.get(self.fragment.variable)

        return entry.get("type", VariableType.TEXT) if entry else VariableType.TEXT

    def _update_state(self):
        if not self.fragment.is_text:
            has_format = bool(presets_for(self._variable_type()))

            self.format_choice.setEnabled(has_format)
            self.format_box.setEnabled(has_format and self.format_choice.currentData() is None)

        # Flyout 给本视图挂了 QGraphicsDropShadowEffect，带图形特效的控件、其子控件
        # 自绘时缓存不会失效：不强制整体重绘的话，下拉框会一直显示旧文字，直到鼠标
        # 划过去才「突然」刷新
        self.update()

    def connect_signals(self):
        if self.fragment.is_text:
            self.text_box.textChanged.connect(self.on_edited)
        else:
            self.variable_choice.currentIndexChanged.connect(self.on_variable_changed)
            self.format_choice.currentIndexChanged.connect(self.on_format_changed)

            self.format_box.textChanged.connect(self.on_edited)
            self.prefix_box.textChanged.connect(self.on_edited)
            self.suffix_box.textChanged.connect(self.on_edited)

        self.left_btn.clicked.connect(lambda: self.moved.emit(-1))
        self.right_btn.clicked.connect(lambda: self.moved.emit(1))

        self.remove_btn.clicked.connect(self.removed)

    def on_variable_changed(self):
        self.fragment.variable = self.variable_choice.currentData()

        # 换了变量，原来的格式多半不再适用（日期格式套到数字上会直接报错）。
        # 落到新变量的第一个预设而不是空串：时间变量不带格式渲染出来是
        # 「2026-03-07 00:00:00」，冒号会被净化成下划线，没人想要那个文件名
        presets = presets_for(self._variable_type())

        self.fragment.spec = presets[0] if presets else ""

        self._set_format_text("")
        self._init_format_choice()
        self._update_state()

        self.changed.emit()

    def on_format_changed(self):
        self._update_state()
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
    """规则里的一个片段，左键打开编辑面板，右键给出同样的几个动作"""

    changed = Signal()
    removed = Signal(object)
    moveRequested = Signal(object, int)

    # 芯片是一排横向排布的按钮，标签过长会把整行挤散，超出就省略
    MAX_LABEL_WIDTH = 200

    def __init__(self, fragment: Fragment, variables: dict, parent = None):
        super().__init__(parent)

        self.fragment = fragment
        self.variables = variables

        self.view = None

        self.can_move_left = False
        self.can_move_right = False

        self.setFixedHeight(30)

        self.refresh()

        self.clicked.connect(self.on_edit)

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

    def set_move_state(self, can_left: bool, can_right: bool):
        self.can_move_left = can_left
        self.can_move_right = can_right

        if self.view:
            self.view.set_move_state(can_left, can_right)

    def on_edit(self):
        view = FragmentEditView(self.fragment, self.variables, self)

        view.changed.connect(self.on_changed)
        view.removed.connect(lambda: self.removed.emit(self.fragment))
        view.moved.connect(lambda offset: self.moveRequested.emit(self.fragment, offset))
        view.set_move_state(self.can_move_left, self.can_move_right)

        self.view = view

        flyout = Flyout.make(view, self, self.window(), FlyoutAnimationType.DROP_DOWN)
        flyout.closed.connect(self.on_flyout_closed)

    def on_flyout_closed(self):
        # 面板关闭时会把视图一并 deleteLater，别再攥着一个已经析构的 C++ 对象
        self.view = None

    def contextMenuEvent(self, event):
        menu = RoundMenu(parent = self)

        edit_action = Action(icon = FluentIcon.EDIT, text = self.tr("Edit"), parent = self)
        edit_action.triggered.connect(self.on_edit)

        left_action = Action(icon = FluentIcon.LEFT_ARROW, text = self.tr("Move left"), parent = self)
        left_action.setEnabled(self.can_move_left)
        left_action.triggered.connect(lambda: self.moveRequested.emit(self.fragment, -1))

        right_action = Action(icon = FluentIcon.RIGHT_ARROW, text = self.tr("Move right"), parent = self)
        right_action.setEnabled(self.can_move_right)
        right_action.triggered.connect(lambda: self.moveRequested.emit(self.fragment, 1))

        remove_action = Action(icon = FluentIcon.DELETE, text = self.tr("Remove"), parent = self)
        remove_action.triggered.connect(lambda: self.removed.emit(self.fragment))

        menu.addAction(edit_action)
        menu.addAction(left_action)
        menu.addAction(right_action)
        menu.addSeparator()
        menu.addAction(remove_action)

        menu.exec(self.mapToGlobal(event.pos()))

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

        self.chips = []

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

    def set_level_state(self, can_up: bool, can_down: bool):
        """只有一层目录时上下移动无处可去，置灰而不是点了没反应"""
        if not self.movable:
            return

        self.up_btn.setEnabled(can_up)
        self.down_btn.setEnabled(can_down)

    def refresh(self):
        while self.chip_layout.count():
            item = self.chip_layout.takeAt(0)

            if item.widget():
                _discard(item.widget())

        self.chips = []

        for fragment in self.level.fragments:
            chip = FragmentChip(fragment, self.variables, self)
            chip.changed.connect(self.changed)
            chip.removed.connect(self.on_remove_fragment)
            chip.moveRequested.connect(self.move_fragment)

            self.chip_layout.addWidget(chip)

            self.chips.append(chip)

        if not self.level.fragments:
            self.chip_layout.addWidget(CaptionLabel(self.tr("Empty, will be skipped"), self))

        self._sync_chip_states()

    def _sync_chip_states(self):
        last = len(self.chips) - 1

        for index, chip in enumerate(self.chips):
            chip.set_move_state(index > 0, index < last)

    def on_add(self):
        """
        插入菜单直接把变量列出来

        以前是先插一个「变量表里的第一个变量」，再让用户点开芯片改成想要的那个 ——
        插进来的东西和用户想插的毫无关系，这一步才是最让人发懵的地方。
        """
        menu = RoundMenu(parent = self)

        more = []

        for entry in self.variables.values():
            if entry.get("group") == "MORE":
                more.append(entry)
            else:
                menu.addAction(self._variable_action(entry, menu))

        if more:
            sub_menu = RoundMenu(self.tr("More variables"), self)
            sub_menu.setIcon(FluentIcon.MORE)

            for entry in more:
                sub_menu.addAction(self._variable_action(entry, sub_menu))

            menu.addMenu(sub_menu)

        menu.addSeparator()

        text_action = Action(icon = FluentIcon.FONT, text = self.tr("Insert text"), parent = self)
        text_action.triggered.connect(lambda: self.add_fragment(Fragment(text = ""), edit = True))

        menu.addAction(text_action)

        menu.exec(self.add_btn.mapToGlobal(self.add_btn.rect().bottomLeft()))

    def _variable_action(self, entry: dict, parent):
        action = Action(icon = FluentIcon.TAG, text = variable_label(entry), parent = parent)
        action.setToolTip(entry["variable"])
        action.triggered.connect(lambda *_, name = entry["name"]: self.add_fragment(Fragment(variable = name)))

        return action

    def add_fragment(self, fragment: Fragment, edit: bool = False):
        self.level.fragments.append(fragment)

        self.refresh()
        self.changed.emit()

        if edit and self.chips:
            # 刚插进来的文字片段是个「(空)」芯片，直接把编辑面板打开，
            # 省得用户去猜要点哪里才能填字
            self.chips[-1].on_edit()

    def move_fragment(self, fragment: Fragment, offset: int):
        index = self.level.fragments.index(fragment)
        target = index + offset

        if not 0 <= target < len(self.level.fragments):
            return

        self.level.fragments[index], self.level.fragments[target] = self.level.fragments[target], self.level.fragments[index]

        # 原地搬运芯片，不走 refresh() 整行重建：重建会把芯片连同它正开着的编辑面板
        # 一起 deleteLater 掉，用户点一次「左移」面板就没了，连点两下都做不到
        self.chip_layout.insertWidget(target, self.chip_layout.takeAt(index).widget())

        self.chips.insert(target, self.chips.pop(index))

        self._sync_chip_states()
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

    目录层级放在滚动区里、文件名留在滚动区外：层级一多，整块内容会把预览和变量表
    一起压扁，而文件名是整条规则里最关键的一行，不能被滚走。
    """

    ruleChanged = Signal(str)

    # 目录层级上限。层级越深越容易撞上 Windows 的 260 字符路径限制，
    # 落盘失败比编辑器里少一层难查得多
    MAX_LEVELS = 8

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

        self.limit_lab = CaptionLabel(
            self.tr("At most {count} directory levels").format(count = self.MAX_LEVELS), self
        )
        self.limit_lab.hide()

        # 「添加层级」留在滚动区**外面**：它是固定入口，跟着内容滚走的话，
        # 层级一多用户就找不到该点哪里了
        add_layout = QHBoxLayout()
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.addWidget(self.add_level_btn)
        add_layout.addWidget(self.limit_lab)
        add_layout.addStretch()

        scroll_layout = QVBoxLayout()
        # 右边留出滚动条的位置，免得滚动条压在层级行的删除按钮上
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        scroll_layout.addLayout(self.level_layout)
        scroll_layout.addStretch()

        self.level_scroll = ScrollArea(self)
        self.level_scroll.setScrollLayout(scroll_layout)
        # 最小高度只保一行。给大了反而坏事：窗口压到最小尺寸时，右栏各块的最小高度
        # 之和一旦超过可用空间，Qt 会无视最小值继续压缩，而这个硬性下限会让滚动区
        # 画到分配区之外，直接盖住下面的「文件名」。
        # 平时它在 body_layout 里 stretch=1，能拿到的远不止这点高度
        self.level_scroll.setMinimumHeight(60)
        # 别的地方用 ScrollArea 都是整页铺满，这里是嵌在面板中间的一块：
        # 不让视口透明的话，暗色主题下会糊出一个浅灰方块
        self.level_scroll.enableTransparentBackground()

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
        body_layout.addWidget(self.level_scroll, 1)
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
            self.level_layout.addWidget(self._level_widget(level, index + 1))

        self.file_name_layout.addWidget(self._build_row(file_name, movable = False))

        for index, row in enumerate(self.rows[:len(directories)]):
            row.set_level_state(index > 0, index < len(directories) - 1)

        can_add = len(directories) < self.MAX_LEVELS

        self.add_level_btn.setEnabled(can_add)
        self.limit_lab.setVisible(not can_add)

    def _level_widget(self, level: Level, number: int):
        widget = QWidget(self)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(BodyLabel(self.tr("Level {number}").format(number = number), widget))
        layout.addSpacing(8)
        layout.addWidget(self._build_row(level, movable = True), 1)

        return widget

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
                _discard(item.widget())

            elif item.layout():
                RuleBuilderWidget._clear_layout(item.layout())

    def on_add_level(self):
        if len(self.model.levels) > self.MAX_LEVELS:
            return

        # 新层级插在文件名之前 —— 最后一层永远是文件名
        self.model.levels.insert(max(len(self.model.levels) - 1, 0), Level())

        self.rebuild()
        self.on_changed()

        # 新层级多半落在可视区之外，滚过去让用户看见自己刚加了什么。
        # 延到下一轮事件循环：此刻布局还没重新算完，滚过去也是滚了个寂寞
        QTimer.singleShot(0, self.scroll_to_last_level)

    def scroll_to_last_level(self):
        if len(self.rows) >= 2:
            self.level_scroll.ensureWidgetVisible(self.rows[-2])

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
