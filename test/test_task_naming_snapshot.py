"""
命名规则快照（TaskInfo.Naming）—— 排队中的任务不该被后来的选择改写。

runtime.naming.target_rule_ids 是进程级全局，每次解析都会重置；而下载真正
开始后，_update_media_info() 拿到画质信息还要再格式化一次文件名。两者相遇
的后果是：任务 A 选了规则 X 进队列排队，用户接着解析视频 B 并选了规则 Y，
A 开始下载时文件名会按 Y 重算。

修法与 OptionsInfo 一致 —— 建任务时把规则**模板本身**固化进 TaskInfo。
存模板而不是 rule_id，是因为用户完全可能在排队期间编辑或删掉那条规则。
"""

from util.download.task.manager import TaskManager
from util.download.task.info import TaskInfo
from util.parse.episode.tree import Attribute
from util.common.enum import ConventionType
from util.common.runtime import runtime
from util.common.naming_rules import load_rules

from json import dumps, loads
import pytest


def freeze(task_info: TaskInfo, options: dict = None):
    # 名字重整后的私有方法，测试里直接调用即可
    TaskManager._TaskManager__freeze_naming_rule(None, task_info, options)


def update_file_name(task_info: TaskInfo):
    TaskManager._TaskManager__update_file_name_info(None, task_info)


def default_rule_id(type_id):
    for entry in load_rules():
        if entry["type"] == type_id and entry["default"]:
            return entry["id"]

    return None


def make_task(attribute: int, title: str = "标题"):
    task_info = TaskInfo()
    task_info.Episode.attribute = attribute
    task_info.Episode.leaf_title = title

    return task_info


@pytest.fixture(autouse = True)
def clean_runtime():
    runtime.naming.target_rule_ids = {}

    yield

    runtime.naming.target_rule_ids = {}


class TestDefaults:
    def test_new_task_has_no_snapshot(self):
        task_info = TaskInfo()

        assert task_info.Naming.rule is None
        assert task_info.Naming.rule_id is None
        assert task_info.Naming.type_id is None

    def test_legacy_record_without_naming_section(self):
        # 旧版本创建的任务，记录里根本没有 Naming 这一节
        task_info = TaskInfo()
        task_info.from_dict({"Basic": {"task_id": "x"}})

        assert task_info.Naming.rule is None

    def test_round_trip_through_json(self):
        # task.db 存的是 to_dict() 的整段 JSON，快照必须能原样往返
        task_info = make_task(Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)
        freeze(task_info)

        restored = TaskInfo()
        restored.from_dict(loads(dumps(task_info.to_dict())))

        assert restored.Naming.rule == task_info.Naming.rule
        assert restored.Naming.type_id == task_info.Naming.type_id


class TestFreezing:
    def test_falls_back_to_the_type_default(self):
        task_info = make_task(Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)
        freeze(task_info)

        assert task_info.Naming.type_id == ConventionType.NORMAL
        assert task_info.Naming.rule

    def test_uses_the_selected_rule(self):
        rule_id = default_rule_id(ConventionType.SPACE)

        task_info = make_task(Attribute.SPACE_BIT | Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)
        freeze(task_info, {"naming_rule_ids": {ConventionType.SPACE: rule_id}})

        assert task_info.Naming.rule_id == rule_id

    def test_options_override_global_state(self):
        runtime.naming.target_rule_ids = {ConventionType.NORMAL: "不存在的规则"}

        task_info = make_task(Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)
        freeze(task_info, {"naming_rule_ids": {}})

        # 查不到指定规则时回落该类型的默认规则，而不是抬手用全局状态
        assert task_info.Naming.rule


