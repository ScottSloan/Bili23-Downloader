import sqlite3
from contextlib import contextmanager

class Database:
    def __init__(self):
        self.path = ""

    @contextmanager
    def _connection(self):
        # sqlite3 的上下文管理器只提交或回滚事务，不会关闭连接。
        conn = sqlite3.connect(self.path)
        try:
            yield conn
        finally:
            conn.close()

    def query(self, query: str, params: tuple = ()):
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        
    def execute(self, query: str, params: tuple = ()):
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    def executemany(self, query: str, params_list: list[tuple]):
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()

    def execute_script(self, script: str):
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(script)
            conn.commit()
