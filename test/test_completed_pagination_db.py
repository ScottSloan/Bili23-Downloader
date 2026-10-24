"""
已完成列表分页查询（util/download/task/db.py）。

已完成列表此前是全量载入（4 万行约 150 MB）后再在内存里排序，导致启动慢、
切换排序要全量重排、下载完成后自动重排卡顿。改为分页后排序与搜索下推到 SQLite。

隔离方式：每个用例用 pytest 的 tmp_path，把 util.download.task.db 模块里的
appdata_path monkeypatch 过去，task.db 落在 tmp_path/Bili23 Downloader/ 下，
用完由 pytest 自动清理。conftest 的 QStandardPaths.setTestModeEnabled(True)
是另一层保险，保证即使这一层漏掉也不会碰用户真实数据。

！！！！！！！！！！！！！！！！！！！注意事项！！！！！！！！！！！！！！！！！！！！：

1. 旧库升级必须补上 file_size 列，并从 data JSON 里迁移出旧值；
2. build_record(completed=True) 必须写入 file_size，否则按大小排的索引永远是 0；
3. query_completed_page 的三种排序 × 升降序结果正确，分页边界正确；
4. 三种排序键都有对应索引，EXPLAIN QUERY PLAN 里确实用上了 ——
   尤其 title 的索引必须带 COLLATE NOCASE，普通索引无法匹配
   ORDER BY "title" COLLATE NOCASE，会退化为全表排序；
5. ORDER BY 必须带 "id" tie-breaker，否则同值时 SQLite 不保证稳定顺序，
   分页时同一行可能出现在两页，或某行永远不出现；
6. 搜索语义与旧版客户端 _getSearchableText 一致：空格分词，每个词都要命中，
   每个词可以落在任意一个字段里（共 9 个字段）。LIKE 里的 %/_ 必须转义；
7. 媒体筛选 SQL 必须与客户端 get_media_type_key 逐条一致（AUDIO > COURSE >
   BANGUMI > INTERACTIVE > VIDEO 的互斥优先级，VIDEO 组同时包含 INTERACTIVE）；
8. clear_completed 清空整表；delete_completed_by_filter 按关键词 + 媒体类型
   AND 关系删除匹配记录，都为空时退回清整表；
9. upgrade_failed = True（_upgrade() 失败时的降级状态）时读接口返回空/0、
   写接口直接 return，不碰结构不对的表；move_to_completed 返回 False，
   任务留在 download_task 里，重启升级成功后可重新处理；
10. 旧库升级时 download_task 里的记录必须原样保留 —— 这条路径若坏了，
    用户升级后下载中的任务会全部消失，比已完成列表不可用更严重；
11. _upgrade() 抛异常时不传播、user_version 不写入、下次启动会重试、
    事务失败时回滚、迁移成功后索引重建、迁移时 hash_id 按当前算法重算。
"""

from util.common._json import loads, dumps
from util.common.enum import DownloadType
from util.download.task.info import TaskInfo
from util.parse.episode.tree import Attribute

from pathlib import Path
import sqlite3

import pytest


@pytest.fixture
def db(tmp_path, monkeypatch):
    # TaskDatabase.__init__ 里 Path(appdata_path) / "Bili23 Downloader" / "task.db"，
    # 把 appdata_path 指到 tmp_path，库就落在 tmp_path/Bili23 Downloader/task.db，
    # 连同 -wal / -shm 一起被 pytest 在用例结束后自动清理，与其他测试完全隔离
    from util.download.task import db as db_module

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    from util.download.task.db import TaskDatabase

    database = TaskDatabase()

    yield database

    database.close_connection()


def _make_completed(task_id, completed_time, title, total_size = 0, file_name = "", **episode_fields):
    """
    构造一条 completed 记录

    episode_fields 用来覆盖 Episode 上的任意字段（uploader、bvid、parent_title、
    attribute 等）。媒体筛选测试需要 attribute 与 Download.type 的组合，
    所以这两项也通过关键字覆盖。
    """
    task_info = TaskInfo()
    task_info.Basic.task_id = task_id
    task_info.Basic.completed_time = completed_time
    task_info.Basic.show_title = title
    task_info.Download.total_size = total_size
    task_info.File.name = file_name

    for key, value in episode_fields.items():
        if key == "download_type":
            task_info.Download.type = value
        else:
            setattr(task_info.Episode, key, value)

    return task_info


def _task_ids_from_rows(rows):
    task_ids = []

    for (data,) in rows:
        task_info = TaskInfo()
        task_info.from_dict(loads(data))

        task_ids.append(task_info.Basic.task_id)

    return task_ids


def _create_old_database(db_path: Path, download_records=None, completed_records=None):
    """
    构造旧版数据库：completed_task 缺 file_size 列，无索引

    与 test_old_db_without_file_size_is_upgraded 里的建表逻辑一致，
    抽出来供多个升级路径用例复用
    """
    db_path.parent.mkdir(parents = True, exist_ok = True)

    conn = sqlite3.connect(db_path)

    conn.executescript("""
        CREATE TABLE download_task (
            id INTEGER UNIQUE,
            task_id TEXT UNIQUE,
            hash_id TEXT,
            cover_id TEXT,
            title TEXT,
            created_time INTEGER,
            data TEXT,
            PRIMARY KEY(id AUTOINCREMENT)
        );
        CREATE TABLE completed_task (
            id INTEGER UNIQUE,
            task_id TEXT UNIQUE,
            hash_id TEXT,
            cover_id TEXT,
            title TEXT,
            completed_time INTEGER,
            data TEXT,
            PRIMARY KEY(id AUTOINCREMENT)
        );
    """)

    for task_info in (download_records or []):
        conn.execute(
            'INSERT INTO download_task (task_id, hash_id, cover_id, title, created_time, data) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (
                task_info.Basic.task_id, "OLD_HASH", "", task_info.Basic.show_title,
                task_info.Basic.created_time, dumps(task_info.to_dict())
            )
        )

    for task_info in (completed_records or []):
        conn.execute(
            'INSERT INTO completed_task (task_id, hash_id, cover_id, title, completed_time, data) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (
                task_info.Basic.task_id, "OLD_HASH", "", task_info.Basic.show_title,
                task_info.Basic.completed_time, dumps(task_info.to_dict())
            )
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 迁移：结构升级、记录保留、失败不传播、版本号、重试、回滚、索引重建、hash 重算
# ---------------------------------------------------------------------------

