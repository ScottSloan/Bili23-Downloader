import os
import wx
import json
import time
from datetime import datetime
from typing import Optional, List

from utils.config import Config

from utils.common.data_type import DownloadTaskInfo
from utils.common.thread import Thread

class DownloadFileTool:
    # 断点续传信息工具类
    def __init__(self, _id: Optional[int] = None, file_name: Optional[str] = None):
        if file_name:
            _file = file_name
        else:
            _file = f"info_{_id}.json"

        self.file_path = os.path.join(Config.User.download_file_directory, _file)

        if not self.file_existence:
            self._write_download_file({})

    def write_file(self, info: DownloadTaskInfo):
        def _header():
            return {
                "min_version": Config.APP.task_file_min_version_code
            }

        # 保存断点续传信息，适用于初次添加下载任务
        contents = self._read_download_file_json()

        contents["header"] = _header()
        contents["task_info"] = info.to_dict()

        if not contents:
            contents["thread_info"] = {}

        self._write_download_file(contents)

    def delete_file(self):
        # 清除断点续传信息
        if self.file_existence:
            os.remove(self.file_path)

    def update_task_info_kwargs(self, **kwargs):
        contents = self._read_download_file_json()

        if contents is not None:
            for key, value in kwargs.items():
                if "task_info" in contents:
                    contents["task_info"][key] = value

            self._write_download_file(contents)

    def update_info(self, category: str, info: dict):
        contents = self._read_download_file_json()

        if contents is not None:
            contents[category] = info

            self._write_download_file(contents)

    def get_info(self, category: str):
        contents = self._read_download_file_json()

        return contents.get(category, {})

    def _read_download_file_json(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding = "utf-8") as f:
                try:
                    return json.loads(f.read())
                
                except Exception:
                    return {}

    def _write_download_file(self, contents: dict):
        with open(self.file_path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False, indent = 4))

    def _check_compatibility(self):
        try:
            if self._read_download_file_json()["header"]["min_version"] < Config.APP.task_file_min_version_code:
                return False

        except Exception:
            return False

        return True
    
    @staticmethod
    def _clear_all_files():
        for file in os.listdir(Config.User.download_file_directory):
            file_path = os.path.join(Config.User.download_file_directory, file)

            if os.path.isfile(file_path):
                if file.startswith("info_") and file.endswith(".json"):
                    os.remove(file_path)
    
    @staticmethod
    def delete_file_by_id(id: int):
        file_path = os.path.join(Config.User.download_file_directory, f"info_{id}.json")

        if os.path.exists(file_path):
            os.remove(file_path)

    @property
    def file_existence(self):
        return os.path.exists(self.file_path)

class UniversalTool:
    def get_time_str_from_timestamp(timestamp: int):
        return datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d %H:%M:%S")

    def remove_files(path_list: List):
        def worker():
            for path in path_list:
                attempts = 0
                while os.path.exists(path) and attempts < 10:
                    try:
                        os.remove(path)
                        break
                    except Exception:
                        attempts += 1
                        time.sleep(0.1)

        Thread(target = worker, daemon = True).start()
