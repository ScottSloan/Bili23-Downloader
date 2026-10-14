"""
解析列表的"已下载"标记（util/parse/episode/download_history.py）。

标记与创建任务时的重复下载判定必须是同一个口径：列表上打了绿色对勾的条目，
点下载时必然被判为重复，反之亦然。两边各算各的 hash 一旦分叉，界面不会报任何错，
只是对勾悄悄失效（或者误标），因此这里把"解析端算出的 hash 与入库端一致"钉住。
"""

from util.parse.episode.tree import Attribute, TreeItem

import pytest


@pytest.fixture
def task_manager():
    # conftest 已把 AppDataLocation 重定向到 qttest，这里建的库在隔离目录下
    from util.download.task.manager import TaskManager

    manager = TaskManager()

    # 隔离目录在整个测试进程内共用同一个 task.db，别的用例留下的记录会串进来
    manager.db_manager.execute_batch([
        ("DELETE FROM download_task", ()),
        ("DELETE FROM completed_task", ())
    ])

    yield manager

    manager._update_executor.submit(manager.db_manager.close_connection)

    manager._update_executor.shutdown(wait = True)
    manager._cancel_executor.shutdown(wait = True)

    manager.db_manager.close_connection()


@pytest.fixture
def mark_enabled():
    """设置项开关，用例结束后恢复原值（config.set 会立即落盘）"""
    from util.common.config import config

    saved = config.get(config.parse_list_mark_downloaded)

    def set_enabled(value: bool):
        config.set(config.parse_list_mark_downloaded, value)

    set_enabled(True)

    yield set_enabled

    config.set(config.parse_list_mark_downloaded, saved)


@pytest.fixture
def mark(task_manager, monkeypatch, mark_enabled):
    from util.parse.episode import download_history

    # 换成隔离库上的实例，避免读到进程级单例背后的那份库
    monkeypatch.setattr(download_history, "task_manager", task_manager)

    return download_history.mark_download_history


def make_item(attribute: int, **data):
    item = TreeItem({"title": data.get("bvid", "item"), **data})
    item.set_attribute(attribute)

    return item


def make_tree(items: list):
    node = TreeItem({"title": "根节点"})
    node.set_attribute(Attribute.TREE_NODE_BIT)

    for item in items:
        node.add_child(item)

    return node


def store(task_manager, item: TreeItem, task_id: str, completed: bool = False):
    """按入库端的方式把条目写进下载记录"""
    from util.download.task.info import TaskInfo

    task_info = TaskInfo()
    task_info.Basic.task_id = task_id
    task_info.Basic.created_time = 1_700_000_000
    task_info.Basic.completed_time = 1_700_000_000
    task_info.Episode.from_dict(item.to_dict())

    task_manager.db_manager.add_tasks([task_info], completed = completed)


class TestHashConsistency:
    @pytest.mark.parametrize("attribute, data", [
        (Attribute.VIDEO_BIT | Attribute.PART_BIT, {"aid": 1, "bvid": "BV1xx", "cid": 11}),
        (Attribute.BANGUMI_BIT, {"aid": 2, "bvid": "BV2xx", "cid": 22, "ep_id": 222}),
        (Attribute.CHEESE_BIT, {"aid": 3, "cid": 33, "ep_id": 333}),
        (Attribute.AUDIO_BIT, {"sid": 4}),
        (Attribute.LESSON_BIT, {"course_id": 5, "lesson_id": 55, "item_id": 555, "section_id": 5555}),
    ])
    def test_parse_side_hash_matches_stored_hash(self, task_manager, attribute, data):
        from util.download.task.hash_id import calc_episode_hash_id
        from util.download.task.info import TaskInfo

        item = make_item(attribute, **data)

        task_info = TaskInfo()
        task_info.Basic.task_id = "consistency"
        task_info.Episode.from_dict(item.to_dict())

        assert calc_episode_hash_id(item.to_dict()) == task_manager.db_manager._calc_hash_id(task_info)