def test_old_db_without_file_size_is_upgraded(tmp_path, monkeypatch):
    from util.download.task import db as db_module

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"

    old_task = _make_completed("old-completed", 1_700_000_000, "旧记录", total_size = 12345)
    _create_old_database(db_path, completed_records=[old_task])

    from util.download.task.db import TaskDatabase

    database = TaskDatabase()

    try:
        columns = {row[1] for row in database.query("PRAGMA table_info(completed_task)")}
        assert "file_size" in columns

        # 老记录的 file_size 从 data JSON 的 Download.total_size 里迁移出来
        rows = database.query("SELECT task_id, file_size FROM completed_task")
        assert rows == [("old-completed", 12345)]

        # 升级成功的库 upgrade_failed 应为 False
        assert database.upgrade_failed is False
    finally:
        database.close_connection()


def test_old_db_upgrade_preserves_downloading_records(tmp_path, monkeypatch):
    """迁移时 download_task 里的记录必须原样保留

    这条路径若坏了，用户升级后下载中的任务会全部消失，比已完成列表不可用
    更严重。test_old_db_without_file_size_is_upgraded 只插入了 completed 记录，
    这里单独覆盖 download_task 记录的迁移
    """
    from util.download.task import db as db_module

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"

    # 两条下载中记录 + 一条已完成记录
    downloading_a = TaskInfo()
    downloading_a.Basic.task_id = "downloading-a"
    downloading_a.Basic.created_time = 1_700_000_000
    downloading_a.Basic.show_title = "下载中 A"

    downloading_b = TaskInfo()
    downloading_b.Basic.task_id = "downloading-b"
    downloading_b.Basic.created_time = 1_700_000_001
    downloading_b.Basic.show_title = "下载中 B"

    completed_c = _make_completed("completed-c", 1_700_000_002, "已完成 C", total_size = 999)

    _create_old_database(
        db_path,
        download_records=[downloading_a, downloading_b],
        completed_records=[completed_c]
    )

    from util.download.task.db import TaskDatabase

    database = TaskDatabase()

    try:
        # 升级成功
        assert database.upgrade_failed is False

        # download_task 的两条记录保留
        downloading_rows = database.query("SELECT task_id FROM download_task ORDER BY task_id")
        assert [row[0] for row in downloading_rows] == ["downloading-a", "downloading-b"]

        # completed_task 的一条记录保留，且 file_size 迁移正确
        completed_rows = database.query("SELECT task_id, file_size FROM completed_task")
        assert completed_rows == [("completed-c", 999)]

    finally:
        database.close_connection()


def test_upgrade_failure_does_not_propagate(tmp_path, monkeypatch):
    """_upgrade() 抛异常时 TaskDatabase.__init__ 不传播，upgrade_failed = True

    TaskDatabase.__init__ 是 TaskManager.__init__ 的同步调用，异常传播出去
    会让应用直接启动失败。这里验证抛异常时 __init__ 正常返回
    """
    from util.download.task import db as db_module
    from util.download.task.db import TaskDatabase

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"
    _create_old_database(db_path)

    original_upgrade = TaskDatabase._upgrade

    def boom(self):
        raise RuntimeError("模拟升级失败")

    TaskDatabase._upgrade = boom

    try:
        database = TaskDatabase()

    finally:
        TaskDatabase._upgrade = original_upgrade

    try:
        # 不抛异常，upgrade_failed = True
        assert database.upgrade_failed is True

    finally:
        database.close_connection()


def test_upgrade_failure_does_not_write_user_version(tmp_path, monkeypatch):
    """升级失败时 user_version 不写入 HASH_ID_VERSION，下次启动会重试"""
    from util.download.task import db as db_module
    from util.download.task.db import TaskDatabase
    from util.download.task.hash_id import HASH_ID_VERSION

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"
    _create_old_database(db_path)

    original_upgrade = TaskDatabase._upgrade

    def boom(self):
        raise RuntimeError("模拟升级失败")

    TaskDatabase._upgrade = boom

    try:
        database = TaskDatabase()

    finally:
        TaskDatabase._upgrade = original_upgrade

    try:
        # user_version 未被写入（旧库默认 0），下次启动 _needs_upgrade 仍返回 True
        assert database.get_user_version() != HASH_ID_VERSION

    finally:
        database.close_connection()


def test_upgrade_failure_is_retried_on_next_startup(tmp_path, monkeypatch):
    """升级失败后下次启动重试，成功则 upgrade_failed = False"""
    from util.download.task import db as db_module
    from util.download.task.db import TaskDatabase

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"

    old_task = _make_completed("retry-task", 1_700_000_000, "重试任务", total_size = 444)
    _create_old_database(db_path, completed_records=[old_task])

    # 第一次：升级失败
    original_upgrade = TaskDatabase._upgrade

    def boom(self):
        raise RuntimeError("模拟升级失败")

    TaskDatabase._upgrade = boom

    try:
        first = TaskDatabase()
        assert first.upgrade_failed is True
        first.close_connection()

    finally:
        TaskDatabase._upgrade = original_upgrade

    # 第二次：不 monkeypatch，升级正常执行
    second = TaskDatabase()

    try:
        assert second.upgrade_failed is False

        # 数据完整，file_size 迁移正确
        rows = second.query("SELECT task_id, file_size FROM completed_task")
        assert rows == [("retry-task", 444)]

    finally:
        second.close_connection()


