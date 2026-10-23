from ...common._json import loads, dumps
from ...common.config import appdata_path
from ...common.timestamp import get_timestamp
from ...common.database import Database
from .hash_id import calc_hash_id, HASH_ID_VERSION
from .info import TaskInfo

from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

class TaskDatabase(Database):
    # 已完成列表分页查询的排序键 -> SQL 表达式。
    # completed_time 与 file_size 有对应索引，走索引时 SQLite 直接取前 N 条，不需要对全表排序
    _COMPLETED_ORDER_COLUMNS = {
        "completed_time": '"completed_time"',
        "show_title": '"title" COLLATE NOCASE',
        "file_size": '"file_size"',
    }

    def __init__(self):
        super().__init__()

        self.path = Path(appdata_path) / "Bili23 Downloader" / "task.db"
        self.path.parent.mkdir(parents = True, exist_ok = True)

        self.check_and_create_table()

        self._check_should_upgrade()

        # 放在升级之后：旧版库升级时会重建两张表，先建的索引会随旧表一起消失
        self._create_bvid_index()
        self._create_extra_indexes()

    def _check_should_upgrade(self):
        # 配置版本与任务数据库版本并不等价。始终检查实际表结构，
        # 避免配置升级成功但数据库迁移失败后永久跳过迁移。
        if self._needs_upgrade():
            logger.info("检测到旧版下载任务数据库，正在进行升级")
            self._upgrade()

            # 升级时已按当前算法重算过 hash_id，直接打上版本号
            self.set_user_version(HASH_ID_VERSION)

            return

        self._check_should_rehash()

    def _check_should_rehash(self):
        # 表结构没变，但 hash_id 的算法可能已经变化。
        # 早期版本的 hash_id 依赖 orjson 的默认输出格式，换环境或升级版本后即失效，
        # 导致旧记录无法参与重复下载判定，因此需要按当前算法重算一次。
        current_version = self.get_user_version()

        if current_version >= HASH_ID_VERSION:
            return

        logger.info("检测到下载任务数据库中的 hash_id 版本过旧（%d），正在重算", current_version)

        try:
            self._rehash_all()

        except Exception:
            # 重算失败时不写入版本号，下次启动会再试一次，不影响本次正常使用
            logger.exception("重算下载任务 hash_id 失败")

            return

        self.set_user_version(HASH_ID_VERSION)

    def _rehash_all(self):
        # data 列中保存着完整的 task_info，可据此重算 hash_id，无需用户重新下载
        for table_name in ("download_task", "completed_task"):
            updates = []

            for task_id, data in self.query(f"SELECT task_id, data FROM {table_name}"):
                try:
                    task_info = TaskInfo()
                    task_info.from_dict(loads(data))

                except Exception:
                    # 单条记录损坏时跳过，不影响其余记录的重算
                    logger.exception("解析下载任务记录失败，已跳过: %s", task_id)

                    continue

                updates.append((self._calc_hash_id(task_info), task_id))

            if updates:
                self.executemany(f"UPDATE {table_name} SET hash_id = ? WHERE task_id = ?", updates)

                logger.info("已重算 %s 表中 %d 条记录的 hash_id", table_name, len(updates))

    def _needs_upgrade(self):
        required_columns = {"task_id", "hash_id", "cover_id", "title", "data"}

        for table_name in ("download_task", "completed_task"):
            column_names = self._get_table_columns(table_name)

            if not required_columns.issubset(column_names):
                return True

        # completed_task 需要 file_size 列，供分页按文件大小排序时走索引。
        if "file_size" not in self._get_table_columns("completed_task"):
            return True

        return False

    def _get_table_columns(self, table_name: str):
        result = self.query(f"PRAGMA table_info({table_name});")

        return {row[1] for row in result}

    def check_and_create_table(self):
        self.execute_script("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS "download_task" (
                "id"	INTEGER UNIQUE,
                "task_id"	TEXT UNIQUE,
                "hash_id"   TEXT,
                "cover_id"	TEXT,
                "title"	TEXT,
                "created_time"	INTEGER,
                "data"	TEXT,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
            CREATE TABLE IF NOT EXISTS "completed_task" (
                "id"	INTEGER UNIQUE,
                "task_id"	TEXT UNIQUE,
                "hash_id"   TEXT,
                "cover_id"	TEXT,
                "title"	TEXT,
                "completed_time"	INTEGER,
                "file_size"	INTEGER DEFAULT 0,
                "data"	TEXT,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
            """)

        # 旧版表可能还没有 hash_id，不能在迁移前直接创建索引。
        if "hash_id" in self._get_table_columns("download_task") and "hash_id" in self._get_table_columns("completed_task"):
            self.execute_script("""
                CREATE INDEX IF NOT EXISTS "idx_download_task_hash_id" ON "download_task" ("hash_id");
                CREATE INDEX IF NOT EXISTS "idx_completed_task_hash_id" ON "completed_task" ("hash_id");
                """)

        # 按时间倒序取最近若干条是列表查询的固定形态，没有索引时 SQLite 要全表扫加排序。
        # 索引不改变数据本身，CREATE INDEX IF NOT EXISTS 是幂等的，无需递增表结构版本
        self.execute_script("""
            CREATE INDEX IF NOT EXISTS "idx_download_task_created_time" ON "download_task" ("created_time");
            CREATE INDEX IF NOT EXISTS "idx_completed_task_completed_time" ON "completed_task" ("completed_time");
            """)

    def _create_bvid_index(self):
        # 收藏夹、个人空间等需要二次解析的条目解析时没有 cid，算不出 hash_id，
        # 只能按 bvid 去下载记录里找（见 count_parts_by_bvid）。bvid 不单独成列，
        # 而是对 data 中的 JSON 建表达式索引：不改表结构，也不必改动任何写入路径。
        #
        # 查询必须使用与这里逐字相同的表达式，SQLite 才会走这个索引
        try:
            self.execute_script("""
                CREATE INDEX IF NOT EXISTS "idx_download_task_bvid" ON "download_task" (json_extract("data", '$.Episode.bvid'));
                CREATE INDEX IF NOT EXISTS "idx_completed_task_bvid" ON "completed_task" (json_extract("data", '$.Episode.bvid'));
                """)

        except Exception:
            # 索引只影响查询速度。SQLite 缺少 JSON 函数时这里会失败，
            # 但绝不能因此让整个任务数据库初始化失败
            logger.exception("创建 bvid 索引失败")

    def _create_extra_indexes(self):
        # 升级会 DROP + CREATE 表，check_and_create_table 里建的时间索引随之丢失。
        # 这里在升级之后补建，CREATE INDEX IF NOT EXISTS 幂等，未升级时也不会重复建。
        # file_size 是本次新增的列，只有 completed_task 需要
        self.execute_script("""
            CREATE INDEX IF NOT EXISTS "idx_download_task_created_time" ON "download_task" ("created_time");
            CREATE INDEX IF NOT EXISTS "idx_completed_task_completed_time" ON "completed_task" ("completed_time");
            CREATE INDEX IF NOT EXISTS "idx_completed_task_file_size" ON "completed_task" ("file_size");
            """)

    def query_tasks(self, completed: bool = False, limit: int = None):
        """
        读取任务记录

        limit 为空时返回全部（界面启动时要恢复整个列表）。传入 limit 则按时间
        倒序只取最近的若干条 —— 已完成的任务是长期累积的，调用方只要最近几条时
        不该把几百条 JSON 全反序列化一遍。
        """
        table, order_column = ("completed_task", "completed_time") if completed else ("download_task", "created_time")

        if limit is None:
            return self.query(f'SELECT data FROM "{table}"')

        return self.query(
            f'SELECT data FROM "{table}" ORDER BY "{order_column}" DESC LIMIT ?', (limit,)
        )

    def query_completed_page(self, offset: int, limit: int, order_by: str = "completed_time", ascending: bool = False, keyword: str = ""):
        # 分页查询已完成任务。排序键走索引，SQLite 无需全表排序
        order_expr = self._COMPLETED_ORDER_COLUMNS.get(order_by, '"completed_time"')
        direction = "ASC" if ascending else "DESC"

        params = []
        where = ""

        if keyword:
            # 只搜标题与文件名。子串匹配用不上索引，界面层有 300 ms 防抖
            where = ' WHERE ("title" LIKE ? OR json_extract("data", \'$.File.name\') LIKE ?)'
            like = f"%{keyword}%"
            params.extend([like, like])

        sql = f'SELECT data FROM "completed_task"{where} ORDER BY {order_expr} {direction} LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        return self.query(sql, tuple(params))

    def count_completed(self, keyword: str = "") -> int:
        if keyword:
            like = f"%{keyword}%"
            result = self.query(
                'SELECT COUNT(*) FROM "completed_task" WHERE ("title" LIKE ? OR json_extract("data", \'$.File.name\') LIKE ?)',
                (like, like)
            )

        else:
            result = self.query('SELECT COUNT(*) FROM "completed_task"')

        return result[0][0] if result else 0

    def clear_completed(self):
        # 分页模式下「全部清除」必须清空整张表，而不是只清当前页的条目
        self.execute('DELETE FROM "completed_task"')

    def query_task_by_id(self, task_id: str, completed: bool = False):
        """按 task_id 直接取一条，task_id 上有 UNIQUE 约束，不必扫全表"""
        table = "completed_task" if completed else "download_task"

        return self.query(f'SELECT data FROM "{table}" WHERE "task_id" = ?', (task_id,))

    def count_tasks(self, completed: bool = False) -> int:
        table = "completed_task" if completed else "download_task"

        result = self.query(f'SELECT COUNT(*) FROM "{table}"')

        return result[0][0] if result else 0

    def build_record(self, task_info: TaskInfo, completed: bool = False) -> tuple:
        # 组装一条待写入的记录。调用方可在自己的线程上预先组装，避免写线程读到中途被改写的 task_info
        timestamp = task_info.Basic.completed_time if completed else task_info.Basic.created_time

        if not timestamp:
            timestamp = get_timestamp()

        if completed:
            # completed_task 表带 file_size 列，供分页按文件大小排序走索引
            return (
                task_info.Basic.task_id,                                    # task_id
                self._calc_hash_id(task_info),                              # hash_id
                task_info.Basic.cover_id,                                   # cover_id
                task_info.Basic.show_title,                                 # title
                timestamp,                                                  # completed_time
                task_info.Download.total_size or 0,                         # file_size
                dumps(task_info.to_dict())                                  # data
            )

        return (
            task_info.Basic.task_id,                                    # task_id
            self._calc_hash_id(task_info),                              # hash_id
            task_info.Basic.cover_id,                                   # cover_id
            task_info.Basic.show_title,                                 # title
            timestamp,                                                  # created_time
            dumps(task_info.to_dict())                                  # data
        )

    def add_tasks(self, task_info_list: List[TaskInfo], completed: bool = False):
        # 通过 completed 参数来区分是插入到 download_task 还是 completed_task 表
        self.add_task_records([self.build_record(task_info, completed) for task_info in task_info_list], completed)

    def add_task_records(self, info_list: List[tuple], completed: bool = False):
        # 记录由调用方预先组装，此处只负责写入，便于把写操作统一投递到写线程执行
        if not info_list:
            return

        if completed:
            self.executemany("""
                INSERT INTO completed_task (task_id, hash_id, cover_id, title, completed_time, file_size, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, info_list)
        else:
            self.executemany("""
                INSERT INTO download_task (task_id, hash_id, cover_id, title, created_time, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, info_list)

    def update_task(self, task_info: TaskInfo):
        self.execute("""
            UPDATE download_task SET data = ? WHERE task_id = ?
        """, (dumps(task_info.to_dict()), task_info.Basic.task_id))

    def update_task_json(self, task_id: str, data: str):
        self.execute("""
            UPDATE download_task SET data = ? WHERE task_id = ?
        """, (data, task_id))

    def update_task_json_many(self, updates: List[tuple]):
        # updates 中每一项为 (task_id, data)，在单个事务中一次性提交
        if not updates:
            return

        self.executemany("""
            UPDATE download_task SET data = ? WHERE task_id = ?
        """, [(data, task_id) for task_id, data in updates])

    def delete_task(self, task_id: str, completed: bool = False):
        self.delete_tasks([task_id], completed)

    def delete_tasks(self, task_id_list: List[str], completed: bool = False):
        # 批量删除，避免逐条提交事务
        if not task_id_list:
            return

        table = "completed_task" if completed else "download_task"

        # SQLITE_MAX_VARIABLE_NUMBER 默认下限为 999，分批处理以保证安全
        for index in range(0, len(task_id_list), 500):
            batch = task_id_list[index:index + 500]
            placeholders = ", ".join("?" * len(batch))

            self.execute(f"DELETE FROM {table} WHERE task_id IN ({placeholders})", tuple(batch))

    def move_to_completed(self, record: tuple):
        # 从下载中表移出并写入已完成表，两步在同一事务内完成，避免中途失败导致任务丢失
        self.execute_batch([
            ("DELETE FROM download_task WHERE task_id = ?", (record[0],)),
            ("""
                INSERT OR REPLACE INTO completed_task (task_id, hash_id, cover_id, title, completed_time, file_size, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, record)
        ])

    def recreate_task(self, record: tuple):
        # 从已完成表移回下载中表，同样在单个事务内完成
        self.execute_batch([
            ("DELETE FROM completed_task WHERE task_id = ?", (record[0],)),
            ("""
                INSERT OR REPLACE INTO download_task (task_id, hash_id, cover_id, title, created_time, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, record)
        ])

    def check_duplicate(self, hash_id: str):
        # 合并为一次查询，避免两次独立的数据库往返
        result = self.query("""
            SELECT
                EXISTS(SELECT 1 FROM completed_task WHERE hash_id = ?)
                OR EXISTS(SELECT 1 FROM download_task WHERE hash_id = ?)
        """, (hash_id, hash_id))

        return bool(result and result[0][0])

    def filter_existing_hash_ids(self, hash_ids) -> set:
        """
        从给定的 hash_id 中筛出已存在于下载记录中的那些，口径与 check_duplicate 一致

        解析列表一次可能有上千条，逐条调用 check_duplicate 就是上千次数据库往返，
        这里按 IN 批量查询。每批 400 个，两张表合计 800 个参数，
        低于旧版 SQLite 999 个绑定参数的上限
        """
        hash_ids = list(hash_ids)
        existing = set()

        for start in range(0, len(hash_ids), 400):
            chunk = hash_ids[start:start + 400]
            placeholders = ", ".join("?" * len(chunk))

            result = self.query(f"""
                SELECT hash_id FROM completed_task WHERE hash_id IN ({placeholders})
                UNION
                SELECT hash_id FROM download_task WHERE hash_id IN ({placeholders})
            """, (*chunk, *chunk))

            existing.update(row[0] for row in result)

        return existing

    def count_parts_by_bvid(self, bvids) -> dict:
        """
        按 bvid 统计下载记录中各稿件已有多少个不同的分P（cid），口径同样覆盖两张表

        用于判定需要二次解析的条目：它们二次解析时会一次性为稿件的全部分P建任务，
        有记录即说明下载过；与分P总数比较，还能看出是否只下过其中一部分
        """
        bvids = list(bvids)
        counts = {}

        for start in range(0, len(bvids), 400):
            chunk = bvids[start:start + 400]
            placeholders = ", ".join("?" * len(chunk))

            result = self.query(f"""
                SELECT bvid, COUNT(DISTINCT cid) FROM (
                    SELECT json_extract("data", '$.Episode.bvid') AS bvid, json_extract("data", '$.Episode.cid') AS cid
                    FROM completed_task WHERE json_extract("data", '$.Episode.bvid') IN ({placeholders})
                    UNION ALL
                    SELECT json_extract("data", '$.Episode.bvid') AS bvid, json_extract("data", '$.Episode.cid') AS cid
                    FROM download_task WHERE json_extract("data", '$.Episode.bvid') IN ({placeholders})
                )
                GROUP BY bvid
            """, (*chunk, *chunk))

            counts.update({bvid: count for bvid, count in result})

        return counts

    def _upgrade(self):
        def _to_task_list(result):
            _task_info_list = []

            for entry in result:
                task_info = TaskInfo()
                task_info.from_dict(loads(entry[0]))

                _task_info_list.append(task_info)

            return _task_info_list

        if not self._needs_upgrade():
            logger.info("数据库已是最新版本，无需升级")
            return

        # 取出原有数据
        download_tasks = self.query_tasks(completed = False)
        completed_tasks = self.query_tasks(completed = True)

        download_task_list = _to_task_list(download_tasks)
        completed_task_list = _to_task_list(completed_tasks)

        def _task_records(task_info_list: List[TaskInfo], completed: bool):
            records = []

            for task_info in task_info_list:
                timestamp = task_info.Basic.completed_time if completed else task_info.Basic.created_time

                if not timestamp:
                    timestamp = get_timestamp()

                if completed:
                    records.append((
                        task_info.Basic.task_id,
                        self._calc_hash_id(task_info),
                        task_info.Basic.cover_id,
                        task_info.Basic.show_title,
                        timestamp,
                        task_info.Download.total_size or 0,
                        dumps(task_info.to_dict())
                    ))

                else:
                    records.append((
                        task_info.Basic.task_id,
                        self._calc_hash_id(task_info),
                        task_info.Basic.cover_id,
                        task_info.Basic.show_title,
                        timestamp,
                        dumps(task_info.to_dict())
                    ))

            return records

        download_records = _task_records(download_task_list, completed = False)
        completed_records = _task_records(completed_task_list, completed = True)

        # 在同一个事务中重建表，避免迁移中途失败后留下空表或半成品表。
        conn = self.get_connection()

        with conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN")

            cursor.execute("DROP TABLE IF EXISTS download_task")
            cursor.execute("DROP TABLE IF EXISTS completed_task")

            cursor.execute("""
                CREATE TABLE download_task (
                    id INTEGER UNIQUE,
                    task_id TEXT UNIQUE,
                    hash_id TEXT,
                    cover_id TEXT,
                    title TEXT,
                    created_time INTEGER,
                    data TEXT,
                    PRIMARY KEY(id AUTOINCREMENT)
                )
            """)
            cursor.execute("""
                CREATE TABLE completed_task (
                    id INTEGER UNIQUE,
                    task_id TEXT UNIQUE,
                    hash_id TEXT,
                    cover_id TEXT,
                    title TEXT,
                    completed_time INTEGER,
                    file_size INTEGER DEFAULT 0,
                    data TEXT,
                    PRIMARY KEY(id AUTOINCREMENT)
                )
            """)
            cursor.execute("CREATE INDEX idx_download_task_hash_id ON download_task (hash_id)")
            cursor.execute("CREATE INDEX idx_completed_task_hash_id ON completed_task (hash_id)")

            cursor.executemany("""
                INSERT INTO download_task (task_id, hash_id, cover_id, title, created_time, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, download_records)
            cursor.executemany("""
                INSERT INTO completed_task (task_id, hash_id, cover_id, title, completed_time, file_size, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, completed_records)

            conn.commit()

    def _calc_hash_id(self, task_info: TaskInfo):
        # 根据 task_info 计算 hash_id
        return calc_hash_id(
            task_info.Episode.attribute,
            aid = task_info.Episode.aid,
            bvid = task_info.Episode.bvid,
            cid = task_info.Episode.cid,
            ep_id = task_info.Episode.ep_id,
            sid = task_info.Episode.sid,
            task_id = task_info.Basic.task_id,
            course_id = task_info.Episode.course_id,
            lesson_id = task_info.Episode.lesson_id,
            item_id = task_info.Episode.item_id,
            section_id = task_info.Episode.section_id
        )