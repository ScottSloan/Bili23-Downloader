from util.common import appdata_path, Database, get_timestamp

from pathlib import Path

class CoverDatabase(Database):
    def __init__(self):
        self.path = Path(appdata_path) / "Bili23 Downloader" / "thumbnail.db"

        self.check_and_create_table()

        self.check_database_size()

    def check_database_size(self):
        threshold = 75 * 1024 * 1024   # 75MB

        # 超过阈值则自动清空数据库
        if self.path.exists() and self.path.stat().st_size > threshold:
            self.execute("DELETE FROM thumbnail")

    def check_and_create_table(self):
        self.execute_script("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS "thumbnail" (
                "id"	INTEGER UNIQUE,
                "cover_id"	TEXT UNIQUE,
                "created_time"	INTEGER,
                "cover"	BLOB,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
        """)

    def query_cover(self, cover_id: str):
        result = self.query("""
            SELECT cover FROM thumbnail WHERE cover_id = ?
        """, (cover_id,))

        if result:
            return result[0][0]
        else:
            return None
        
    def add_cover(self, cover_id: str, cover_data: bytes):
        self.execute("""
            INSERT INTO thumbnail (cover_id, created_time, cover) VALUES (?, ?, ?)
        """, (cover_id, get_timestamp(), cover_data))