def test_upgrade_transaction_rolls_back_on_failure(tmp_path, monkeypatch):
    """_upgrade 事务中途失败时整体回滚，旧表结构与数据保留

    PR 描述「任一步失败均整体回滚，旧表数据保留」的验证：
    在 INSERT INTO completed_task 的 executemany 阶段抛异常，验证
    DROP + CREATE 也被回滚，旧表（无 file_size 列）和旧数据都还在。

    sqlite3.Cursor 是 C 扩展类型，无法直接 monkeypatch。改为包装
    TaskDatabase.get_connection() 的返回值：cursor().executemany 在
    遇到 INSERT INTO completed_task 时抛异常，其余全部转发到真实连接。
    sqlite3.Connection.__exit__ 在异常时回滚整个事务，包括 DROP/CREATE。
    """
    from util.download.task import db as db_module
    from util.download.task.db import TaskDatabase

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"

    old_task = _make_completed("rollback-task", 1_700_000_000, "回滚任务", total_size = 777)
    _create_old_database(db_path, completed_records=[old_task])

    original_get_connection = TaskDatabase.get_connection

    class _FailingCursor:
        def __init__(self, real):
            self._real = real

        def execute(self, sql, *args):
            return self._real.execute(sql, *args)

        def executemany(self, sql, params):
            if "INSERT INTO completed_task" in sql:
                raise RuntimeError("模拟写入 completed_task 失败")

            return self._real.executemany(sql, params)

        def fetchall(self):
            return self._real.fetchall()

        def fetchone(self):
            return self._real.fetchone()

        def close(self):
            return self._real.close()

    class _FailingConnection:
        def __init__(self, real):
            self._real = real

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # 转发给真实连接的 __exit__：异常时回滚、正常时提交
            return self._real.__exit__(exc_type, exc_val, exc_tb)

        def cursor(self):
            return _FailingCursor(self._real.cursor())

        def execute(self, sql, *args):
            return self._real.execute(sql, *args)

        def executemany(self, sql, params):
            return self._real.executemany(sql, params)

        def executescript(self, script):
            return self._real.executescript(script)

        def commit(self):
            return self._real.commit()

        def rollback(self):
            return self._real.rollback()

        def close(self):
            return self._real.close()

    def patched_get_connection(self):
        return _FailingConnection(original_get_connection(self))

    monkeypatch.setattr(TaskDatabase, "get_connection", patched_get_connection)

    database = TaskDatabase()

    try:
        assert database.upgrade_failed is True

        # 旧表结构未变（缺 file_size 列）——DROP TABLE + CREATE TABLE 被回滚
        columns = {row[1] for row in database.query("PRAGMA table_info(completed_task)")}
        assert "file_size" not in columns

        # 旧数据仍在
        rows = database.query("SELECT task_id FROM completed_task")
        assert rows == [("rollback-task",)]

    finally:
        database.close_connection()


def test_upgrade_recreates_indexes(tmp_path, monkeypatch):
    """迁移成功后索引被重建

    _upgrade 里 DROP TABLE 会连带删除旧索引，__init__ 末尾调
    _create_extra_indexes 补建。这里验证迁移后索引确实存在
    """
    from util.download.task import db as db_module
    from util.download.task.db import TaskDatabase

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"

    old_task = _make_completed("index-task", 1_700_000_000, "索引任务")
    _create_old_database(db_path, completed_records=[old_task])

    database = TaskDatabase()

    try:
        assert database.upgrade_failed is False

        # 迁移后所有索引都在
        index_names = {row[1] for row in database.query("PRAGMA index_list(completed_task)")}

        assert "idx_completed_task_hash_id" in index_names
        assert "idx_completed_task_completed_time" in index_names
        assert "idx_completed_task_file_size" in index_names
        assert "idx_completed_task_title" in index_names
        assert "idx_completed_task_bvid" in index_names

    finally:
        database.close_connection()


def test_upgrade_recalculates_hash_id(tmp_path, monkeypatch):
    """迁移时 hash_id 按当前算法重算

    旧库里的 hash_id 可能是早期算法的结果（依赖 orjson 默认输出格式等），
    迁移时用 _calc_hash_id 按当前算法重算。这里插入 OLD_HASH 占位，
    验证迁移后 hash_id 被改写成 _calc_hash_id(task_info) 的结果
    """
    from util.download.task import db as db_module
    from util.download.task.db import TaskDatabase

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"

    old_task = _make_completed("hash-task", 1_700_000_000, "hash 任务", attribute = 1)
    _create_old_database(db_path, completed_records=[old_task])

    database = TaskDatabase()

    try:
        assert database.upgrade_failed is False

        rows = database.query("SELECT hash_id, data FROM completed_task WHERE task_id = ?", ("hash-task",))
        assert len(rows) == 1

        stored_hash, data = rows[0]

        # 迁移前是占位 "OLD_HASH"，迁移后被改写成当前算法的结果
        assert stored_hash != "OLD_HASH"

        # 与新算法算出的值一致
        task_info = TaskInfo()
        task_info.from_dict(loads(data))
        assert stored_hash == database._calc_hash_id(task_info)

    finally:
        database.close_connection()


# ---------------------------------------------------------------------------
# build_record / move_to_completed
# ---------------------------------------------------------------------------

def test_build_record_completed_returns_seven_tuple(db):
    task_info = _make_completed("build-test", 1_700_000_001, "标题", total_size = 999)

    record = db.build_record(task_info, completed = True)

    assert len(record) == 7
    assert record[0] == "build-test"
    assert record[3] == "标题"
    assert record[4] == 1_700_000_001
    assert record[5] == 999


def test_build_record_downloading_still_six_tuple(db):
    task_info = TaskInfo()
    task_info.Basic.task_id = "queued"
    task_info.Basic.created_time = 1_700_000_000

    record = db.build_record(task_info, completed = False)

    assert len(record) == 6


