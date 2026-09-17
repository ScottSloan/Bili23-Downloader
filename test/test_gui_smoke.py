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

    def test_editor_does_not_overlap_at_minimum_height(self, parent):
        """
        窗口压到最小尺寸时右栏不能重叠

        右栏把可视化编辑器、预览、变量表叠在一栏里，各块的最小高度之和一旦超过
        窗口能给的，Qt 就不再理会最小值继续压，带硬性下限的滚动区会画到分配区
        之外、直接盖住「文件名」那一行。以后往这一栏里再加东西，先看这条用例。
        """
        from gui.dialog.setting.edit_rule import EditRuleDialog
        from util.common.enum import ConventionType

        panel = EditRuleDialog(parent)
        panel.load({
            "id": "x", "name": "n", "type": ConventionType.FAVORITE,
            "rule": "{favorites_owner_id}_{favorites_owner}/{favorites_name}/{parent_title}/<P{p:02d}->{leaf_title}",
            "default": False
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
