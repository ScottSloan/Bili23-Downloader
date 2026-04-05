from util.common import Database, appdata_path, get_timestamp

from pathlib import Path
from uuid import uuid4

class HistoryDatabase(Database):
    def __init__(self):
        self.path = Path(appdata_path) / "Bili23 Downloader" / "history.db"

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

        # 1. 删除已存在的相同 URL 的记录（如果有的话）
        self.execute("""
            DELETE FROM history WHERE url = ?
        """, (url,))

        # 2.插入新记录
        self.execute("""
            INSERT INTO history (history_id, title, url, type, created_time) VALUES (?, ?, ?, ?, ?)
        """, (history_id, title, url, type, get_timestamp()))

        # 3.保留最新的 max_length 条记录，删除更旧的数据
        self.execute("""
            DELETE FROM history 
            WHERE id NOT IN (
                SELECT id FROM history ORDER BY created_time DESC LIMIT ?
            )
        """, (self.max_length,))

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
        self.db_manager = HistoryDatabase()

    def add_history(self, title: str, url: str, type: str):
        self.db_manager.add(title, url, type)

    def get_history(self):
        return self.db_manager.query_all()
    
    def delete_history(self, history_id: str):
        self.db_manager.delete(history_id)

history_manager = HistoryManager()
