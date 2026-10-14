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
def mark(task_manager, monkeypatch):
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

    def test_need_parse_items_are_skipped(self, task_manager, mark):
        # 收藏夹等需要二次解析的条目，解析端算出的 hash 与入库时的对不上，一律不标
        item = make_item(Attribute.VIDEO_BIT | Attribute.FAVLIST_BIT | Attribute.NEED_PARSE_BIT, aid = 1, bvid = "BV1", cid = 1)

        store(task_manager, item, "fav")

        mark([make_tree([item])])

        assert not item.in_download_history

    def test_unidentifiable_items_are_skipped(self, task_manager, mark, monkeypatch):
        # 没有任何形态位的条目落在兜底分支，解析端彼此会算出同一个 hash，查了只会误报
        item = make_item(0, aid = 1)

        queried = []
        monkeypatch.setattr(task_manager.db_manager, "filter_existing_hash_ids", lambda hash_ids: queried.append(list(hash_ids)) or set())

        mark([make_tree([item])])

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


class TestParseModelDecoration:
    def test_icon_only_on_title_column_of_history_items(self, app):
        from PySide6.QtCore import QModelIndex, QSize, Qt
        from PySide6.QtGui import QIcon

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

        parent = model.index(0, 0, QModelIndex())
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
