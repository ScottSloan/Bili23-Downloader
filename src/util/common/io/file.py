from pathlib import Path
from typing import Callable

from util.common.enum import FileConflictResolution
from util.common import config

from threading import Lock
import logging

logger = logging.getLogger(__name__)

# 线程锁，确保同一时间只有一个线程在执行文件操作，避免因多线程同时执行文件操作而导致的竞态条件和数据不一致问题
rename_lock = Lock()

class Remover:
    def __init__(self):
        self.cwd = None
        self.on_error = None
        self.files_to_remove = []

    def set_cwd(self, cwd: Path):
        self.cwd = cwd

        return self

    def set_on_error(self, callback: Callable[[Exception, str], None]):
        self.on_error = callback

        return self

    def add_file(self, file_name: str):
        self.files_to_remove.append(file_name)

        return self
    
    def add_files(self, file_names: list):
        self.files_to_remove.extend(file_names)

        return self
    
    def execute(self):
        for file_name in self.files_to_remove:
            try:
                path = Path(self.cwd, file_name)

                if path.exists():
                    Path(self.cwd, file_name).unlink()
                
            except Exception as e:
                if self.on_error:
                    self.on_error(e, file_name)

                logger.exception("删除文件失败: %s", path)

                raise e

class Renamer:
    def __init__(self):
        self.cwd = None
        self.on_error = None
        self.files_to_rename = []

    def set_cwd(self, cwd: Path):
        self.cwd = cwd

        return self
    
    def set_on_error(self, callback: Callable[[Exception, str, str], None]):
        self.on_error = callback

        return self

    def add_file(self, original_file_name: str, new_file_name: str):
        self.files_to_rename.append((original_file_name, new_file_name))

        return self
    
    def execute(self):
        for original_file_name, new_file_name in self.files_to_rename:
            original_path = Path(self.cwd, original_file_name)
            new_path = Path(self.cwd, new_file_name)

            try:
                with rename_lock:
                    # 重命名之前，检查目标文件是否已存在，避免因目标文件已存在而导致重命名失败
                    new_path = self.__pre_check(original_path, new_path)

                    original_path.rename(new_path)

            except Exception as e:
                if self.on_error:
                    self.on_error(str(e), original_file_name, new_file_name)

                logger.exception("重命名文件失败: %s -> %s", original_path, new_path)

                raise e
            
            finally:
                return new_path 
            
    def __pre_check(self, original_path: Path, new_path: Path):
        if not new_path.exists():
            return new_path
        
        if not original_path.exists():
            raise FileNotFoundError(f"源文件不存在: {original_path}")
        
        match config.get(config.file_conflict_resolution):
            case FileConflictResolution.OVERWRITE:
                # 覆盖文件，直接删除目标文件即可

                with rename_lock:
                    new_path.unlink()

                return new_path

            case FileConflictResolution.AUTO_RENAME:
                # 自动重命名，在文件名后添加 "(n)"，直到找到一个不存在的文件名
                suffix = new_path.suffix
                name_without_suffix = new_path.stem

                n = 1

                while True:
                    new_name = f"{name_without_suffix} ({n}){suffix}"
                    new_target_path = new_path.with_name(new_name)

                    if not new_target_path.exists():
                        return new_target_path
                    
                    n += 1
                
class File:
    @staticmethod
    def preallocate_file(path: str, size: int):
        """
        预分配文件空间
        """
        with open(path, "wb") as f:
            f.seek(size - 1)
            f.write(b"\0")

    