def test_move_to_completed_writes_file_size(db):
    task_info = _make_completed("move-test", 1_700_000_100, "移动测试", total_size = 555)

    db.add_tasks([task_info])

    db.move_to_completed(db.build_record(task_info, completed = True))

    completed_rows = db.query('SELECT file_size FROM completed_task WHERE task_id = ?', ("move-test",))
    assert completed_rows == [(555,)]

    downloading_rows = db.query('SELECT COUNT(*) FROM download_task WHERE task_id = ?', ("move-test",))
    assert downloading_rows == [(0,)]


def test_move_to_completed_returns_true_on_success(db):
    """正常路径 move_to_completed 返回 True"""
    task_info = _make_completed("normal-archive", 1_700_000_000, "正常归档")
    db.add_tasks([task_info], completed = False)

    assert db.move_to_completed(db.build_record(task_info, completed = True)) is True

    assert db.count_tasks(completed = False) == 0
    assert db.count_tasks(completed = True) == 1


# ---------------------------------------------------------------------------
# 索引：三种排序键都必须走索引
#
# 这里的 SQL 必须与 db.py 的 query_completed_page 里逐字一致（含 COLLATE NOCASE
# 与 "id" tie-breaker），否则 EXPLAIN QUERY PLAN 描述的是一条与实际查询不同的
# 路径 —— 那等于测试的是另一条 SQL。
# ---------------------------------------------------------------------------

def test_title_sort_uses_index(db):
    """按标题排序必须走 NOCASE 索引，不能是全表排序"""
    plan = db.query("""
        EXPLAIN QUERY PLAN
        SELECT data FROM "completed_task"
        ORDER BY "title" COLLATE NOCASE DESC, "id" DESC
        LIMIT 100
    """)

    details = " ".join(str(row[-1]) for row in plan)

    assert "idx_completed_task_title" in details
    assert "TEMP B-TREE" not in details


def test_completed_time_sort_uses_index(db):
    plan = db.query("""
        EXPLAIN QUERY PLAN
        SELECT data FROM "completed_task"
        ORDER BY "completed_time" DESC, "id" DESC
        LIMIT 100
    """)

    details = " ".join(str(row[-1]) for row in plan)

    assert "idx_completed_task_completed_time" in details
    assert "TEMP B-TREE" not in details


def test_file_size_sort_uses_index(db):
    plan = db.query("""
        EXPLAIN QUERY PLAN
        SELECT data FROM "completed_task"
        ORDER BY "file_size" DESC, "id" DESC
        LIMIT 100
    """)

    details = " ".join(str(row[-1]) for row in plan)

    assert "idx_completed_task_file_size" in details
    assert "TEMP B-TREE" not in details


def test_tie_breaker_keeps_pagination_stable(db):
    """同值时按 id 排序，分页不会重复或遗漏

    按 file_size 排序时大量条目的 total_size 为 0 或相同。没有 tie-breaker 的话
    SQLite 不保证稳定顺序，同一行可能出现在两页，或某行永远不出现。这个用例在
    没有 "id" tie-breaker 时会失败 —— 是钉住 reviewer ① 的核心保护
    """
    # 10 条 total_size 全为 0 的记录，只有 id 不同
    tasks = [_make_completed(f"t{i}", 1000 + i, f"标题{i}", total_size = 0) for i in range(1, 11)]
    db.add_tasks(tasks, completed = True)

    seen = []
    page_size = 3

    # 4 页 * 3 条 = 12 个位置，但只有 10 条记录，最后一页 1 条
    for page in range(4):
        rows = db.query_completed_page(page * page_size, page_size, "file_size", False)
        seen.extend(_task_ids_from_rows(rows))

    assert len(seen) == 10
    assert len(set(seen)) == 10
    assert set(seen) == {f"t{i}" for i in range(1, 11)}


# ---------------------------------------------------------------------------
# query_completed_page
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_db(db):
    tasks = [
        _make_completed("t1", 1000, "Banana",     total_size = 100, file_name = "banana.mp4"),
        _make_completed("t2", 3000, "Apple",      total_size = 300, file_name = "apple.mp4"),
        _make_completed("t3", 2000, "Cherry",     total_size = 200, file_name = "cherry.mp4"),
        _make_completed("t4", 4000, "Date",       total_size = 400, file_name = "date.mp4"),
        _make_completed("t5", 500,  "Elderberry", total_size = 50,  file_name = "elderberry.mp4"),
    ]

    db.add_tasks(tasks, completed = True)

    return db


@pytest.mark.parametrize("order_by, ascending, expected_ids", [
    ("completed_time", False, ["t4", "t2", "t3", "t1", "t5"]),
    ("completed_time", True,  ["t5", "t1", "t3", "t2", "t4"]),
    ("show_title",     True,  ["t2", "t1", "t3", "t4", "t5"]),
    ("show_title",     False, ["t5", "t4", "t3", "t1", "t2"]),
    ("file_size",      False, ["t4", "t2", "t3", "t1", "t5"]),
    ("file_size",      True,  ["t5", "t1", "t3", "t2", "t4"]),
])
def test_query_completed_page_sorting(seeded_db, order_by, ascending, expected_ids):
    rows = seeded_db.query_completed_page(
        offset = 0, limit = 10, order_by = order_by, ascending = ascending
    )

    assert _task_ids_from_rows(rows) == expected_ids


def test_query_completed_page_pagination_boundaries(seeded_db):
    first = seeded_db.query_completed_page(0, 2, "completed_time", True)
    assert _task_ids_from_rows(first) == ["t5", "t1"]

    middle = seeded_db.query_completed_page(2, 2, "completed_time", True)
    assert _task_ids_from_rows(middle) == ["t3", "t2"]

    tail = seeded_db.query_completed_page(4, 2, "completed_time", True)
    assert _task_ids_from_rows(tail) == ["t4"]

    out_of_range = seeded_db.query_completed_page(100, 2, "completed_time", True)
    assert out_of_range == []


