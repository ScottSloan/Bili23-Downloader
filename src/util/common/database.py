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
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

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