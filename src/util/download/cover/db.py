from ...common.timestamp import get_timestamp
from ...common.config import appdata_path
from ...common.database import Database

from pathlib import Path
from threading import Thread
import logging

logger = logging.getLogger(__name__)

# 容量上限。封面已改为按设备像素存放（DPR 1.5 下单张体积约为原先的 2.7 倍），
# 阈值同步放宽 —— 每次触发都是全量清空，会让列表封面集体重新加载一遍
COVER_DB_SIZE_THRESHOLD = 150 * 1024 * 1024

# 这里没有格式版本号，也不需要迁移：缓存的键已经并入像素尺寸
# （见 CoverManager.arrange_cover_key），改尺寸后旧行对应的键再也查不到，
# 天然失效并随容量清理回收；只改压缩质量或存储格式而不动尺寸时，
# 读取侧的格式校验会把旧值判为无效并重新下载，再经 INSERT OR REPLACE 覆盖掉。
# 封面本就是可再生的缓存，不必像 task.db 那样维护 HASH_ID_VERSION 那类版本迁移

class CoverDatabase(Database):
    def __init__(self):
        super().__init__()

        self.path = Path(appdata_path) / "Bili23 Downloader" / "thumbnail.db"
        self.path.parent.mkdir(parents = True, exist_ok = True)

        self.check_and_create_table()

        self.check_database_size()

    def check_database_size(self):
        # 超过阈值则自动清空数据库。清理放到后台线程执行，避免阻塞启动过程
        if self.path.exists() and self.path.stat().st_size > COVER_DB_SIZE_THRESHOLD:
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

    def query_cover(self, cover_key: str):
        result = self.query("""
            SELECT cover FROM thumbnail WHERE cover_id = ?
        """, (cover_key,))

        if result:
            return result[0][0]
        else:
            return None
        
    def add_cover(self, cover_key: str, cover_data: bytes):
        # cover_id 列存的是 cover_id 与像素尺寸拼成的复合键（见 CoverManager.arrange_cover_key），
        # 列名沿用不改，避免为了改名重建表。cover 列直接存 webp 原始字节
        #
        # 用 OR REPLACE 而非裸 INSERT：查询返回空值时是假值，会让调用方每次都重新下载、
        # 每次写入都撞 UNIQUE，那行脏数据将永远无法被覆盖。REPLACE 让后续每次成功下载
        # 都能自愈。id 是 AUTOINCREMENT 会被换掉，但没有任何外部引用
        self.execute("""
            INSERT OR REPLACE INTO thumbnail (cover_id, created_time, cover) VALUES (?, ?, ?)
        """, (cover_key, get_timestamp(), cover_data))
