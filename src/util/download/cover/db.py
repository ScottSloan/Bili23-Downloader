from ...common.timestamp import get_timestamp
from ...common.config import appdata_path
from ...common.database import Database

from pathlib import Path
from threading import Thread
import logging

logger = logging.getLogger(__name__)

class CoverDatabase(Database):
    def __init__(self):
        super().__init__()

        self.path = Path(appdata_path) / "Bili23 Downloader" / "thumbnail.db"
        self.path.parent.mkdir(parents = True, exist_ok = True)

        self.check_and_create_table()

        self.check_database_size()

    def check_database_size(self):
        threshold = 75 * 1024 * 1024   # 75MB

        # 超过阈值则自动清空数据库。清理放到后台线程执行，避免阻塞启动过程
        if self.path.exists() and self.path.stat().st_size > threshold:
            thread = Thread(target = self._clear_database, name = "cover-db-cleanup", daemon = True)
            thread.start()

    def _clear_database(self):
        try:
            self.execute("DELETE FROM thumbnail")

            # 仅 DELETE 并不会缩小数据库文件，否则每次启动都会重复触发清理
            self.vacuum()

            logger.info("封面缓存数据库已超过阈值，已清空并回收空间")

        except Exception:
            logger.exception("清理封面缓存数据库失败")

        finally:
            # 清理线程即将退出，及时释放其持有的连接
            self.close_connection()

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