class TestRaceCondition:
    def test_queued_task_is_not_rewritten_by_a_later_choice(self):
        """本文件的核心用例：排队中的任务不受后续选择影响"""
        task_info = make_task(Attribute.VIDEO_BIT | Attribute.NORMAL_BIT, "视频标题")
        freeze(task_info)
        update_file_name(task_info)

        frozen_name = task_info.File.name
        frozen_folder = task_info.File.folder

        # 用户接着解析了别的链接，并选了另一条规则
        runtime.naming.target_rule_ids = {ConventionType.NORMAL: "另一条规则"}

        # 下载开始，_update_media_info 触发二次格式化
        update_file_name(task_info)

        assert task_info.File.name == frozen_name
        assert task_info.File.folder == frozen_folder


class TestHeterogeneousBatch:
    def test_each_item_uses_its_own_type_rule(self):
        # 界面上只为收藏夹指定了规则，剧集条目必须落到剧集自己的默认规则，
        # 绝不能套用收藏夹那条。
        #
        # 剧集那条用的是**解析器真实产出的**属性组合（favlist.py 对 ogv 条目
        # 同时打上 BANGUMI_BIT 与 FAVLIST_BIT）。曾经这里造的是裸 BANGUMI_BIT，
        # 现实中不存在，于是这条测试一直在替一个不成立的行为背书
        favorite_rule_id = default_rule_id(ConventionType.FAVORITE)
        options = {"naming_rule_ids": {ConventionType.FAVORITE: favorite_rule_id}}

        favorite = make_task(Attribute.FAVLIST_BIT | Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)
        bangumi = make_task(Attribute.FAVLIST_BIT | Attribute.BANGUMI_BIT | Attribute.NEED_PARSE_BIT)

        freeze(favorite, options)
        freeze(bangumi, options)

        assert favorite.Naming.type_id == ConventionType.FAVORITE
        assert bangumi.Naming.type_id == ConventionType.BANGUMI

        assert bangumi.Naming.rule_id is None
        assert bangumi.Naming.rule != favorite.Naming.rule


class TestEpisodeTitleMerge:
    """
    入口标签与稿件标题各走各的变量，不再互相覆盖

    二次解析产出的 related_titles 排在来源级 EpisodeData **之后**（见
    __update_episode_info 的合并顺序）。此前 {parent_title} 兼着「来源列表入口标签」
    与「稿件标题」两种含义，就是被这个顺序决定的：分P条目的稿件标题会把
    「稍后再看」这个入口标签盖掉，于是同一个变量在同一个位置有两种含义。

    入口标签挪进 {source_title} 后，两条路互不相干：related_titles 里从来不含
    source_title，合并顺序无需改动
    """

    @staticmethod
    def merge(episode_info: dict):
        class _Stub:
            # 只把标题里的非法字符换成下划线，与「取谁的标题」无关
            _TaskManager__filter_illegal_characters = staticmethod(lambda data: None)

        return TaskManager._TaskManager__update_episode_info(_Stub(), episode_info, 1)

    def test_entry_label_survives_a_multi_part_reparse(self):
        from util.parse.episode.tree import EpisodeData

        episode_id = EpisodeData.add_episode()

        try:
            # 来源解析器只写入口标签；稿件标题由二次解析的 related_titles 给出
            EpisodeData.get_episode_data(episode_id)["source_title"] = "稍后再看"

            merged = self.merge({
                "episode_id": episode_id,
                "title": "04 アルカテイル",
                "related_titles": {"parent_title": "【KEY社20周年音乐专辑】Key BEST SELECTION"},
            })

            assert merged["source_title"] == "稍后再看"
            assert merged["parent_title"] == "【KEY社20周年音乐专辑】Key BEST SELECTION"

        finally:
            EpisodeData.table.pop(episode_id, None)


class TestFailureHandling:
    def test_unrenderable_rule_raises_instead_of_vanishing(self):
        # 以前是 Path(None) 抛 TypeError 被 create() 外层吞掉，条目静默消失，
        # 用户只看到下载数量对不上
        task_info = make_task(Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)
        task_info.Naming.rule = "{根本不存在的变量}"

        with pytest.raises(ValueError):
            update_file_name(task_info)
