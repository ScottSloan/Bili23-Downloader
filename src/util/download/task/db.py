from util.common.timestamp import get_timestamp
from util.download.task.info import TaskInfo
from util.common.config import appdata_path
from util.common.database import Database

from pathlib import Path
from typing import List
import json

class TaskDatabase(Database):
    def __init__(self):
        self.path = Path(appdata_path) / "Bili23 Downloader" / "task.db"

        self.check_and_create_table()

    def check_and_create_table(self):
        self.execute_script("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS "download_task" (
                "id"	INTEGER UNIQUE,
                "task_id"	TEXT UNIQUE,
                "cover_id"	TEXT,
                "title"	TEXT,
                "created_time"	INTEGER,
                "data"	TEXT,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
            CREATE TABLE IF NOT EXISTS "completed_task" (
                "id"	INTEGER UNIQUE,
                "task_id"	TEXT UNIQUE,
                "cover_id"	TEXT,
                "title"	TEXT,
                "completed_time"	INTEGER,
                "data"	TEXT,
                PRIMARY KEY("id" AUTOINCREMENT)
            );""")
        
    def query_tasks(self, completed: bool = False):
        if completed:
            result = self.query("""
                SELECT data FROM completed_task
            """)
        else:
            result = self.query("""
                SELECT data FROM download_task
            """)

        return result

    def add_tasks(self, task_info_list: List[TaskInfo], completed: bool = False):
        # 通过 completed 参数来区分是插入到 download_task 还是 completed_task 表
        info_list = []

        for task_info in task_info_list:
            info_list.append((
                task_info.Basic.task_id,                                    # task_id
                task_info.Basic.cover_id,                                   # cover_id
                task_info.Basic.show_title,                                 # title
                get_timestamp(),                                            # created_time or completed_time
                json.dumps(task_info.to_dict(), ensure_ascii = False)       # data
            ))

        if completed:
            self.executemany("""
                INSERT INTO completed_task (task_id, cover_id, title, completed_time, data)
                VALUES (?, ?, ?, ?, ?)
            """, info_list)
        else:
            self.executemany("""
                INSERT INTO download_task (task_id, cover_id, title, created_time, data)
                VALUES (?, ?, ?, ?, ?)
            """, info_list)
