"""
已完成列表分页查询（util/download/task/db.py）。

已完成列表此前是全量载入（4 万行约 150 MB）后再在内存里排序，导致启动慢、
切换排序要全量重排、下载完成后自动重排卡顿。改为分页后排序与过滤下推到 SQLite。

隔离方式：每个用例用 pytest 的 tmp_path，把 util.download.task.db 模块里的
appdata_path monkeypatch 过去，task.db 落在 tmp_path/Bili23 Downloader/ 下，
用完由 pytest 自动清理。conftest 的 QStandardPaths.setTestModeEnabled(True)
是另一层保险，保证即使这一层漏掉也不会碰用户真实数据。

这里钉住几件容易悄悄坏掉的事：

1. 旧库升级必须补上 file_size 列，并从 data JSON 里迁移出旧值；
2. build_record(completed=True) 必须写入 file_size，否则按大小排的索引永远是 0；
3. query_completed_page 的三种排序 × 升降序结果正确，分页边界正确；
4. 搜索只匹配 title 与 File.name（口径比客户端 _getSearchableText 窄）；
5. clear_completed 清空整表而不是当前页。
"""

from util.common._json import loads, dumps
from util.download.task.info import TaskInfo

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


def _make_completed(task_id, completed_time, title, total_size = 0, file_name = ""):
    task_info = TaskInfo()
    task_info.Basic.task_id = task_id
    task_info.Basic.completed_time = completed_time
    task_info.Basic.show_title = title
    task_info.Download.total_size = total_size
    task_info.File.name = file_name

    return task_info


def _task_ids_from_rows(rows):
    task_ids = []

    for (data,) in rows:
        task_info = TaskInfo()
        task_info.from_dict(loads(data))

        task_ids.append(task_info.Basic.task_id)

    return task_ids


# ---------------------------------------------------------------------------
# 迁移
# ---------------------------------------------------------------------------

def test_old_db_without_file_size_is_upgraded(tmp_path, monkeypatch):
    from util.download.task import db as db_module

    monkeypatch.setattr(db_module, "appdata_path", str(tmp_path))

    db_path = tmp_path / "Bili23 Downloader" / "task.db"
    db_path.parent.mkdir(parents = True, exist_ok = True)

    # 按旧版结构建库：completed_task 没有 file_size
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

    old_task = _make_completed("old-completed", 1_700_000_000, "旧记录", total_size = 12345)

    conn.execute(
        'INSERT INTO completed_task (task_id, hash_id, cover_id, title, completed_time, data) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        ("old-completed", "oldhash", "", "旧记录", 1_700_000_000, dumps(old_task.to_dict()))
    )
    conn.commit()
    conn.close()

    from util.download.task.db import TaskDatabase

    database = TaskDatabase()

    try:
        columns = {row[1] for row in database.query("PRAGMA table_info(completed_task)")}
        assert "file_size" in columns

        # 老记录的 file_size 从 data JSON 的 Download.total_size 里迁移出来
        rows = database.query("SELECT task_id, file_size FROM completed_task")
        assert rows == [("old-completed", 12345)]
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


def test_query_completed_page_keyword_matches_title_and_file_name(seeded_db):
    by_title = seeded_db.query_completed_page(0, 10, "completed_time", False, keyword = "Apple")
    assert _task_ids_from_rows(by_title) == ["t2"]

    by_file = seeded_db.query_completed_page(0, 10, "completed_time", False, keyword = "cherry")
    assert _task_ids_from_rows(by_file) == ["t3"]

    no_match = seeded_db.query_completed_page(0, 10, "completed_time", False, keyword = "ZZZ")
    assert no_match == []


def test_count_completed_agrees_with_query(seeded_db):
    assert seeded_db.count_completed() == 5
    assert seeded_db.count_completed(keyword = "Apple") == 1
    assert seeded_db.count_completed(keyword = "ZZZ") == 0


def test_clear_completed_does_not_touch_downloading(seeded_db):
    downloading = TaskInfo()
    downloading.Basic.task_id = "queued"
    downloading.Basic.created_time = 1_700_000_000

    seeded_db.add_tasks([downloading])

    seeded_db.clear_completed()

    assert seeded_db.count_completed() == 0
    assert seeded_db.count_tasks(completed = False) == 1