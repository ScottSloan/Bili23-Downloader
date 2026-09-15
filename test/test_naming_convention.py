"""
util/common/data/naming_convention.py —— 变量清单与预览样本数据。

本文件最重要的一条是 test_key_space_matches_runtime。

编辑器曾经拿「按规则类型裁剪过的变量清单」去当 str.format 的 kwargs，于是
个人空间下写 {parent_title} 会抛 KeyError，被 format() 的 except 吞掉，界面
报「命名规则无效」拒绝保存 —— 而同一条规则在运行期完全正常，因为
get_variable_data_from_task_info 是无条件填齐全部键的。GitHub issue #461
的用户就撞在这堵墙上。

按类型裁剪从此只是界面上的「推荐」，键空间必须恒等于运行期。
"""

from util.common.data.naming_convention import (
    VariableListFactory, SampleShape, SUPPORTED_SHAPES
)
from util.common.enum import ConventionType, VariableType
from util.common.translator import Translator

from util.format.file_name import FileNameFormatter
from util.download.task.info import TaskInfo

import pytest


@pytest.fixture(scope = "module")
def factory():
    return VariableListFactory()


@pytest.fixture(scope = "module")
def runtime_keys():
    return set(FileNameFormatter().get_variable_data_from_task_info(TaskInfo()))


class TestKeySpace:
    @pytest.mark.parametrize("type", list(ConventionType))
    @pytest.mark.parametrize("shape", list(SampleShape))
    def test_key_space_matches_runtime(self, factory, runtime_keys, type, shape):
        assert set(factory.build_variable_data(type, shape)) == runtime_keys

    @pytest.mark.parametrize("type", list(ConventionType))
    def test_full_list_covers_the_whole_key_space(self, factory, runtime_keys, type):
        assert {entry["name"] for entry in factory.build(type)} == runtime_keys


class TestVariableList:
    @pytest.mark.parametrize("type", [
        ConventionType.SPACE,
        ConventionType.FAVORITE,
        ConventionType.HISTORY,
        ConventionType.WATCH_LATER,
    ])
    def test_source_types_expose_structural_variables(self, factory, type):
        # 来源类规则也要能用分P、合集的变量 —— 一次解析里什么形态都可能有
        names = {entry["name"] for entry in factory.build(type)}

        assert {"parent_title", "p", "collection_title", "section_title"} <= names

    def test_primary_list_is_unchanged(self, factory):
        # full = False 必须原样给出类型专属清单，顺序也不能被打乱
        primary = factory.build(ConventionType.PART, full = False)

        assert [entry["name"] for entry in primary] == [
            "pub_time", "pub_ts", "create_time", "create_ts", "number",
            "uploader", "uploader_uid", "video_quality", "audio_quality", "video_codec",
            "parent_title", "p", "leaf_title", "aid", "bvid", "cid",
        ]

    def test_groups_are_tagged(self, factory):
        entries = factory.build(ConventionType.SPACE)
        groups = {entry["name"]: entry["group"] for entry in entries}

        assert groups["space_owner"] == "PRIMARY"
        assert groups["p"] == "MORE"

    @pytest.mark.parametrize("type", list(ConventionType))
    def test_every_entry_carries_a_type(self, factory, type):
        # 可视化编辑器据此决定格式项的形态
        for entry in factory.build(type):
            assert isinstance(entry["type"], VariableType)

    def test_number_like_variables_typed_as_number(self, factory):
        types = {entry["name"]: entry["type"] for entry in factory.build(ConventionType.BANGUMI)}

        assert types["episode_number"] == VariableType.NUMBER
        assert types["pub_time"] == VariableType.DATETIME
        assert types["leaf_title"] == VariableType.TEXT

    @pytest.mark.parametrize("type", list(ConventionType))
    def test_descriptions_are_translatable(self, factory, type):
        descriptions = Translator.VARIABLE_DESCRIPTION()

        for entry in factory.build(type):
            assert entry["description"] in descriptions, entry["name"]


class TestSampleData:
    def test_shapes_are_declared_for_every_type(self):
        assert set(SUPPORTED_SHAPES) == set(ConventionType)

    def test_single_shape_clears_structural_values(self, factory):
        data = factory.build_variable_data(ConventionType.SPACE, SampleShape.SINGLE)

        assert data["parent_title"] == ""
        assert data["p"] == 0

    def test_multi_shape_fills_structural_values(self, factory):
        data = factory.build_variable_data(ConventionType.SPACE, SampleShape.MULTI)

        assert data["parent_title"]
        assert data["p"] == 4

    def test_label_parent_title_kept_for_single(self, factory):
        # 历史记录单个条目的 parent_title 是入口标签，不能被形态覆盖清空
        data = factory.build_variable_data(ConventionType.HISTORY, SampleShape.SINGLE)

        assert data["parent_title"] == "历史记录"

    def test_label_parent_title_replaced_for_multi(self, factory):
        # 分P条目经二次解析后，related_titles 会盖掉入口标签，
        # 此时 parent_title 确实是稿件标题
        data = factory.build_variable_data(ConventionType.HISTORY, SampleShape.MULTI)

        assert data["parent_title"] != "历史记录"

    def test_numeric_sentinels_survive_number_formatting(self, factory):
        # 哨兵若是空串，{aid:>12} 这类写法会在预览里抛 ValueError，
        # 编辑器便报「规则无效」—— 正是 #461 那类假阴性
        formatter = FileNameFormatter()
        formatter.set_variable_data(factory.build_variable_data(ConventionType.SPACE, SampleShape.SINGLE))
        formatter.set_rule("{aid:>12}/{season_number:02d}/{pub_time:%Y-%m}")

        assert formatter.format() is not None

    def test_datetime_variables_are_datetime(self, factory):
        data = factory.build_variable_data(ConventionType.NORMAL, SampleShape.SINGLE)

        for name in ("pub_time", "create_time", "fav_time", "last_watched_time"):
            assert hasattr(data[name], "strftime"), name


class TestIssue461:
    """原 bug 的直接复现：个人空间下的分P规则曾经存不下来"""

    RULE = "{space_owner}/{parent_title}/<P{p:02d}->{leaf_title}"

    def _render(self, factory, shape):
        formatter = FileNameFormatter()
        formatter.set_variable_data(factory.build_variable_data(ConventionType.SPACE, shape))
        formatter.set_rule(self.RULE)

        return formatter.format()

    def test_preview_no_longer_rejects_structural_variables(self, factory):
        assert self._render(factory, SampleShape.MULTI) is not None

    def test_single_and_multi_render_differently(self, factory):
        single = self._render(factory, SampleShape.SINGLE)
        multi = self._render(factory, SampleShape.MULTI)

        # 单P不该留下 P00- 这样的残缺前缀
        assert "P0" not in single
        assert "P04-" in multi
