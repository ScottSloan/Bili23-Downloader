"""
GUI 层的构造冒烟测试。

这一层此前零覆盖，而它恰恰是最容易被"清理未使用的导入"误伤的地方：
删掉一个只在某个分支里用到的符号，导入依然成功，直到用户点开那个对话框
才会 NameError。这里把改动面较大的控件与对话框实际构造一遍。

不断言外观，只断言"能造出来且不抛异常" —— 目标是挡住导入级与初始化级的回归，
而不是做视觉测试。
"""

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

import pytest


@pytest.fixture(scope = "module")
def app():
    # QApplication 全进程只能有一个，模块级复用
    instance = QApplication.instance() or QApplication([])

    import res.resources_rc   # noqa: F401  图标与样式表由此注册，构造控件时会用到

    return instance


@pytest.fixture
def parent(app):
    return QWidget()


class TestListWidgets:
    def test_entry_item_delegate(self, parent):
        from gui.component.entry_list.entry_item_delegate import EntryListItemDelegate

        assert EntryListItemDelegate(parent) is not None

    def test_poster_item_delegate(self, parent):
        from gui.component.entry_list.poster_item_delegate import PosterListItemDelegate

        assert PosterListItemDelegate(parent) is not None

    def test_entry_list_view(self, parent):
        from gui.component.entry_list.list_view import EntryListView

        assert EntryListView(parent) is not None


class TestNavigationPanel:
    def test_items_is_dict(self, parent):
        # items 的类型标注曾是旧式 type comment（# type: Dict[...]），
        # 已改为 PEP 526 注解。注解在运行时会被求值，写错会直接抛 NameError
        from gui.component.widget.navigation import NavigationPanel

        assert isinstance(NavigationPanel(parent).items, dict)


class TestSettingCards:
    @pytest.mark.parametrize(
        "name",
        ["DanmakuSettingCard", "SubtitleSettingCard", "CoverSettingCard",
         "ChapterSettingCard", "MetadataSettingCard", "DownloadFormatCard",
         # 同时被设置界面与下载选项对话框复用，两边构筑路径不同，都过一遍
         "MediaOptionsCard"],
    )
    def test_card_constructs(self, parent, name):
        from gui.component import setting

        assert getattr(setting, name)(parent) is not None


class TestStyleDialogs:
    """这两个对话框的 ScrollArea 曾被重复导入，qfluentwidgets 版本被项目版本遮蔽"""

    def test_danmaku_style_dialog(self, parent):
        from gui.dialog.setting.danmaku_style import DanmakuStyleDialog

        assert DanmakuStyleDialog(parent) is not None

    def test_subtitles_style_dialog(self, parent):
        from gui.dialog.setting.subtitles_style import SubtitlesStyleDialog

        assert SubtitlesStyleDialog(parent) is not None

    def test_uses_project_scroll_area(self):
        # 项目版 ScrollArea 带平滑滚动，必须是它而不是 qfluentwidgets 的原版
        from gui.component.widget.scroll import ScrollArea
        from gui.dialog.setting import danmaku_style

        assert danmaku_style.ScrollArea is ScrollArea


class TestMiscDialogs:
    def test_interactive_video_dialog(self, parent):
        from gui.dialog.misc.interactive_video import InteractiveVideoDialog

        assert InteractiveVideoDialog({"title": "t", "choices": []}, parent) is not None


