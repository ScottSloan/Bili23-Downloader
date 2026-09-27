"""
util/parse/episode/tree.py —— 解析结果的树模型与全局剧集数据表。

两块都是易碎且难以人工复现的逻辑：

* 勾选状态的双向传递：向下全选/全不选、向上三态汇总。表现为"点了父节点
  子项没跟着变"或"取消一个子项父节点还是全选状态"。

* EpisodeData 的并发清理：解析界面与分P对话框可以同时存活，两边解析各跑
  各的线程。clear_cache() 若在并发期间真的清了表，另一边创建下载任务时
  拿到空字典，UP 主、简介等附加信息全部丢失 —— 而这只在特定时序下出现。
"""

from PySide6.QtCore import Qt

from util.parse.episode.tree import TreeItem, EpisodeData, Attribute

from threading import Barrier, Thread
import pytest


def build_tree(children_count: int = 3):
    """一个根节点 + 若干叶子，模拟最常见的「合集 → 分P」结构"""
    root = TreeItem({"title": "root"})
    root.set_attribute(Attribute.TREE_NODE_BIT)

    for i in range(children_count):
        child = TreeItem({"title": f"child-{i}"})
        child.set_attribute(Attribute.VIDEO_BIT)
        root.add_child(child)

    return root


class TestCheckStatePropagation:
    def test_check_parent_checks_all_children(self):
        root = build_tree()
        root.set_checked_state(Qt.CheckState.Checked)

        assert all(c.checked == Qt.CheckState.Checked for c in root.children)

    def test_uncheck_parent_unchecks_all_children(self):
        root = build_tree()
        root.set_checked_state(Qt.CheckState.Checked)
        root.set_checked_state(Qt.CheckState.Unchecked)

        assert all(c.checked == Qt.CheckState.Unchecked for c in root.children)

    def test_partial_child_selection_makes_parent_partially_checked(self):
        root = build_tree()
        root.children[0].set_checked_state(Qt.CheckState.Checked)

        assert root.checked == Qt.CheckState.PartiallyChecked

    def test_all_children_checked_makes_parent_checked(self):
        root = build_tree()

        for child in root.children:
            child.set_checked_state(Qt.CheckState.Checked)

        assert root.checked == Qt.CheckState.Checked

    def test_unchecking_one_child_downgrades_parent(self):
        root = build_tree()
        root.set_checked_state(Qt.CheckState.Checked)
        root.children[0].set_checked_state(Qt.CheckState.Unchecked)

        assert root.checked == Qt.CheckState.PartiallyChecked

    def test_propagation_crosses_multiple_levels(self):
        grandparent = TreeItem({"title": "gp"})
        parent = build_tree()
        grandparent.add_child(parent)

        parent.children[0].set_checked_state(Qt.CheckState.Checked)

        assert grandparent.checked == Qt.CheckState.PartiallyChecked

        for child in parent.children:
            child.set_checked_state(Qt.CheckState.Checked)

        assert grandparent.checked == Qt.CheckState.Checked


class TestRefreshCheckState:
    def test_matches_incremental_propagation(self):
        # refresh_check_state 是 Shift 范围勾选用的批量版本，
        # 结果必须与逐项 set_checked_state 完全一致，否则批量选择后父节点状态会错
        root = build_tree(4)

        for child in root.children[:2]:
            child.checked = Qt.CheckState.Checked

        assert root.refresh_check_state() == Qt.CheckState.PartiallyChecked

        for child in root.children:
            child.checked = Qt.CheckState.Checked

        assert root.refresh_check_state() == Qt.CheckState.Checked


class TestCollectChildren:
    def test_checked_children_exclude_tree_nodes(self):
        root = build_tree()
        root.set_checked_state(Qt.CheckState.Checked)

        # 根节点自身带 TREE_NODE_BIT，不应出现在待下载列表里
        assert len(root.get_all_checked_children()) == 3

    def test_get_all_leaves(self):
        root = build_tree()

        assert len(root.get_all_leaves()) == 3


class TestEpisodeDataConcurrency:
    @pytest.fixture(autouse = True)
    def reset(self):
        EpisodeData.table.clear()
        EpisodeData._active_parsers = 0

        yield

        EpisodeData.table.clear()
        EpisodeData._active_parsers = 0

    def test_clear_cache_works_when_idle(self):
        EpisodeData.add_episode()
        EpisodeData.clear_cache()

        assert EpisodeData.table == {}

    def test_clear_cache_skipped_while_parsing(self):
        # 有解析在进行时清理必须被跳过，否则会擦掉对方刚写进去的数据
        with EpisodeData.parsing():
            episode_id = EpisodeData.add_episode()
            EpisodeData.clear_cache()

            assert episode_id in EpisodeData.table

    def test_nested_parsing_restores_counter(self):
        with EpisodeData.parsing():
            with EpisodeData.parsing(clear_cache = False):
                assert EpisodeData._active_parsers == 2

            assert EpisodeData._active_parsers == 1

        assert EpisodeData._active_parsers == 0

    def test_counter_restored_on_exception(self):
        with pytest.raises(RuntimeError):
            with EpisodeData.parsing():
                raise RuntimeError("解析失败")

        # 计数没回落的话，此后 clear_cache 会永久失效，数据表只增不减
        assert EpisodeData._active_parsers == 0

    def test_concurrent_parsers_do_not_erase_each_other(self):
        """
        复现注释中描述的竞态：两个线程同时解析，后进入的那个不得清掉先进入者的数据。

        用 Barrier 强制两个线程在「已写入数据」这一点上会合，再让第二个线程
        带着 clear_cache=True 进入 parsing()，这正是危险时序。
        """
        barrier = Barrier(2)
        written: dict[str, str] = {}
        errors: list[Exception] = []

        def parse(name: str):
            try:
                with EpisodeData.parsing():
                    episode_id = EpisodeData.add_episode()
                    EpisodeData.get_episode_data(episode_id)["owner"] = name
                    written[name] = episode_id

                    # 两个线程都完成写入后才继续，确保清理时机落在对方的解析区间内
                    barrier.wait(timeout = 5)

            except Exception as exc:
                errors.append(exc)

        threads = [Thread(target = parse, args = (f"parser-{i}",)) for i in range(2)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout = 10)

        assert not errors, errors

        # 两份数据都必须留存，且内容没有串台
        for name, episode_id in written.items():
            assert EpisodeData.get_episode_data(episode_id).get("owner") == name
