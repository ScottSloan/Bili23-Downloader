from ...common.config import appdata_path, config
from ...common.timestamp import get_timestamp
from ...common.database import Database
from ...parse.episode.tree import Attribute

from .info import TaskInfo

from pathlib import Path
from typing import List
import hashlib
import orjson

class TaskDatabase(Database):
    def __init__(self):
        self.path = Path(appdata_path) / "Bili23 Downloader" / "task.db"

        self.check_and_create_table()

        self._check_should_upgrade()

    def _check_should_upgrade(self):
        if config.should_upgrade_config:
            self._upgrade()

            config.should_upgrade_config = False

    def check_and_create_table(self):
        self.execute_script("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS "download_task" (
                "id"	INTEGER UNIQUE,
                "task_id"	TEXT UNIQUE,
                "hash_id"   TEXT,
                "cover_id"	TEXT,
                "title"	TEXT,
                "created_time"	INTEGER,
                "data"	TEXT,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
            CREATE TABLE IF NOT EXISTS "completed_task" (
                "id"	INTEGER UNIQUE,
                "task_id"	TEXT UNIQUE,
                "hash_id"   TEXT,
                "cover_id"	TEXT,
                "title"	TEXT,
                "completed_time"	INTEGER,
                "data"	TEXT,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
            CREATE INDEX IF NOT EXISTS "idx_download_task_hash_id" ON "download_task" ("hash_id");
            CREATE INDEX IF NOT EXISTS "idx_completed_task_hash_id" ON "completed_task" ("hash_id");
            """)
        
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
            timestamp = task_info.Basic.completed_time if completed else task_info.Basic.created_time

            if not timestamp:
                timestamp = get_timestamp()

            info_list.append((
                task_info.Basic.task_id,                                    # task_id
                self._calc_hash_id(task_info),                              # hash_id
                task_info.Basic.cover_id,                                   # cover_id
                task_info.Basic.show_title,                                 # title
                timestamp,                                                  # created_time or completed_time
                orjson.dumps(task_info.to_dict()).decode("utf-8")           # data
            ))

        if completed:
            self.executemany("""
                INSERT INTO completed_task (task_id, hash_id, cover_id, title, completed_time, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, info_list)
        else:
            self.executemany("""
                INSERT INTO download_task (task_id, hash_id, cover_id, title, created_time, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, info_list)

    def update_task(self, task_info: TaskInfo):
        self.execute("""
            UPDATE download_task SET data = ? WHERE task_id = ?
        """, (orjson.dumps(task_info.to_dict()).decode("utf-8"), task_info.Basic.task_id))

    def delete_task(self, task_id: str, completed: bool = False):
        if completed:
            self.execute("""
                DELETE FROM completed_task WHERE task_id = ?
            """, (task_id,))
        else:
            self.execute("""
                DELETE FROM download_task WHERE task_id = ?
            """, (task_id,))

    def check_duplicate(self, hash_id: str):
        completed_result = self.query("""
            SELECT title FROM completed_task WHERE hash_id = ?
        """, (hash_id,))
    
        download_result = self.query("""
            SELECT title FROM download_task WHERE hash_id = ?
        """, (hash_id,))

        return len(completed_result) > 0 or len(download_result) > 0

    def _upgrade(self):
        def _to_task_list(result):
            _task_info_list = []

            for entry in result:
                task_info = TaskInfo()
                task_info.from_dict(orjson.loads(entry[0]))

                _task_info_list.append(task_info)

            return _task_info_list

        # 执行数据库升级逻辑

        # 取出原有数据
        download_tasks = self.query_tasks(completed = False)
        completed_tasks = self.query_tasks(completed = True)

        # 删除原有表
        self.execute_script("""
            DROP TABLE IF EXISTS download_task;
            DROP TABLE IF EXISTS completed_task;
        """)

        # 重新创建表
        self.check_and_create_table()

        self.add_tasks(_to_task_list(download_tasks), completed = False)
        self.add_tasks(_to_task_list(completed_tasks), completed = True)

    def _calc_hash_id(self, task_info: TaskInfo):
        # 根据 task_info 计算 hash_id
        attr = task_info.Episode.attribute

        if attr & Attribute.VIDEO_BIT:
            # 投稿视频
            metadata = {
                "bvid": task_info.Episode.bvid,
                "cid": task_info.Episode.cid,
                "aid": task_info.Episode.aid
            }

        elif attr & Attribute.BANGUMI_BIT:
            # 剧集类
            metadata = {
                "bvid": task_info.Episode.bvid,
                "cid": task_info.Episode.cid,
                "aid": task_info.Episode.aid,
                "ep_id": task_info.Episode.ep_id
            }

        elif attr & Attribute.CHEESE_BIT:
            # 课程类
            metadata = {
                "aid": task_info.Episode.aid,
                "cid": task_info.Episode.cid,
                "ep_id": task_info.Episode.ep_id
            }

        elif attr & Attribute.AUDIO_BIT:
            # 音乐类
            metadata = {
                "sid": task_info.Episode.sid
            }

        return hashlib.md5(orjson.dumps(metadata)).hexdigest()