class TestFilterExistingHashIds:
    def test_covers_both_tables(self, task_manager):
        from util.download.task.hash_id import calc_episode_hash_id

        queued = make_item(Attribute.VIDEO_BIT, aid = 1, bvid = "BV1", cid = 1)
        done = make_item(Attribute.VIDEO_BIT, aid = 2, bvid = "BV2", cid = 2)
        never = make_item(Attribute.VIDEO_BIT, aid = 3, bvid = "BV3", cid = 3)

        store(task_manager, queued, "queued")
        store(task_manager, done, "done", completed = True)

        hashes = {name: calc_episode_hash_id(item.to_dict()) for name, item in (("queued", queued), ("done", done), ("never", never))}

        assert task_manager.db_manager.filter_existing_hash_ids(hashes.values()) == {hashes["queued"], hashes["done"]}

    def test_large_input_is_split_into_batches(self, task_manager):
        from util.download.task.hash_id import calc_episode_hash_id

        # 落在第二批里的那一条也必须查得到
        target = make_item(Attribute.VIDEO_BIT, aid = 999, bvid = "BV999", cid = 999)
        store(task_manager, target, "target", completed = True)

        target_hash = calc_episode_hash_id(target.to_dict())
        hash_ids = [f"missing-{i}" for i in range(450)] + [target_hash]

        assert task_manager.db_manager.filter_existing_hash_ids(hash_ids) == {target_hash}

    def test_empty_input(self, task_manager):
        assert task_manager.db_manager.filter_existing_hash_ids([]) == set()


class TestMarkDownloadHistory:
    def test_marks_only_items_in_history(self, task_manager, mark):
        downloaded = make_item(Attribute.VIDEO_BIT, aid = 1, bvid = "BV1", cid = 1)
        fresh = make_item(Attribute.VIDEO_BIT, aid = 2, bvid = "BV2", cid = 2)

        store(task_manager, downloaded, "downloaded", completed = True)

        root = make_tree([downloaded, fresh])
        mark([root])

        assert downloaded.in_download_history
        assert not fresh.in_download_history
        # 树节点本身不参与判定
        assert not root.in_download_history
        # 与"本次会话已提交下载"是两回事，不能顺带改动
        assert not downloaded.downloaded

    def test_other_parts_of_the_same_video_are_not_marked(self, task_manager, mark):
        # 同一视频的分P共享 aid / bvid，只有 cid 不同，只下过 P1 不能把 P2 也标上
        p1 = make_item(Attribute.VIDEO_BIT | Attribute.PART_BIT, aid = 1, bvid = "BV1", cid = 101)
        p2 = make_item(Attribute.VIDEO_BIT | Attribute.PART_BIT, aid = 1, bvid = "BV1", cid = 102)

        store(task_manager, p1, "p1")

        mark([make_tree([p1, p2])])

        assert p1.in_download_history
        assert not p2.in_download_history

    def test_need_parse_items_are_skipped_by_hash(self, task_manager, mark, monkeypatch):
        # 需要二次解析的条目缺少 cid，算出的 hash 与入库时的对不上，不能拿去按 hash 查
        item = make_item(Attribute.VIDEO_BIT | Attribute.FAVLIST_BIT | Attribute.NEED_PARSE_BIT, bvid = "BV1")

        queried = []
        monkeypatch.setattr(task_manager.db_manager, "filter_existing_hash_ids", lambda hash_ids: queried.append(list(hash_ids)) or set())

        mark([make_tree([item])])

        assert queried == []

    def test_unidentifiable_items_are_skipped(self, task_manager, mark, monkeypatch):
        # 没有任何形态位的条目落在兜底分支，解析端彼此会算出同一个 hash，查了只会误报
        item = make_item(0, aid = 1)

        queried = []
        monkeypatch.setattr(task_manager.db_manager, "filter_existing_hash_ids", lambda hash_ids: queried.append(list(hash_ids)) or set())

        mark([make_tree([item])])

        assert queried == []
        assert not item.in_download_history

    def test_disabled_skips_query(self, task_manager, mark, mark_enabled, monkeypatch):
        item = make_item(Attribute.VIDEO_BIT, aid = 1, bvid = "BV1", cid = 1)

        store(task_manager, item, "disabled", completed = True)

        queried = []
        monkeypatch.setattr(task_manager.db_manager, "filter_existing_hash_ids", lambda hash_ids: queried.append(list(hash_ids)) or set())

        mark_enabled(False)
        mark([make_tree([item])])

        # 关闭时连数据库都不碰
        assert queried == []
        assert not item.in_download_history

    def test_database_error_does_not_break_parsing(self, task_manager, mark, monkeypatch, caplog):
        item = make_item(Attribute.VIDEO_BIT, aid = 1, bvid = "BV1", cid = 1)

        def boom(_):
            raise RuntimeError("database is locked")

        monkeypatch.setattr(task_manager.db_manager, "filter_existing_hash_ids", boom)

        mark([make_tree([item])])

        assert not item.in_download_history
        assert "查询下载记录失败" in caplog.text