# ---------------------------------------------------------------------------
# 搜索：字段与旧版 proxy_model._getSearchableText 一致
# ---------------------------------------------------------------------------

def test_query_completed_page_searches_title(seeded_db):
    rows = seeded_db.query_completed_page(0, 10, "completed_time", False, keyword = "Apple")
    assert _task_ids_from_rows(rows) == ["t2"]


def test_query_completed_page_searches_file_name(seeded_db):
    rows = seeded_db.query_completed_page(0, 10, "completed_time", False, keyword = "cherry")
    assert _task_ids_from_rows(rows) == ["t3"]


@pytest.mark.parametrize("field, keyword", [
    ("uploader",         "Alice"),
    ("bvid",             "BV1xx"),
    ("parent_title",     "稿件标题"),
    ("collection_title", "合集名"),
    ("series_title",     "系列名"),
    ("season_title",     "季名"),
    ("favorites_name",   "收藏夹名"),
])
def test_query_completed_page_searches_episode_fields(db, field, keyword):
    """旧版客户端搜索覆盖 9 个字段，这里逐一确认除 title 与 file_name 外的 7 个也下推到了 SQLite"""
    task = _make_completed("task-x", 1000, "标题", **{field: f"前缀 {keyword} 后缀"})

    db.add_tasks([task], completed = True)

    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = keyword)

    assert _task_ids_from_rows(rows) == ["task-x"]


def test_query_completed_page_search_is_case_insensitive(seeded_db):
    """LIKE 对 ASCII 大小写不敏感，等价于旧版 casefold() 的常见行为"""
    rows = seeded_db.query_completed_page(0, 10, "completed_time", False, keyword = "APPLE")
    assert _task_ids_from_rows(rows) == ["t2"]


def test_query_completed_page_no_match(seeded_db):
    rows = seeded_db.query_completed_page(0, 10, "completed_time", False, keyword = "ZZZ")
    assert rows == []


def test_query_completed_page_multiple_keywords_are_anded(db):
    """空格分词，每个词都要命中；每个词可以落在不同字段里"""
    tasks = [
        _make_completed("a", 1000, "Minecraft 生存", uploader = "Alice"),
        _make_completed("b", 2000, "Minecraft 建筑", uploader = "Bob"),
        _make_completed("c", 3000, "原神", uploader = "Alice"),
    ]
    db.add_tasks(tasks, completed = True)

    # 跨字段 AND：标题含 minecraft，同时 UP 主是 alice
    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "minecraft alice")
    assert _task_ids_from_rows(rows) == ["a"]

    # 单词：两个 alice 的条目都命中
    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "alice")
    assert set(_task_ids_from_rows(rows)) == {"a", "c"}

    # 同一字段内的两个词：只有 b 的标题和 UP 主都命中
    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "minecraft bob")
    assert _task_ids_from_rows(rows) == ["b"]

    # 任意一个词不命中就整条排除
    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "minecraft 不存在的词")
    assert rows == []


def test_query_completed_page_keyword_with_extra_whitespace(db):
    """多余空白不影响分词：'  alice   minecraft  ' 等价于 'alice minecraft'"""
    task = _make_completed("a", 1000, "Minecraft 生存", uploader = "Alice")
    db.add_tasks([task], completed = True)

    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "  ALICE   minecraft  ")
    assert _task_ids_from_rows(rows) == ["a"]


def test_query_completed_page_whitespace_only_keyword_is_no_filter(db):
    task = _make_completed("a", 1000, "标题")
    db.add_tasks([task], completed = True)

    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "   ")
    assert _task_ids_from_rows(rows) == ["a"]


def test_query_completed_page_keyword_escapes_like_wildcards(db):
    """关键词里的 % 和 _ 必须按字面匹配，不能当通配符

    不转义的话 "%" 会匹配所有记录，而 delete_completed_by_filter("%") 会清空整表。
    原版 proxy 用 Python 的 `in` 是字面匹配，这里必须对齐
    """
    tasks = [
        _make_completed("a", 1000, "普通标题"),
        _make_completed("b", 2000, "100% 完整版"),
        _make_completed("c", 3000, "file_name_test"),
    ]
    db.add_tasks(tasks, completed = True)

    # "%" 只匹配标题里含字面 % 的 b
    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "%")
    assert _task_ids_from_rows(rows) == ["b"]

    # "_" 只匹配含字面下划线的 c
    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "_")
    assert _task_ids_from_rows(rows) == ["c"]


def test_query_completed_page_search_combines_with_pagination(seeded_db):
    """搜索与分页同时生效：offset/limit 作用于筛选后的结果集"""
    tasks = [
        _make_completed("m1", 1000, "Keyword Alpha", uploader = "Keyword"),
        _make_completed("m2", 2000, "Keyword Beta",  uploader = "Keyword"),
        _make_completed("m3", 3000, "Keyword Gamma", uploader = "Keyword"),
    ]

    seeded_db.add_tasks(tasks, completed = True)

    first = seeded_db.query_completed_page(0, 2, "completed_time", False, keyword = "Keyword")
    assert _task_ids_from_rows(first) == ["m3", "m2"]

    second = seeded_db.query_completed_page(2, 2, "completed_time", False, keyword = "Keyword")
    assert _task_ids_from_rows(second) == ["m1"]


def test_count_completed_agrees_with_query(seeded_db):
    assert seeded_db.count_completed() == 5
    assert seeded_db.count_completed(keyword = "Apple") == 1
    assert seeded_db.count_completed(keyword = "cherry") == 1
    assert seeded_db.count_completed(keyword = "ZZZ") == 0


