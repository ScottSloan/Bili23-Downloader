import sqlite3

class Database:
    def __init__(self):
        self.path = ""

    def query(self, query: str, params: tuple = ()):
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        
    def execute(self, query: str, params: tuple = ()):
        import logging
        logger = logging.getLogger(__name__)
        try:
            conn = sqlite3.connect(self.path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            logger.info(f"SQL 执行成功: {query[:50]}... 影响行数: {cursor.rowcount}")
        except Exception as e:
            logger.error(f"SQL 执行失败: {query[:50]}... 错误: {e}")
            raise
        finally:
            conn.close()

    def executemany(self, query: str, params_list: list[tuple]):
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()

    def execute_script(self, script: str):
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.executescript(script)
            conn.commit()