@pytest.fixture(scope = "module")
def app():
    from PySide6.QtWidgets import QApplication

    instance = QApplication.instance() or QApplication([])

    import res.resources_rc   # noqa: F401  图标由此注册

    return instance


def store_parts(task_manager, bvid: str, cids: list, completed: bool = True):
    """模拟二次解析：为稿件的各分P分别建任务"""
    for cid in cids:
        part = make_item(Attribute.VIDEO_BIT | Attribute.FAVLIST_BIT | Attribute.PART_BIT, aid = 1, bvid = bvid, cid = cid)

        store(task_manager, part, f"{bvid}-{cid}", completed = completed)


def make_reparse_item(bvid: str, page_count: int = 0, attribute = Attribute.VIDEO_BIT | Attribute.FAVLIST_BIT):
    item = TreeItem({"title": bvid, "bvid": bvid, "page_count": page_count})
    item.set_attribute(attribute | Attribute.NEED_PARSE_BIT)

    return item


class TestMarkByBvid:
    def test_matches_by_bvid_across_both_tables(self, task_manager, mark):
        store_parts(task_manager, "BVdone", [1], completed = True)
        store_parts(task_manager, "BVqueued", [2], completed = False)

        done = make_reparse_item("BVdone")
        queued = make_reparse_item("BVqueued")
        fresh = make_reparse_item("BVfresh")

        mark([make_tree([done, queued, fresh])])

        assert done.in_download_history
        assert queued.in_download_history
        assert not fresh.in_download_history

    def test_partially_downloaded_is_not_marked_when_page_count_known(self, task_manager, mark):
        # 收藏夹给出了分P总数：3P 只下了 2P，不打勾
        store_parts(task_manager, "BVpart", [1, 2])
        store_parts(task_manager, "BVfull", [1, 2, 3])

        part = make_reparse_item("BVpart", page_count = 3)
        full = make_reparse_item("BVfull", page_count = 3)

        mark([make_tree([part, full])])

        assert not part.in_download_history
        assert full.in_download_history

    def test_same_part_downloaded_twice_counts_once(self, task_manager, mark):
        # 同一分P重复下载过（例如重复下载设置为继续），不能凑数成"全部下载"
        store_parts(task_manager, "BVdup", [1], completed = True)
        store_parts(task_manager, "BVdup", [1], completed = False)

        item = make_reparse_item("BVdup", page_count = 2)

        mark([make_tree([item])])

        assert not item.in_download_history

    def test_unknown_page_count_marks_on_any_record(self, task_manager, mark):
        # 个人空间、稍后再看等来源拿不到分P总数，有记录即视为下载过
        store_parts(task_manager, "BVspace", [1])

        item = make_reparse_item("BVspace", attribute = Attribute.VIDEO_BIT | Attribute.SPACE_BIT)

        mark([make_tree([item])])

        assert item.in_download_history

    @pytest.mark.parametrize("attribute", [
        Attribute.BANGUMI_BIT | Attribute.FAVLIST_BIT,
        Attribute.CHEESE_BIT | Attribute.SPACE_BIT,
    ], ids = ["bangumi", "cheese"])
    def test_bangumi_and_cheese_are_skipped(self, task_manager, mark, attribute):
        # 番剧按 ep_id 取单集、课程整季下载，条目上的 bvid 对应不到具体任务
        store_parts(task_manager, "BVother", [1])

        item = make_reparse_item("BVother", attribute = attribute)

        mark([make_tree([item])])

        assert not item.in_download_history

    def test_bvid_query_failure_keeps_hash_marks(self, task_manager, mark, monkeypatch, caplog):
        direct = make_item(Attribute.VIDEO_BIT, aid = 1, bvid = "BVdirect", cid = 1)
        store(task_manager, direct, "direct", completed = True)

        def boom(_):
            raise RuntimeError("no such function: json_extract")

        monkeypatch.setattr(task_manager.db_manager, "count_parts_by_bvid", boom)

        reparse = make_reparse_item("BVdirect")

        mark([make_tree([direct, reparse])])

        assert direct.in_download_history
        assert not reparse.in_download_history
        assert "按 bvid 查询下载记录失败" in caplog.text

    def test_query_uses_bvid_index(self, task_manager):
        # 查询里的表达式必须与建索引时逐字一致，否则静默退化为全表扫描、逐行解析 JSON
        plan = task_manager.db_manager.query("""
            EXPLAIN QUERY PLAN
            SELECT 1 FROM completed_task WHERE json_extract("data", '$.Episode.bvid') IN (?)
        """, ("BV1",))

        assert any("idx_completed_task_bvid" in row[-1] for row in plan)

    def test_large_input_is_split_into_batches(self, task_manager):
        store_parts(task_manager, "BVtarget", [1, 2])

        bvids = [f"BVmissing{i}" for i in range(450)] + ["BVtarget"]

        assert task_manager.db_manager.count_parts_by_bvid(bvids) == {"BVtarget": 2}