def test_count_completed_respects_multiple_keywords(db):
    tasks = [
        _make_completed("a", 1000, "Minecraft 生存", uploader = "Alice"),
        _make_completed("b", 2000, "Minecraft 建筑", uploader = "Bob"),
    ]
    db.add_tasks(tasks, completed = True)

    assert db.count_completed(keyword = "minecraft") == 2
    assert db.count_completed(keyword = "minecraft alice") == 1
    assert db.count_completed(keyword = "minecraft bob") == 1
    assert db.count_completed(keyword = "minecraft carol") == 0


# ---------------------------------------------------------------------------
# 媒体筛选：SQL 分类必须与客户端 get_media_type_key 逐条一致
#
# 客户端判定是一个互斥的分派：AUDIO > COURSE > BANGUMI > INTERACTIVE > VIDEO。
# SQL 版本必须同样互斥，否则一条带多个属性位的记录会同时落入多个类别，
# 筛选结果与封面角标对不上。
#
# UI 的 get_media_type_group_dict 只提供四个组：VIDEO / BANGUMI / COURSE / AUDIO，
# 其中 VIDEO 组同时包含 VIDEO 与 INTERACTIVE（互动视频归在「视频」里）。
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("attribute, download_type, expected_client_key", [
    # 普通投稿视频
    (Attribute.VIDEO_BIT, DownloadType.VIDEO | DownloadType.AUDIO, "VIDEO"),
    # 互动视频：VIDEO_BIT + INTERACTIVE_BIT，客户端归到「互动」，UI 组归到「视频」
    (Attribute.VIDEO_BIT | Attribute.INTERACTIVE_BIT, DownloadType.VIDEO | DownloadType.AUDIO, "INTERACTIVE"),
    # 番剧
    (Attribute.BANGUMI_BIT, DownloadType.VIDEO | DownloadType.AUDIO, "BANGUMI"),
    # 课程（CHEESE）
    (Attribute.CHEESE_BIT, DownloadType.VIDEO | DownloadType.AUDIO, "COURSE"),
    # 会员购课程（LESSON）
    (Attribute.LESSON_BIT, DownloadType.VIDEO | DownloadType.AUDIO, "COURSE"),
    # 仅下载音频（type 无 VIDEO 位），attribute 无特殊位
    (Attribute.VIDEO_BIT, DownloadType.AUDIO, "AUDIO"),
    # 带 AUDIO_BIT 的音频条目
    (Attribute.AUDIO_BIT, DownloadType.AUDIO, "AUDIO"),
])
def test_media_type_sql_matches_client_classification(db, attribute, download_type, expected_client_key):
    """_build_media_type_sql 的分类必须与客户端 get_media_type_key 逐条一致

    用例同时验证客户端分类和 SQL 分类，任何一侧语义分叉都会失败
    """
    from types import SimpleNamespace
    from gui.component.download_list.item_delegate import get_media_type_key

    # 1. 客户端分类
    client_task = SimpleNamespace(
        Episode = SimpleNamespace(attribute = attribute),
        Download = SimpleNamespace(type = download_type),
    )
    client_key = get_media_type_key(client_task)

    assert client_key == expected_client_key, f"客户端分类与预期不符：{client_key} != {expected_client_key}"

    # 2. SQL 分类
    task_info = _make_completed("media-test", 1000, "媒体类型测试", attribute = attribute, download_type = download_type)
    db.add_tasks([task_info], completed = True)

    # 四个 UI 组逐一测试：只有客户端分类命中的组才应该查到这条记录
    ui_groups = {
        "VIDEO": {"VIDEO", "INTERACTIVE"},
        "BANGUMI": {"BANGUMI"},
        "COURSE": {"COURSE"},
        "AUDIO": {"AUDIO"},
    }

    for group, members in ui_groups.items():
        rows = db.query_completed_page(0, 10, "completed_time", False, media_types = frozenset({group}))
        found = _task_ids_from_rows(rows) == ["media-test"]

        expected = expected_client_key in members

        assert found == expected, (
            f"属性位 {attribute:#x} type {download_type} 在组 {group} 的分类不一致"
            f"（客户端：{expected_client_key}，SQL 命中：{found}，应命中：{expected}）"
        )


def test_media_type_sql_priority_excludes_lower_categories(db):
    """同时带多个属性位时，SQL 的互斥排除必须生效

    客户端的判定是 AUDIO > COURSE > BANGUMI > INTERACTIVE > VIDEO 的互斥分派。
    一条记录同时带 BANGUMI_BIT 与 VIDEO_BIT 时，客户端归到 BANGUMI；
    SQL 的 is_bangumi 分支必须通过 NOT is_audio AND NOT course_pre 排除
    AUDIO 与 COURSE，才能在 BANGUMI 组命中而 VIDEO 组不命中。

    这个用例在 SQL 缺少互斥排除时会失败：VIDEO 组会额外命中这条记录
    """
    from types import SimpleNamespace
    from gui.component.download_list.item_delegate import get_media_type_key

    attribute = Attribute.VIDEO_BIT | Attribute.BANGUMI_BIT
    download_type = DownloadType.VIDEO | DownloadType.AUDIO

    client_task = SimpleNamespace(
        Episode = SimpleNamespace(attribute = attribute),
        Download = SimpleNamespace(type = download_type),
    )

    # 客户端归到 BANGUMI（优先级高于 VIDEO）
    assert get_media_type_key(client_task) == "BANGUMI"

    task_info = _make_completed("multi-bit", 1000, "多属性位", attribute = attribute, download_type = download_type)
    db.add_tasks([task_info], completed = True)

    # BANGUMI 组命中
    rows = db.query_completed_page(0, 10, "completed_time", False, media_types = frozenset({"BANGUMI"}))
    assert _task_ids_from_rows(rows) == ["multi-bit"]

    # VIDEO 组不命中（被互斥排除）
    rows = db.query_completed_page(0, 10, "completed_time", False, media_types = frozenset({"VIDEO"}))
    assert _task_ids_from_rows(rows) == []