class TestNamingRuleEditor:
    """
    命名规则编辑器

    这两个类此前没有任何构造覆盖。规则编辑改成可视化之后，「载入 → 编辑 →
    取出」这条往返链路是最容易在重构中悄悄坏掉的地方。
    """

    RULE = "{space_owner}/{parent_title}/<P{p:02d}->{leaf_title}"

    def test_rule_builder_round_trip(self, parent):
        from gui.component.rule_builder import RuleBuilderWidget
        from util.common.enum import ConventionType

        builder = RuleBuilderWidget(parent)
        builder.set_type(ConventionType.SPACE)

        assert builder.set_rule(self.RULE)
        assert builder.rule() == self.RULE

    def test_rule_builder_degrades_on_unsupported_rule(self, parent):
        from gui.component.rule_builder import RuleBuilderWidget
        from util.common.enum import ConventionType

        builder = RuleBuilderWidget(parent)
        builder.set_type(ConventionType.SPACE)

        # 表达不了时禁用可视化区并给出原因，绝不静默丢掉解析不了的部分
        assert not builder.set_rule("<{parent_title}-{leaf_title}>")
        assert not builder.body.isEnabled()
        assert builder.unsupported_label.text()

        assert builder.set_rule("{leaf_title}")
        assert builder.body.isEnabled()

    def test_edit_panel_load_and_dump(self, parent):
        from gui.dialog.setting.edit_rule import EditRuleDialog
        from util.common.enum import ConventionType

        entry = {
            "id": "test-id",
            "name": "DEFAULT_FOR_SPACE",
            "type": ConventionType.SPACE,
            "rule": self.RULE,
            "default": False
        }

        panel = EditRuleDialog(parent)
        panel.load(entry)

        result = panel.dump()

        assert result["rule"] == self.RULE
        assert result["type"] == ConventionType.SPACE
        # 名称没改动过，内置规则要把翻译键原样存回去
        assert result["name"] == "DEFAULT_FOR_SPACE"

    def test_edit_panel_previews_every_shape(self, parent):
        from gui.dialog.setting.edit_rule import EditRuleDialog
        from util.common.data.naming_convention import SampleShape
        from util.common.enum import ConventionType

        panel = EditRuleDialog(parent)
        panel.load({"id": "x", "name": "n", "type": ConventionType.SPACE, "rule": self.RULE, "default": False})
        panel.refresh_preview()

        rendered = {shape: label.text() for shape, label in panel.preview_panel.rows.items()}

        # 同一条规则在三种形态下给出三种结果，这正是可选段存在的理由
        assert len(rendered) == 3
        assert "P04-" in rendered[SampleShape.MULTI]
        assert "P0" not in rendered[SampleShape.SINGLE]

    def test_edit_panel_validation_messages(self, parent):
        from gui.dialog.setting.edit_rule import EditRuleDialog
        from util.common.enum import ConventionType

        panel = EditRuleDialog(parent)
        panel.load({"id": "x", "name": "n", "type": ConventionType.NORMAL, "rule": "{leaf_title}", "default": False})

        assert panel.validate_rule("{leaf_title}")[0]

        # 以前一律报「命名规则无效」，用户根本不知道错在哪个变量上
        valid, message = panel.validate_rule("{titel}")

        assert not valid
        assert "titel" in message

    def test_rule_builder_scrolls_when_levels_pile_up(self, parent):
        """层级堆多了要滚动，不能把预览和变量表一起压扁"""
        from gui.component.rule_builder import RuleBuilderWidget
        from util.common.enum import ConventionType

        builder = RuleBuilderWidget(parent)
        builder.set_type(ConventionType.SPACE)
        builder.set_rule("/".join(["{leaf_title}"] * 6))

        scroll_widget = builder.level_scroll.widget()

        # 目录层在滚动区里，文件名留在滚动区外 —— 它是最关键的一行，不能被滚走
        assert builder.rows[0].parent() is not None
        assert scroll_widget.isAncestorOf(builder.rows[0])
        assert not scroll_widget.isAncestorOf(builder.rows[-1])

        # 超过上限就不给再加了，并且把原因摆在按钮旁边（禁用控件不弹 tooltip）
        for _ in range(builder.MAX_LEVELS):
            builder.on_add_level()

        assert len(builder.model.levels) == builder.MAX_LEVELS + 1
        assert not builder.add_level_btn.isEnabled()
        assert builder.limit_lab.isVisibleTo(builder)

    def test_rebuild_does_not_spawn_stray_windows(self, parent):
        """
        重建层级时不能冒出野生顶层窗口

        被丢弃的控件必须 hide() 而不是 setParent(None)：后者会把它变成顶层窗口，
        在 DeferredDelete 真正执行前作为独立窗口显示出来 —— 切换规则时屏幕上会
        闪过一排空窗口。
        """
        from gui.component.rule_builder import RuleBuilderWidget, RuleLevelRow
        from util.common.enum import ConventionType

        parent.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        parent.resize(700, 400)
        parent.show()

        builder = RuleBuilderWidget(parent)
        builder.resize(700, 400)
        builder.show()

        builder.set_type(ConventionType.SPACE)
        builder.set_rule("/".join(["{leaf_title}"] * 5))

        # 不放行 DeferredDelete：待销毁的控件只在这个窗口期里露头
        builder.set_rule("{space_owner}/{leaf_title}")

        stray = [
            widget for widget in QApplication.allWidgets()
            if isinstance(widget, RuleLevelRow) and widget.parent() is None
        ]

        assert not stray

    @pytest.mark.parametrize("case", ["favorite", "collection"])
    def test_editor_does_not_overlap_at_minimum_height(self, parent, case):
        """
        窗口压到最小尺寸时右栏不能重叠

        右栏把可视化编辑器、预览、变量表叠在一栏里，各块的最小高度之和一旦超过
        窗口能给的，Qt 就不再理会最小值继续压，带硬性下限的滚动区会画到分配区
        之外、直接盖住「文件名」那一行。以后往这一栏里再加东西，先看这条用例。

        按预览行数取两个类型：收藏夹三行形态加一行混入提示，合集两行形态 ——
        预览越高，留给可视化编辑器的高度越少，重叠就是从那里开始的
        """
        from gui.dialog.setting.edit_rule import EditRuleDialog
        from util.common.enum import ConventionType

        cases = {
            "favorite": (
                ConventionType.FAVORITE,
                "{favorites_owner_id}_{favorites_owner}/{favorites_name}/{parent_title}/<P{p:02d}->{leaf_title}"
            ),
            "collection": (
                ConventionType.COLLECTION,
                "{collection_title}/{section_title}/{parent_title}/{leaf_title}"
            ),
        }

        type_id, rule = cases[case]

        panel = EditRuleDialog(parent)
        panel.load({
            "id": "x", "name": "n", "type": type_id, "rule": rule, "default": False
        })

        # 最坏组合：最小窗口高度减去标题栏与按钮行 + 高级区展开 + 规则报错多出一行红字
        panel.advanced_btn.setChecked(True)
        panel.rule_box.setText("{titel}")
        panel.refresh_preview()

        # WA_DontShowOnScreen：走完整的布局流程但不真的弹出窗口。
        # 只调 layout().activate() 的话，嵌套布局不会被激活，量到的全是默认几何
        parent.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        parent.resize(700, 630)
        parent.show()

        panel.resize(700, 630)
        panel.show()

        builder = panel.builder

        def top_of(widget):
            return widget.mapTo(builder, widget.rect().topLeft()).y()

        assert builder.level_scroll.geometry().bottom() <= top_of(builder.add_level_btn)
        assert builder.add_level_btn.geometry().bottom() <= top_of(builder.file_name_label)
        assert builder.file_name_label.geometry().bottom() <= top_of(builder.rows[-1])

    def test_variable_list_can_be_folded_away(self, parent):
        """三十来行的变量表要能收起来，把高度还给可视化编辑器"""
        from gui.dialog.setting.edit_rule import EditRuleDialog
        from util.common.enum import ConventionType

        panel = EditRuleDialog(parent)
        panel.load({
            "id": "x", "name": "n", "type": ConventionType.NORMAL,
            "rule": "{leaf_title}", "default": False
        })

        # 默认展开：折叠的价值是「想专心时收起来」，默认收起会让新用户找不到变量
        assert panel.variable_btn.isChecked()
        assert not panel.variable_list.isHidden()

        panel.variable_btn.setChecked(False)

        assert panel.variable_list.isHidden()

    def test_fragment_move_inside_file_name(self, parent):
        """文件名那一行的片段此前只能删掉重加，顺序完全调不了"""
        from gui.component.rule_builder import RuleBuilderWidget
        from util.common.enum import ConventionType

        builder = RuleBuilderWidget(parent)
        builder.set_type(ConventionType.SPACE)
        builder.set_rule(self.RULE)

        row = builder.rows[-1]
        leaf = row.level.fragments[1]

        row.move_fragment(leaf, -1)

        assert builder.rule() == "{space_owner}/{parent_title}/{leaf_title}<P{p:02d}->"
        # 芯片是原地搬运的，不是整行重建 —— 重建会把正开着的编辑面板一起销毁
        assert row.chips[0].fragment is leaf
        assert not row.chips[0].can_move_left
        assert row.chips[1].can_move_left

    def test_fragment_edit_view_keeps_shape_on_variable_change(self, parent):
        """换变量不改面板的行数，也不会把格式串污染成时间变量用不了的写法"""
        from gui.component.rule_builder import FragmentEditView, RuleBuilderWidget
        from util.common.enum import ConventionType
        from util.format.rule_model import Fragment

        builder = RuleBuilderWidget(parent)
        builder.set_type(ConventionType.SPACE)

        fragment = Fragment(variable = "leaf_title")

        view = FragmentEditView(fragment, builder.variables, parent)

        rows = view.form_layout.rowCount()

        view.variable_choice.setCurrentIndex(view.variable_choice.findData("pub_time"))

        assert fragment.variable == "pub_time"
        # 时间变量不带格式渲染出来是「2026-03-07 00:00:00」，冒号要被净化成下划线
        assert fragment.spec == "%Y-%m-%d"
        assert view.form_layout.rowCount() == rows
        assert view.format_choice.isEnabled()
        assert not view.format_box.isEnabled()


