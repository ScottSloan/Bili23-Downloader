from util.common.timestamp import get_timestamp
from util.common.config import appdata_path
from util.common.database import Database

from pathlib import Path

class CoverDatabase(Database):
    def __init__(self):
        self.path = Path(appdata_path) / "Bili23 Downloader" / "thumbnail.db"

        self.check_and_create_table()

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