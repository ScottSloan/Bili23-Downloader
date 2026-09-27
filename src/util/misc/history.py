from ..common.timestamp import get_timestamp
from ..common.config import appdata_path
from ..common.database import Database

from pathlib import Path
from uuid import uuid4

class HistoryDatabase(Database):
    def __init__(self):
        super().__init__()

        self.path = Path(appdata_path) / "Bili23 Downloader" / "history.db"
        # 与 TaskDatabase、CoverDatabase 保持一致：自己确保目录存在。
        # history_manager 在模块导入期就建库，此前该目录是靠 main.py 创建
        # 日志目录时顺带建出来的，等于隐式依赖了启动顺序
        self.path.parent.mkdir(parents = True, exist_ok = True)

        self.max_length = 100

        self.check_and_create_table()

    def check_and_create_table(self):
        self.execute_script("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS "history" (
                "id"	INTEGER UNIQUE,
                "history_id"	TEXT UNIQUE,
                "title" TEXT,
                "url"	TEXT,
                "type"	TEXT,
                "created_time"	INTEGER,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
        """)

    def query_all(self):
        return self.query("""
            SELECT history_id, title, url, type, created_time FROM history ORDER BY created_time DESC
        """)

    def add(self, title: str, url: str, type: str):
        history_id = str(uuid4())

        # 三条语句合并到单个事务中提交，避免三次独立的写入开销
        self.execute_batch([
            # 1. 删除已存在的相同 URL 的记录（如果有的话）
            ("DELETE FROM history WHERE url = ?", (url,)),

            # 2.插入新记录
            ("""
                INSERT INTO history (history_id, title, url, type, created_time) VALUES (?, ?, ?, ?, ?)
            """, (history_id, title, url, type, get_timestamp())),

            # 3.保留最新的 max_length 条记录，删除更旧的数据
            ("""
                DELETE FROM history
                WHERE id NOT IN (
                    SELECT id FROM history ORDER BY created_time DESC LIMIT ?
                )
            """, (self.max_length,))
        ])

    def delete(self, history_id: str):
        self.execute("""
            DELETE FROM history WHERE history_id = ?
        """, (history_id,))

    def clear(self):
        self.execute("""
            DELETE FROM history
        """)

class HistoryManager:
    def __init__(self):
        # 惰性建库：HistoryDatabase 的构造会连库、建表并切到 WAL 模式，
        # 而本模块被解析界面在模块级引入，这笔开销原本落在启动路径上。
        # 解析历史是用户可能整轮都不会打开的功能，推迟到首次真正使用时再付
        self._db_manager = None

    @property
    def db_manager(self):
        if self._db_manager is None:
            self._db_manager = HistoryDatabase()

        return self._db_manager

    def add_history(self, title: str, url: str, type: str):
        self.db_manager.add(title, url, type)

    def get_history(self):
        return self.db_manager.query_all()
    
    def delete_history(self, history_id: str):
        self.db_manager.delete(history_id)

    def clear_history(self):
        self.db_manager.clear()

history_manager = HistoryManager()