def test_media_type_sql_priority_audio_beats_everything(db):
    """audio_only 优先于所有属性位：type 只有 AUDIO 时不论 attribute 有什么位都归 AUDIO"""
    from types import SimpleNamespace
    from gui.component.download_list.item_delegate import get_media_type_key

    # 一条记录同时带 BANGUMI_BIT，但 type 只有 AUDIO（无 VIDEO 位）
    attribute = Attribute.BANGUMI_BIT
    download_type = DownloadType.AUDIO

    client_task = SimpleNamespace(
        Episode = SimpleNamespace(attribute = attribute),
        Download = SimpleNamespace(type = download_type),
    )

    # audio_only 优先级最高，覆盖属性位
    assert get_media_type_key(client_task) == "AUDIO"

    task_info = _make_completed("audio-priority", 1000, "音频优先", attribute = attribute, download_type = download_type)
    db.add_tasks([task_info], completed = True)

    # 只在 AUDIO 组命中
    rows = db.query_completed_page(0, 10, "completed_time", False, media_types = frozenset({"AUDIO"}))
    assert _task_ids_from_rows(rows) == ["audio-priority"]

    rows = db.query_completed_page(0, 10, "completed_time", False, media_types = frozenset({"BANGUMI"}))
    assert _task_ids_from_rows(rows) == []


