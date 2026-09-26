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
    VariableListFactory, SampleShape, SUPPORTED_SHAPES, MIXED_ENTRY_TYPES
)
from util.common.enum import ConventionType, VariableType
from util.common.translator import Translator

from util.parse.episode.tree import Attribute

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

    def test_parent_title_is_structural_only(self, factory):
        """
        {parent_title} 从 2.20.0 起只表示稿件标题

        此前它兼着「来源列表入口标签」这一层含义（历史记录的单P条目上是
        「历史记录」），而分P与合集条目上又是稿件标题 —— 同一个变量在同一位置
        有两种含义。入口标签已挪进 {source_title}
        """
        single = factory.build_variable_data(ConventionType.HISTORY, SampleShape.SINGLE)
        multi = factory.build_variable_data(ConventionType.HISTORY, SampleShape.MULTI)

        assert single["parent_title"] == ""
        assert multi["parent_title"]

    def test_source_title_survives_every_shape(self, factory):
        # 入口标签与条目形态无关：单P、分P、合集条目都在同一个来源列表里
        for shape in SampleShape:
            data = factory.build_variable_data(ConventionType.HISTORY, shape)

            assert data["source_title"] == "历史记录", shape

    def test_source_title_is_empty_outside_the_source_types(self, factory):
        # 收藏夹/个人空间/合集各有专属变量（favorites_name、space_owner、
        # collection_title），不重复给一个 source_title
        for type_id in (ConventionType.NORMAL, ConventionType.FAVORITE, ConventionType.COLLECTION):
            data = factory.build_variable_data(type_id, SampleShape.SINGLE)

            assert data["source_title"] == "", type_id

    def test_numeric_sentinels_survive_number_formatting(self, factory):
        # 哨兵若是空串，{aid:>12} 这类写法会在预览里抛 ValueError，
        # 编辑器便报「规则无效」—— 正是 #461 那类假阴性
        formatter = FileNameFormatter()
        formatter.set_variable_data(factory.build_variable_data(ConventionType.SPACE, SampleShape.SINGLE))
        formatter.set_rule("{aid:>12}/{season_number:02d}/{pub_time:%Y-%m}")

        assert formatter.format() is not None

    def test_collection_shape_keeps_the_collection_title(self, factory):
        """
        合集条目的 collection_title 是归属信息，不是形态信息

        形态覆盖里会清空它（来源列表里的分P稿件不在任何合集里），但合集条目
        自己就住在合集里，清空等于告诉用户 {collection_title} 取不到值
        """
        single = factory.build_variable_data(ConventionType.COLLECTION, SampleShape.SINGLE)

        assert single["collection_title"]
        assert single["leaf_title"]

        # 单P条目没有稿件标题、页码与章节，这几项该空 —— 两行样本的差别正在这里
        assert single["parent_title"] == ""
        assert single["p"] == 0
        assert single["section_title"] == ""

    def test_collection_shapes_differ(self, factory):
        single = factory.build_variable_data(ConventionType.COLLECTION, SampleShape.SINGLE)
        full = factory.build_variable_data(ConventionType.COLLECTION, SampleShape.COLLECTION)

        assert single["collection_title"] == full["collection_title"]
        assert single["leaf_title"] != full["leaf_title"]

    def test_datetime_variables_are_datetime(self, factory):
        data = factory.build_variable_data(ConventionType.NORMAL, SampleShape.SINGLE)

        for name in ("pub_time", "create_time", "fav_time", "last_watched_time"):
            assert hasattr(data[name], "strftime"), name


class TestMixedEntryTypes:
    """
    MIXED_ENTRY_TYPES 是给编辑器预览用的声明

    预览多列的那一行据此告诉用户「影视、课程条目不归当前这条规则管」，写错了
    界面就会替一个错误的行为背书 —— 而它只是一张手写的表，没有任何东西保证
    它与 FileNameFormatter 里那条优先级规则一致，所以在这里钉住。
    """

    SOURCE_BITS = {
        ConventionType.FAVORITE: Attribute.FAVLIST_BIT,
        ConventionType.SPACE: Attribute.SPACE_BIT,
        ConventionType.HISTORY: Attribute.HISTORY_BIT,
        ConventionType.WATCH_LATER: Attribute.WATCH_LATER_BIT,
    }

    KIND_BITS = {
        ConventionType.BANGUMI: Attribute.BANGUMI_BIT,
        ConventionType.CHEESE: Attribute.CHEESE_BIT,
    }

    def test_declared_mixed_entries_match_the_type_mapping(self):
        formatter = FileNameFormatter()

        for source, mixed in MIXED_ENTRY_TYPES.items():
            # 来源类型不在 SOURCE_BITS 里时这里会 KeyError —— 表里冒出一个
            # 没人认识的来源类型本该让测试挂掉，而不是静默跳过
            for kind in mixed:
                attribute = self.SOURCE_BITS[source] | self.KIND_BITS[kind] | Attribute.NEED_PARSE_BIT

                assert formatter.get_type_id_from_attribute(attribute) == kind, (source, kind)

    def test_only_multi_shape_types_declare_mixed_entries(self):
        # 混进别的类型是对「来源类列表」才成立的说法 —— 只有装着多种形态条目的
        # 类型才会同时装着投稿视频与影视、课程。只声明一种形态的类型（单个视频、
        # 音乐、影视自己）不该出现在这张表里
        for type_id in MIXED_ENTRY_TYPES:
            assert len(SUPPORTED_SHAPES[type_id]) > 1, type_id


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
