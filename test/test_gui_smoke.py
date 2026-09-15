"""
GUI 层的构造冒烟测试。

这一层此前零覆盖，而它恰恰是最容易被"清理未使用的导入"误伤的地方：
删掉一个只在某个分支里用到的符号，导入依然成功，直到用户点开那个对话框
才会 NameError。这里把改动面较大的控件与对话框实际构造一遍。

不断言外观，只断言"能造出来且不抛异常" —— 目标是挡住导入级与初始化级的回归，
而不是做视觉测试。
"""

from PySide6.QtWidgets import QApplication, QWidget

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
         "ChapterSettingCard", "MetadataSettingCard", "DownloadFormatCard"],
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