def test_media_type_filter_accepts_multiple_groups(db):
    """多组选择时是 OR 关系：勾「视频」+「音频」应同时命中两类"""
    tasks = [
        _make_completed("video", 1000, "视频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.VIDEO | DownloadType.AUDIO),
        _make_completed("audio", 2000, "音频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.AUDIO),
        _make_completed("bangumi", 3000, "番剧", attribute = Attribute.BANGUMI_BIT, download_type = DownloadType.VIDEO | DownloadType.AUDIO),
    ]
    db.add_tasks(tasks, completed = True)

    rows = db.query_completed_page(0, 10, "completed_time", False, media_types = frozenset({"VIDEO", "AUDIO"}))
    assert set(_task_ids_from_rows(rows)) == {"video", "audio"}

    rows = db.query_completed_page(0, 10, "completed_time", False, media_types = frozenset({"VIDEO", "BANGUMI"}))
    assert set(_task_ids_from_rows(rows)) == {"video", "bangumi"}


def test_media_type_filter_combines_with_keyword_as_and(db):
    """关键词与媒体筛选是 AND 关系，与旧版 proxy 的 _batchTargets 语义一致"""
    tasks = [
        _make_completed("vm", 1000, "Minecraft 视频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.VIDEO | DownloadType.AUDIO),
        _make_completed("am", 2000, "Minecraft 音频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.AUDIO),
        _make_completed("vo", 3000, "原神 视频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.VIDEO | DownloadType.AUDIO),
    ]
    db.add_tasks(tasks, completed = True)

    # 关键词 Minecraft + 视频组：只应命中 vm
    rows = db.query_completed_page(0, 10, "completed_time", False, keyword = "minecraft", media_types = frozenset({"VIDEO"}))
    assert _task_ids_from_rows(rows) == ["vm"]


# ---------------------------------------------------------------------------
# clear_completed / delete_completed_by_filter
# ---------------------------------------------------------------------------

def test_clear_completed_does_not_touch_downloading(seeded_db):
    downloading = TaskInfo()
    downloading.Basic.task_id = "queued"
    downloading.Basic.created_time = 1_700_000_000

    seeded_db.add_tasks([downloading])

    seeded_db.clear_completed()

    assert seeded_db.count_completed() == 0
    assert seeded_db.count_tasks(completed = False) == 1


def test_delete_completed_by_filter_only_touches_matches(db):
    """搜索生效时「全部清除」只删匹配的记录，其余保留"""
    tasks = [
        _make_completed("a", 1000, "Minecraft 生存", uploader = "Alice"),
        _make_completed("b", 2000, "原神", uploader = "Bob"),
        _make_completed("c", 3000, "Minecraft 建筑", uploader = "Alice"),
    ]
    db.add_tasks(tasks, completed = True)

    db.delete_completed_by_filter("minecraft")

    remaining = _task_ids_from_rows(db.query_completed_page(0, 10, "completed_time", False))
    assert set(remaining) == {"b"}


def test_delete_completed_by_filter_respects_multiple_keywords(db):
    tasks = [
        _make_completed("a", 1000, "Minecraft 生存", uploader = "Alice"),
        _make_completed("b", 2000, "Minecraft 建筑", uploader = "Bob"),
        _make_completed("c", 3000, "原神", uploader = "Alice"),
    ]
    db.add_tasks(tasks, completed = True)

    db.delete_completed_by_filter("minecraft alice")

    remaining = _task_ids_from_rows(db.query_completed_page(0, 10, "completed_time", False))
    assert set(remaining) == {"b", "c"}


def test_delete_completed_by_filter_combines_keyword_and_media_types(db):
    """关键词与媒体筛选是 AND 关系，只删同时匹配的

    这是 reviewer 强调的「关键词 + 媒体筛选组合下清空可能误删」的保护
    """
    tasks = [
        _make_completed("vm", 1000, "Minecraft 视频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.VIDEO | DownloadType.AUDIO),
        _make_completed("am", 2000, "Minecraft 音频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.AUDIO),
        _make_completed("vo", 3000, "原神 视频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.VIDEO | DownloadType.AUDIO),
    ]
    db.add_tasks(tasks, completed = True)

    # 只删「关键词 Minecraft 且媒体是视频」的 vm，am 与 vo 都保留
    db.delete_completed_by_filter("minecraft", frozenset({"VIDEO"}))

    remaining = _task_ids_from_rows(db.query_completed_page(0, 10, "completed_time", False))
    assert set(remaining) == {"am", "vo"}


def test_delete_completed_by_filter_only_media_types(db):
    """只有媒体筛选时按媒体筛选删，不触碰其他类型"""
    tasks = [
        _make_completed("video", 1000, "视频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.VIDEO | DownloadType.AUDIO),
        _make_completed("audio", 2000, "音频", attribute = Attribute.VIDEO_BIT, download_type = DownloadType.AUDIO),
        _make_completed("bangumi", 3000, "番剧", attribute = Attribute.BANGUMI_BIT, download_type = DownloadType.VIDEO | DownloadType.AUDIO),
    ]
    db.add_tasks(tasks, completed = True)

    db.delete_completed_by_filter("", frozenset({"VIDEO"}))

    remaining = _task_ids_from_rows(db.query_completed_page(0, 10, "completed_time", False))
    assert set(remaining) == {"audio", "bangumi"}


def test_delete_completed_by_filter_empty_clears_all(db):
    db.add_tasks([
        _make_completed("a", 1000, "标题 A"),
        _make_completed("b", 2000, "标题 B"),
    ], completed = True)

    db.delete_completed_by_filter("")

    assert db.count_completed() == 0


def test_delete_completed_by_filter_whitespace_falls_back_to_clear(db):
    db.add_tasks([
        _make_completed("a", 1000, "标题 A"),
        _make_completed("b", 2000, "标题 B"),
    ], completed = True)

    db.delete_completed_by_filter("   ")

    assert db.count_completed() == 0


def test_delete_completed_by_filter_does_not_touch_downloading(db):
    downloading = TaskInfo()
    downloading.Basic.task_id = "queued"
    downloading.Basic.created_time = 1_700_000_000
    downloading.Basic.show_title = "Minecraft"

    db.add_tasks([downloading])

    db.add_tasks([_make_completed("a", 1000, "Minecraft 生存")], completed = True)

    db.delete_completed_by_filter("minecraft")

    assert db.count_completed() == 0
    assert db.count_tasks(completed = False) == 1


def test_delete_completed_by_keyword_still_works(db):
    """delete_completed_by_keyword 是 delete_completed_by_filter 的兼容薄包装"""
    db.add_tasks([
        _make_completed("a", 1000, "Minecraft 生存"),
        _make_completed("b", 2000, "原神"),
    ], completed = True)

    db.delete_completed_by_keyword("minecraft")

    remaining = _task_ids_from_rows(db.query_completed_page(0, 10, "completed_time", False))
    assert set(remaining) == {"b"}


# ---------------------------------------------------------------------------
# 升级失败降级：upgrade_failed = True 时读接口返回空/0、写接口不抛异常
#
# _upgrade() 失败（磁盘满、只读文件系统、进程被 kill）时 TaskDatabase.__init__
# 不抛异常，而是设 upgrade_failed = True。读接口返回空列表/0 让 UI 显示
# 「No completed downloads」而不是崩溃；写接口直接 return，不再碰结构不对的表。
#
# move_to_completed 也检查 upgrade_failed：跳过归档并返回 False，
# 任务留在 download_task 里，重启并升级成功后可重新处理。
# 不做 DELETE + INSERT 的「半截操作」，避免 DELETE 已提交、INSERT 失败
# 导致任务记录永久丢失。
# ---------------------------------------------------------------------------

def test_upgrade_failed_flag_defaults_to_false(db):
    """新库不触发升级，upgrade_failed 恒为 False"""
    assert db.upgrade_failed is False


def test_upgrade_failed_makes_reads_return_empty(db):
    """upgrade_failed 时 query_completed_page / count_completed 返回空/0"""
    db.upgrade_failed = True

    try:
        assert db.query_completed_page(0, 10, "completed_time", False) == []
        assert db.query_completed_page(0, 10, "completed_time", False, keyword = "any") == []
        assert db.query_completed_page(0, 10, "completed_time", False, media_types = frozenset({"VIDEO"})) == []
        assert db.count_completed() == 0
        assert db.count_completed(keyword = "any") == 0
        assert db.count_completed(media_types = frozenset({"VIDEO"})) == 0

    finally:
        db.upgrade_failed = False


def test_upgrade_failed_makes_writes_noop(db):
    """upgrade_failed 时 clear_completed / delete_completed_by_filter 直接返回，不碰表"""
    # 先塞一条正常记录
    db.add_tasks([_make_completed("a", 1000, "标题 A")], completed = True)
    assert db.count_completed() == 1

    db.upgrade_failed = True

    try:
        # 写接口直接返回，不抛异常，也不删任何记录
        db.clear_completed()
        db.delete_completed_by_filter("minecraft")
        db.delete_completed_by_filter("minecraft", frozenset({"VIDEO"}))
        db.delete_completed_by_keyword("minecraft")

    finally:
        db.upgrade_failed = False

    # 记录仍在（写接口在 upgrade_failed 时直接 return）
    assert db.count_completed() == 1


def test_upgrade_failed_skips_move_to_completed(db):
    """upgrade_failed 时 move_to_completed 返回 False，不做 DELETE + INSERT

    升级事务已回滚，completed_task 仍缺 file_size 列，INSERT 7 元组会 SQL 报错。
    这里直接跳过，任务留在 download_task 里，重启并升级成功后可重新处理。
    不做 DELETE + INSERT 的「半截操作」，避免 DELETE 已提交、INSERT 失败
    导致任务记录永久丢失
    """
    task_info = _make_completed("skip-archive", 1_700_000_000, "跳过归档")
    db.add_tasks([task_info], completed = False)

    assert db.count_tasks(completed = False) == 1

    db.upgrade_failed = True

    try:
        result = db.move_to_completed(db.build_record(task_info, completed = True))

    finally:
        db.upgrade_failed = False

    # 返回 False
    assert result is False

    # 任务仍在 download_task 里，completed_task 里没有
    assert db.count_tasks(completed = False) == 1
    assert db.count_tasks(completed = True) == 0