class TestCDNServerDialog:
    """
    CDN 节点对话框

    拖拽换位抽成混入之后，它是 RuleListDialog 之外唯一的使用方，而混入里为了
    行号不错位还屏蔽了信号 —— 这里确认另一个使用方没被带坏
    """

    def test_drag_reorders_the_node_list(self, parent):
        from gui.dialog.setting.cdn_server import CDNServerDialog

        dialog = CDNServerDialog(parent)
        node_list = dialog.cdn_server_list

        if node_list.topLevelItemCount() < 2:
            pytest.skip("默认节点不足两条，换位无从谈起")

        first = dialog.cdn_list[0]

        node_list.insertTopLevelItem(1, node_list.takeTopLevelItem(0))
        dialog.on_item_moved(0, 1)

        assert dialog.cdn_list[1] is first
        assert len(dialog.cdn_list) == node_list.topLevelItemCount()


class TestNamingRuleDialog:
    """
    命名规则窗口

    这个类此前没有任何覆盖，而它管着「选中项、编辑器内容、工作副本」三者的同步 ——
    窗口的一半行为都藏在这条状态机里，改起来最容易悄悄坏掉。
    """

    @staticmethod
    def _open(parent):
        from gui.dialog.setting.rule_list import RuleListDialog

        window = RuleListDialog(parent)

        # 校验失败会弹 InfoBar，它带动画与定时器，在无头环境里纯粹是噪声。
        # 换成空实现，顺便把「有没有提示」变成可断言的事实
        window.toast_messages = []
        window.show_top_toast_message = lambda category, title, message: window.toast_messages.append(message)

        return window

    def test_invalid_edit_survives_switching_rows(self, parent):
        """
        校验没过时点别的规则，不能把用户敲到一半的内容抹掉

        曾经的写法是「挪回原选中」时顺手 load 一遍，而 load 读到的是上一次提交的
        内容 —— 用户正在输入的规则串就这么无声消失了，提示里还没有一句话说「已还原」
        """
        window = self._open(parent)
        window.editor.preview_timer.stop()

        window.editor.rule_box.setText("<P{p:02d}-{leaf_title}")

        committed = window.rule_data_list[0]["rule"]
        typed = window.editor.rule_box.text()

        window.rule_list.setCurrentItem(window.rule_list.topLevelItem(1))

        assert window.toast_messages, "校验没过要给提示"
        assert window.current_index == 0, "应把选中挪回原来那一条"
        assert window.editor.rule_box.text() == typed, "用户输入的内容必须原样留着"
        assert window.rule_data_list[0]["rule"] == committed, "值不回工作副本"

    def test_discard_restores_the_committed_state(self, parent):
        """「放弃修改」是校验失败时唯一的出路，得真的把人送回上一次提交的状态"""
        window = self._open(parent)
        window.editor.preview_timer.stop()

        committed = window.rule_data_list[0]["rule"]

        window.editor.rule_box.setText("<P{p:02d}-{leaf_title}")
        window.editor.refresh_preview()

        assert not window.editor.discard_btn.isHidden()

        window.editor.on_discard()

        assert window.editor.rule_box.text() == committed
        assert window.editor.discard_btn.isHidden()

    def test_discard_hint_is_reserved_for_rule_errors(self, parent):
        """
        规则名出错时不摆「放弃修改」

        它住在高级区里，而规则名出错时那一区是收着的 —— 摆出来用户也看不见，
        反倒会在展开高级区后看到一个来路不明的按钮。名字为空有红框和焦点，
        重打一遍就是了
        """
        window = self._open(parent)
        window.editor.preview_timer.stop()

        window.editor.name_box.setText("")
        window.editor.refresh_preview()

        assert window.editor.discard_btn.isHidden()

        window.rule_list.setCurrentItem(window.rule_list.topLevelItem(1))

        assert window.toast_messages, "仍然要给出提示"
        assert window.editor.discard_btn.isHidden()

    def test_name_edit_shows_up_in_the_list_immediately(self, parent):
        """名字改一下左栏当场跟着变 —— 提交时机没变，变的只是显示"""
        window = self._open(parent)
        window.editor.preview_timer.stop()

        window.editor.name_box.setText("我的规则")

        assert window.rule_list.topLevelItem(0).text(0) == "我的规则"
        # 显示归显示，工作副本要等切行或保存才动
        assert window.rule_data_list[0]["name"] != "我的规则"

    def test_checking_default_clears_the_other_row(self, parent):
        """默认勾选是排他的，实时回显也得把同类型另一行的 ✓ 撤掉"""
        window = self._open(parent)
        window.editor.preview_timer.stop()

        first = window.rule_data_list[0]

        window._append_rule({
            "id": "test-copy",
            "name": "副本",
            "type": first["type"],
            "rule": "{leaf_title}",
            "default": False
        })

        new_index = window.rule_list.topLevelItemCount() - 1

        assert window.current_index == new_index
        assert window.rule_list.topLevelItem(0).text(2) == "✓"

        window.editor.set_default_chk.setChecked(True)

        assert window.rule_list.topLevelItem(new_index).text(2) == "✓"
        assert window.rule_list.topLevelItem(0).text(2) == ""
        # 提交之前，工作副本里第一条仍然是默认规则
        assert window.rule_data_list[0]["default"] is True

    def test_filter_hides_rows_and_blocks_dragging(self, parent):
        """
        搜索只隐藏行、不删行

        行号要与工作副本始终一一对应，所以筛选期间必须关掉拖拽 —— 隐藏的行不参与
        视觉顺序，两者一错位，落回数据的顺序就是错的
        """
        window = self._open(parent)
        window.editor.preview_timer.stop()

        total = window.rule_list.topLevelItemCount()

        # 只有「合集」那条默认规则用到这个变量
        window.search_box.setText("{collection_title}")

        visible = [index for index in range(total) if not window.rule_list.topLevelItem(index).isHidden()]

        assert visible == [2]
        assert not window.rule_list._drag_enabled

        window.search_box.setText("")

        assert not any(window.rule_list.topLevelItem(index).isHidden() for index in range(total))
        assert window.rule_list._drag_enabled

    def test_adding_a_rule_clears_the_filter(self, parent):
        """
        新建规则时清掉搜索词

        新规则多半不符合当前筛选条件，而它马上就是选中项 —— 留着筛选，用户会对着
        一条列表里看不见的规则编辑
        """
        window = self._open(parent)
        window.editor.preview_timer.stop()

        window.search_box.setText("{collection_title}")
        window.on_add_rule()

        assert window.search_box.text() == ""
        assert not window.rule_list.topLevelItem(window.current_index).isHidden()

    def test_item_moved_syncs_the_working_copy(self, parent):
        """拖拽换位要把新顺序同步进工作副本 —— 它就是下载选项下拉框里的次序"""
        window = self._open(parent)
        window.editor.preview_timer.stop()

        first, second, third = (entry["id"] for entry in window.rule_data_list[:3])

        # 控件在 mouseMoveEvent 里已经换好了行，这里补上它随后发出的信号
        window.rule_list.insertTopLevelItem(2, window.rule_list.takeTopLevelItem(0))

        window.on_item_moved(0, 2)

        assert [entry["id"] for entry in window.rule_data_list[:3]] == [second, third, first]
        assert window.current_index == 2

    def test_switching_rows_without_editing_is_not_dirty(self, parent):
        """
        点开别的规则看看，不该被当成改动

        提交会把配置里的 int 类型换成 ConventionType 成员，两者相等 ——
        若在这里判成改动，用户什么都没做就会被问「是否丢弃修改」
        """
        window = self._open(parent)
        window.editor.preview_timer.stop()

        window.rule_list.setCurrentItem(window.rule_list.topLevelItem(1))
        window.rule_list.setCurrentItem(window.rule_list.topLevelItem(5))

        assert not window.dirty

    def test_item_moved_is_reverted_when_the_editor_is_invalid(self, parent):
        """编辑器里有非法内容时，整个拖拽要撤销 —— 数据与视图错位比拖不动糟得多"""
        window = self._open(parent)
        window.editor.preview_timer.stop()

        window.editor.rule_box.setText("<P{p:02d}-{leaf_title}")

        committed = window.rule_data_list[0]["rule"]
        item = window.rule_list.takeTopLevelItem(0)

        window.rule_list.insertTopLevelItem(2, item)

        window.on_item_moved(0, 2)

        assert window.rule_data_list[0]["rule"] == committed
        assert window.rule_list.topLevelItem(0) is item
        assert window.current_index == 0

    def test_restore_builtin_default_touches_only_that_rule(self, parent):
        """预设改坏了要能单独还原，不必连自己写的规则一起陪葬"""
        window = self._open(parent)
        window.editor.preview_timer.stop()

        original = window.rule_data_list[0]["rule"]

        window.editor.rule_box.setText("{leaf_title}/{leaf_title}")
        window.rule_list.setCurrentItem(window.rule_list.topLevelItem(1))

        window._append_rule({
            "id": "custom", "name": "副本", "type": 11,
            "rule": "{leaf_title}", "default": False
        })

        window.rule_list.setCurrentItem(window.rule_list.topLevelItem(0))
        window.on_restore_default_rule()

        assert window.rule_data_list[0]["rule"] == original
        assert window.editor.rule_box.text() == original
        assert window.rule_data_list[-1]["name"] == "副本", "自建规则不受影响"

    def test_left_column_does_not_overlap_at_minimum_size(self, parent):
        """工具栏、搜索框、规则列表三块叠在 300px 的左栏里，压到最小尺寸也不能重叠"""
        window = self._open(parent)

        parent.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        parent.resize(1060, 720)
        parent.show()

        window.resize(1060, 720)
        window.show()

        def top_of(widget):
            return widget.mapTo(window, widget.rect().topLeft()).y()

        assert window.command_bar.geometry().bottom() <= top_of(window.search_box)
        assert window.search_box.geometry().bottom() <= top_of(window.rule_list)

    def test_new_rule_seed_has_a_usable_variable_for_every_type(self, parent):
        """
        新规则的种子要在该类型下取得到值

        老写法一律套 {leaf_title}，而剧集与课程这两类的变量清单里没有它 ——
        新建出来的规则能通过校验，却渲染成一个字面量下划线，用户对着它还得自己
        猜这个类型能用哪些变量。这类「不报错但没用」的默认值最难被发现
        """
        from util.common.data import convention_type_map, VariableListFactory
        from util.common.data.naming_convention import SampleShape
        from util.format.rule_template import compile_rule

        window = self._open(parent)
        factory = VariableListFactory()

        for type_id in convention_type_map.values():
            seed = window._new_rule_seed(type_id)

            data = factory.build_variable_data(type_id, SampleShape.SINGLE)
            filled = [
                name for name in compile_rule(seed, True).field_names()
                if str(data.get(name, "")).strip()
            ]

            assert filled, f"类型 {type_id} 的种子规则里没有一个变量取得到值，预览会是一片下划线"

    def test_new_rule_follows_the_selected_type(self, parent):
        """正在给剧集写规则时点「添加」，得到的该是一条剧集规则"""
        window = self._open(parent)
        window.editor.preview_timer.stop()

        # 第 2 条是合集（type 13）
        window.rule_list.setCurrentItem(window.rule_list.topLevelItem(2))
        window.on_add_rule()

        assert window.rule_data_list[-1]["type"] == window.rule_data_list[2]["type"]
        # 名字存的是翻译键，换个界面语言不会把旧译名钉死在配置里
        assert window.rule_data_list[-1]["name"] == "NEW_RULE"

    def test_restore_is_unavailable_for_custom_rules(self, parent):
        """自建规则没有出厂值，菜单项该是灰的而不是点了没反应"""
        window = self._open(parent)
        window.editor.preview_timer.stop()

        assert window.get_builtin_default(window.rule_data_list[0]) is not None
        assert window.get_builtin_default({"id": "not-builtin", "name": "n"}) is None

        builtin_actions = window._build_context_menu().actions()

        assert builtin_actions[0].isEnabled(), "内置规则可以恢复"
        assert builtin_actions[-1].isEnabled(), "整表重置始终可用"

        window._append_rule({
            "id": "custom", "name": "副本", "type": 11,
            "rule": "{leaf_title}", "default": False
        })

        custom_actions = window._build_context_menu().actions()

        assert not custom_actions[0].isEnabled(), "自建规则没有出厂值可恢复"

    def test_dirty_is_computed_not_accumulated(self, parent):
        """
        脏不脏是算出来的，不是攒标志位攒出来的

        只改编辑器还没提交时不算脏（工作副本没动）；把工作副本改回去，它自己就
        变干净。攒标志位做不到后者 —— 用户改完又改回来、什么都没留下，关窗时
        却仍被问「是否丢弃修改」
        """
        from util.common.naming_rules import load_default_rules

        window = self._open(parent)
        window.editor.preview_timer.stop()

        assert not window.dirty

        window.editor.name_box.setText("我的规则")

        # 编辑器改了、但没提交，工作副本没动
        assert not window.dirty

        window.editor.on_discard()
        assert not window.dirty

        window.rule_data_list[0]["name"] = "改过的名字"
        assert window.dirty

        window.rule_data_list[0]["name"] = load_default_rules()[0]["name"]
        assert not window.dirty, "改回去就该自己变干净"
