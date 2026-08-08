from threading import local, Lock
import sqlite3

_storage_lock = Lock()

class Database:
    # 单次写入若每次新建连接，关闭时会触发 WAL checkpoint 与 fsync，实测约 18ms／次；
    # 改为每个线程持有一个长连接后降至 0.13ms，配合 synchronous = NORMAL 可进一步降至 0.006ms。
    timeout = 30

    def __init__(self):
        self.path = ""

    def _get_storage(self) -> local:
        # 子类通常不会调用 super().__init__()，此处兼容性地惰性创建线程本地存储
        storage = getattr(self, "_storage", None)

        if storage is None:
            with _storage_lock:
                storage = getattr(self, "_storage", None)

                if storage is None:
                    storage = local()

                    self._storage = storage

        return storage

    def get_connection(self) -> sqlite3.Connection:
        # sqlite3 连接不允许跨线程使用，因此每个线程各自持有一个长连接。
        # WAL 模式下多连接读写互不阻塞，写入之间由 SQLite 自身串行化。
        storage = self._get_storage()

        conn = getattr(storage, "conn", None)

        if conn is None:
            conn = sqlite3.connect(self.path, timeout = self.timeout)

            # 切换 journal_mode 需要短暂地取得排他锁，而 QThreadPool 的线程是短命的，
            # 频繁建连时这一步会与真正的写入互相阻塞。已经是 WAL 时直接跳过。
            mode = conn.execute("PRAGMA journal_mode").fetchone()

            if not mode or str(mode[0]).lower() != "wal":
                conn.execute("PRAGMA journal_mode = WAL")

            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute(f"PRAGMA busy_timeout = {int(self.timeout * 1000)}")

            storage.conn = conn

        return conn

    def close_connection(self):
        # 关闭当前线程持有的连接，仅在明确需要释放数据库文件时调用
        storage = self._get_storage()

        conn = getattr(storage, "conn", None)

        if conn is not None:
            storage.conn = None

            conn.close()

    def query(self, query: str, params: tuple = ()):
        conn = self.get_connection()

        return conn.execute(query, params).fetchall()

    def execute(self, query: str, params: tuple = ()):
        conn = self.get_connection()

        with conn:
            conn.execute(query, params)

    def executemany(self, query: str, params_list: list[tuple]):
        if not params_list:
            return

        conn = self.get_connection()

        with conn:
            conn.executemany(query, params_list)

    def execute_batch(self, statements: list[tuple]):
        # 在单个事务中执行多条语句，避免逐条提交带来的多次 fsync。
        # statements 中每一项为 (query, params) 或 (query, params_list, True) 形式
        if not statements:
            return

        conn = self.get_connection()

        with conn:
            for statement in statements:
                if len(statement) == 3 and statement[2]:
                    conn.executemany(statement[0], statement[1])
                else:
                    conn.execute(statement[0], statement[1])

    def execute_script(self, script: str):
        conn = self.get_connection()

        with conn:
            conn.executescript(script)

    def get_user_version(self) -> int:
        # 借助 SQLite 自带的 user_version 记录数据结构版本，避免与配置文件的版本号耦合
        result = self.query("PRAGMA user_version")

        return int(result[0][0]) if result else 0

    def set_user_version(self, version: int):
        conn = self.get_connection()

        # PRAGMA 不支持参数绑定，因此在拼接前强制转换为整数
        with conn:
            conn.execute(f"PRAGMA user_version = {int(version)}")

    def vacuum(self):
        # VACUUM 无法在事务中执行，先提交挂起的事务再回收空间
        conn = self.get_connection()

        conn.commit()
        conn.execute("VACUUM")