class TestParseModelDecoration:
    @staticmethod
    def _make_model():
        from PySide6.QtCore import QModelIndex

        from gui.component.parse_list.model import ParseModel

        history = make_item(Attribute.VIDEO_BIT, bvid = "BV1")
        history.in_download_history = True
        fresh = make_item(Attribute.VIDEO_BIT, bvid = "BV2")

        root = TreeItem({})
        root.add_child(make_tree([history, fresh]))

        model = ParseModel()
        model.beginResetModel()
        model.root_node = root
        model.endResetModel()

        return model, model.index(0, 0, QModelIndex())

    def test_disabled_hides_icon_and_placeholder(self, app, mark_enabled):
        from PySide6.QtCore import Qt

        from util.common.signal_bus import signal_bus

        model, parent = self._make_model()
        title_column = model._title_column
        role = Qt.ItemDataRole.DecorationRole

        assert model.index(0, title_column, parent).data(role) is not None

        # 与设置对话框保存时的路径一致：改配置后发 update_column_settings
        mark_enabled(False)
        signal_bus.parse.update_column_settings.emit()

        # 已解析出的对勾立即隐藏，占位也一并去掉，标题回到原来的位置
        assert model.index(0, title_column, parent).data(role) is None
        assert model.index(1, title_column, parent).data(role) is None

    def test_icon_only_on_title_column_of_history_items(self, app, mark_enabled):
        from PySide6.QtCore import QSize, Qt
        from PySide6.QtGui import QIcon

        model, parent = self._make_model()
        title_column = model._title_column

        assert title_column >= 0

        role = Qt.ItemDataRole.DecorationRole

        history_icon = model.index(0, title_column, parent).data(role)
        fresh_icon = model.index(1, title_column, parent).data(role)

        assert isinstance(history_icon, QIcon)
        # 没有下载记录的行也要返回图标占位，否则标题会与带对勾的行错开
        assert isinstance(fresh_icon, QIcon)
        assert fresh_icon.cacheKey() != history_icon.cacheKey()

        # 占位图标必须与对勾等大，否则两种行的标题仍然对不齐
        size = QSize(16, 16)
        assert fresh_icon.actualSize(size) == history_icon.actualSize(size) == size

        for column in range(model.columnCount()):
            if column != title_column:
                assert model.index(0, column, parent).data(role) is None

        # 下载记录里的条目不再显示为灰色，灰色留给本次会话刚提交的
        assert model.index(0, title_column, parent).data(Qt.ItemDataRole.ForegroundRole) is None
