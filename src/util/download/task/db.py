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
    # 三个键都有对应索引，走索引时 SQLite 直接取前 N 条，不需要对全表排序。
    # title 的索引必须带 COLLATE NOCASE，否则普通（BINARY）索引无法匹配这里的
    # ORDER BY "title" COLLATE NOCASE，SQLite 会退化为全表排序。
    #
    # 新增排序键时必须同步更新三处：本映射、_create_extra_indexes 的索引、
    # config.completed_list_sort_by 的 OptionsValidator，否则新键会静默回落到
    # completed_time
    _COMPLETED_ORDER_COLUMNS = {
        "completed_time": '"completed_time"',
        "show_title": '"title" COLLATE NOCASE',
        "file_size": '"file_size"',
    }

    # 已完成列表的搜索字段：与旧版客户端 _getSearchableText 逐字对应。
    # title 是 completed_task 的普通列，其余 8 个字段从 data JSON 中提取。
    # 子串匹配用不上索引，每次查询是全表扫 + N×9 次 LIKE，界面层有 300 ms 防抖。
    #
    # 新增搜索字段时必须同步更新客户端 proxy_model._getSearchableText，
    # 否则旧版全量模式下能搜到的字段在分页模式下会搜不到
    _COMPLETED_SEARCH_FIELDS = (
        '"title"',
        'json_extract("data", \'$.File.name\')',
        'json_extract("data", \'$.Episode.uploader\')',
        'json_extract("data", \'$.Episode.bvid\')',
        'json_extract("data", \'$.Episode.parent_title\')',
        'json_extract("data", \'$.Episode.collection_title\')',
        'json_extract("data", \'$.Episode.series_title\')',
        'json_extract("data", \'$.Episode.season_title\')',
        'json_extract("data", \'$.Episode.favorites_name\')',
    )

    def __init__(self):
        super().__init__()

        self.path = Path(appdata_path) / "Bili23 Downloader" / "task.db"
        self.path.parent.mkdir(parents = True, exist_ok = True)

        # 升级失败标记：旧库首次启动走 _upgrade() 时若失败（磁盘满、只读文件系统、
        # 进程被 kill），不抛异常让应用无法启动，而是标记本字段。
        # 已完成列表相关的读接口返回空/0，写接口直接 return，用户至少能正常打开
        # 应用、使用下载中列表。再次启动会重试升级，成功则恢复正常
        self.upgrade_failed = False

        self.check_and_create_table()

        self._check_should_upgrade()

        # 放在升级之后：旧版库升级时会重建两张表，先建的索引会随旧表一起消失
        self._create_bvid_index()
        self._create_extra_indexes()

    def _check_should_upgrade(self):
        # 配置版本与任务数据库版本并不等价。始终检查实际表结构，
        # 避免配置升级成功但数据库迁移失败后永久跳过迁移。
        if not self._needs_upgrade():
            self._check_should_rehash()
            return

        logger.info("检测到旧版下载任务数据库，正在进行升级")

        try:
            self._upgrade()

        except Exception:
            # 升级失败不抛出：TaskDatabase.__init__ 是 TaskManager.__init__ 的
            # 同步调用，异常传播出去会让应用直接启动失败。降级为「已完成列表
            # 不可用」让应用能起来，由 DownloadInterface 提示用户
            logger.exception("升级下载任务数据库失败，已完成列表将不可用")

            self.upgrade_failed = True
            return

        # 升级时已按当前算法重算过 hash_id，直接打上版本号
        self.set_user_version(HASH_ID_VERSION)

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
        # hash_id 索引依赖 hash_id 列存在，所以必须留在这里单独判断。
        #
        # 其他索引（created_time / completed_time / title / file_size）全部放到
        # _create_extra_indexes（带 try/except），避免这里建索引失败让
        # TaskDatabase.__init__ 抛异常 —— 与 _create_bvid_index 的保护一致
        if "hash_id" in self._get_table_columns("download_task") and "hash_id" in self._get_table_columns("completed_task"):
            self.execute_script("""
                CREATE INDEX IF NOT EXISTS "idx_download_task_hash_id" ON "download_task" ("hash_id");
                CREATE INDEX IF NOT EXISTS "idx_completed_task_hash_id" ON "completed_task" ("hash_id");
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
        # 所有非 hash_id / bvid 的索引都集中在这里，统一用 try/except 保护：
        # 索引只影响查询速度，失败不应让 TaskDatabase.__init__ 抛异常。
        #
        # 升级会 DROP + CREATE 表，先建的索引会随旧表一起消失，
        # 所以本方法必须在 _check_should_upgrade 之后调用。
        #
        # 下载中列表与已完成列表的索引分开 try/except：已完成列表的某个索引
        # 因列缺失等原因失败时，不影响下载中列表索引创建
        try:
            self.execute_script("""
                CREATE INDEX IF NOT EXISTS "idx_download_task_created_time" ON "download_task" ("created_time");
                """)

        except Exception:
            logger.exception("创建下载中列表索引失败")

        try:
            self.execute_script("""
                CREATE INDEX IF NOT EXISTS "idx_completed_task_completed_time" ON "completed_task" ("completed_time");
                CREATE INDEX IF NOT EXISTS "idx_completed_task_file_size" ON "completed_task" ("file_size");
                CREATE INDEX IF NOT EXISTS "idx_completed_task_title" ON "completed_task" ("title" COLLATE NOCASE);
                """)

        except Exception:
            logger.exception("创建已完成列表索引失败")

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

    @staticmethod
    def _escape_like(value: str) -> str:
        # SQLite LIKE 里 % 与 _ 是通配符，反斜杠是默认的转义字符。
        # 不转义的话用户输入 "%" 会匹配所有记录，而 delete_completed_by_filter("%")
        # 会清空整表 —— 原版 proxy 用 Python 的 `in` 是字面匹配，这里必须对齐
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _build_search_clause(self, keyword: str):
        """
        构造已完成任务的关键词 WHERE 子句

        语义与旧版客户端 _getSearchableText 一致：空格分词，每个词都要命中，
        每个词可以落在任意一个字段里。整串当作一个 keyword 会把「UP主名 合集名」
        变成含中间空格的子串匹配，多关键词 AND 的能力就丢了。
        """
        keywords = keyword.strip().casefold().split()

        if not keywords:
            return "", []

        keyword_clauses = []
        params = []

        for kw in keywords:
            like = f"%{self._escape_like(kw)}%"
            clauses = [f"{field} LIKE ? ESCAPE '\\'" for field in self._COMPLETED_SEARCH_FIELDS]

            keyword_clauses.append(f"({' OR '.join(clauses)})")
            params.extend([like] * len(self._COMPLETED_SEARCH_FIELDS))

        return " AND ".join(keyword_clauses), params

    @staticmethod
    def _build_media_type_sql(media_types) -> str:
        """
        把客户端 get_media_type_key 的优先级链翻译成 SQL

        客户端判定是一个互斥的分派：AUDIO > COURSE > BANGUMI > INTERACTIVE > VIDEO。
        每个类别必须显式排除前面更高优先级的类别，否则一条同时带多个属性位的记录
        会同时落入多个类别，筛选结果与封面角标对不上。

        UI 的 get_media_type_group_dict 只提供四个组：
        VIDEO / BANGUMI / COURSE / AUDIO。其中 VIDEO 组同时包含 VIDEO 与
        INTERACTIVE 两个 key（互动视频归在「视频」里，不单列选项）。
        先把传入的 key 集合规范化回这四个组，避免同一组被拆成多个 OR 条件
        """
        if not media_types:
            return ""

        # 惰性导入：util.download.task.db 被 main.py 的导入链间接加载，如果在模块顶层
        # 导入 parse.episode.tree，会把整条解析链拖进启动路径（实测约 0.2 秒）。
        # DownloadType 同理，util.common.enum 本身不重，但和 Attribute 成对出现更清楚。
        # 不要"优化"成顶部导入
        from ...parse.episode.tree import Attribute
        from ...common.enum import DownloadType

        # 规范化回 UI 的四个组：INTERACTIVE 是 VIDEO 组的成员
        groups = set()

        if "VIDEO" in media_types or "INTERACTIVE" in media_types:
            groups.add("VIDEO")
        if "BANGUMI" in media_types:
            groups.add("BANGUMI")
        if "COURSE" in media_types:
            groups.add("COURSE")
        if "AUDIO" in media_types:
            groups.add("AUDIO")

        if not groups:
            return ""

        attr = 'CAST(json_extract("data", \'$.Episode.attribute\') AS INTEGER)'
        dtype = 'CAST(json_extract("data", \'$.Download.type\') AS INTEGER)'

        video_bit = int(DownloadType.VIDEO)
        audio_bit = int(DownloadType.AUDIO)

        aud_attr_bit = int(Attribute.AUDIO_BIT)
        cheese_lesson_bits = int(Attribute.CHEESE_BIT) | int(Attribute.LESSON_BIT)
        bangumi_bit = int(Attribute.BANGUMI_BIT)
        interactive_bit = int(Attribute.INTERACTIVE_BIT)
        video_attr_bit = int(Attribute.VIDEO_BIT)

        # audio_only = (type & AUDIO) != 0 AND (type & VIDEO) == 0
        audio_only = f'(({dtype} & {audio_bit}) != 0 AND ({dtype} & {video_bit}) == 0)'
        is_audio = f'({audio_only} OR ({attr} & {aud_attr_bit}) != 0)'

        # 后续每一类都要排除前面所有更高优先级的类别，保证互斥
        course_pre = f'(({attr} & {cheese_lesson_bits}) != 0)'
        is_course = f'(NOT {is_audio} AND {course_pre})'

        bangumi_pre = f'(({attr} & {bangumi_bit}) != 0)'
        is_bangumi = f'(NOT {is_audio} AND NOT {course_pre} AND {bangumi_pre})'

        interactive_pre = f'(({attr} & {interactive_bit}) != 0)'
        is_interactive = f'(NOT {is_audio} AND NOT {course_pre} AND NOT {bangumi_pre} AND {interactive_pre})'

        video_pre = f'(({attr} & {video_attr_bit}) != 0)'
        is_video = f'(NOT {is_audio} AND NOT {course_pre} AND NOT {bangumi_pre} AND NOT {interactive_pre} AND {video_pre})'

        # VIDEO 组同时命中视频与互动视频，与封面角标一致
        group_clauses = []

        if "AUDIO" in groups:
            group_clauses.append(is_audio)
        if "COURSE" in groups:
            group_clauses.append(is_course)
        if "BANGUMI" in groups:
            group_clauses.append(is_bangumi)
        if "VIDEO" in groups:
            group_clauses.append(f'({is_video} OR {is_interactive})')

        return "(" + " OR ".join(group_clauses) + ")"

    def _build_filter_clause(self, keyword: str = "", media_types = None):
        """
        构造已完成任务的完整筛选 WHERE 子句：关键词 AND 媒体类型

        与旧版 proxy 的 _batchTargets 语义一致：关键词和媒体筛选同时生效时
        是 AND 关系。keywords 为空时只按媒体类型筛，media_types 为空时只按
        关键词筛，都为空时返回 ("", []) 表示不筛。
        """
        clauses = []
        params = []

        if keyword:
            keyword_sql, keyword_params = self._build_search_clause(keyword)

            if keyword_sql:
                clauses.append(f"({keyword_sql})")
                params.extend(keyword_params)

        if media_types:
            media_sql = self._build_media_type_sql(media_types)

            if media_sql:
                clauses.append(media_sql)

        if not clauses:
            return "", []

        return " AND ".join(clauses), params

    def query_completed_page(
        self,
        offset: int,
        limit: int,
        order_by: str = "completed_time",
        ascending: bool = False,
        keyword: str = "",
        media_types = None,
    ):
        # 升级失败的库：completed_task 表结构不对，任何查询都会报错。
        # 直接返回空列表，让 UI 显示「No completed downloads」而不是崩溃
        if self.upgrade_failed:
            return []

        # 未定义的排序键静默回落到 completed_time，记一条 warning 便于排查
        if order_by not in self._COMPLETED_ORDER_COLUMNS:
            logger.warning("未知的已完成列表排序键 %r，回落到 completed_time", order_by)
            order_by = "completed_time"

        order_expr = self._COMPLETED_ORDER_COLUMNS[order_by]
        direction = "ASC" if ascending else "DESC"

        where_sql, where_params = self._build_filter_clause(keyword, media_types)

        where = f" WHERE {where_sql}" if where_sql else ""

        # 必须以 "id" 作为次级排序键：同值时 SQLite 不保证稳定顺序，
        # 分页时同一行可能出现在两页，或某行永远不出现在任何页。
        # id 是自增主键，唯一且单调，作为 tie-breaker 永远稳定
        sql = f'SELECT data FROM "completed_task"{where} ORDER BY {order_expr} {direction}, "id" {direction} LIMIT ? OFFSET ?'

        params = list(where_params) + [limit, offset]

        return self.query(sql, tuple(params))

    def count_completed(self, keyword: str = "", media_types = None) -> int:
        if self.upgrade_failed:
            return 0

        where_sql, params = self._build_filter_clause(keyword, media_types)

        where = f" WHERE {where_sql}" if where_sql else ""

        result = self.query(f'SELECT COUNT(*) FROM "completed_task"{where}', tuple(params))

        return result[0][0] if result else 0

    def clear_completed(self):
        if self.upgrade_failed:
            return

        # 分页模式下「全部清除」必须清空整张表，而不是只清当前页的条目
        self.execute('DELETE FROM "completed_task"')

    def delete_completed_by_filter(self, keyword: str = "", media_types = None):
        """
        按筛选条件删除已完成任务

        关键词和媒体类型同时存在时是 AND 关系，与旧版 proxy 的 _batchTargets
        语义一致。都为空时退回清空整表。
        """
        if self.upgrade_failed:
            return

        where_sql, params = self._build_filter_clause(keyword, media_types)

        if not where_sql:
            self.clear_completed()
            return

        self.execute(f'DELETE FROM "completed_task" WHERE {where_sql}', tuple(params))

    def delete_completed_by_keyword(self, keyword: str = ""):
        # 兼容旧调用方与测试；生产路径请用 delete_completed_by_filter。
        # 保留这个薄包装是因为 test_completed_pagination_db.py 里有一个用例
        # 专门验证它仍然工作，新代码不应再调
        self.delete_completed_by_filter(keyword, None)

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

    def move_to_completed(self, record: tuple) -> bool:
        # 升级失败的库：completed_task 表仍缺 file_size 列（升级事务已回滚），
        # 写入 7 元组会 SQL 报错。这里直接返回 False，让调用方知道归档被跳过，
        # 任务留在 download_task 里，重启并升级成功后会重新出现为「下载中」，
        # 用户可以重新处理。不做 DELETE + INSERT 的「半截操作」，
        # 避免 DELETE 已提交、INSERT 失败导致任务记录永久丢失
        if self.upgrade_failed:
            logger.warning("数据库升级失败，跳过归档: %s", record[0])
            return False

        # 从下载中表移出并写入已完成表，两步在同一事务内完成，避免中途失败导致任务丢失。
        # record 是 build_record(task_info, completed=True) 的 7 元组
        self.execute_batch([
            ("DELETE FROM download_task WHERE task_id = ?", (record[0],)),
            ("""
                INSERT OR REPLACE INTO completed_task (task_id, hash_id, cover_id, title, completed_time, file_size, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, record)
        ])

        return True

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