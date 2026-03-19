from pathlib import Path
from typing import Callable

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
    
    def execute(self):
        for file_name in self.files_to_remove:
            try:
                path = Path(self.cwd, file_name)

                if path.exists():
                    Path(self.cwd, file_name).unlink()
                
            except Exception as e:
                if self.on_error:
                    self.on_error(e, file_name)

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
            target_path = Path(self.cwd, new_file_name)

            try:
                original_path.rename(target_path)

            except Exception as e:
                if self.on_error:
                    self.on_error(str(e), original_file_name, new_file_name)

                raise e

class File:
    @staticmethod
    def preallocate_file(path: str, size: int):
        """
        预分配文件空间
        """
        with open(path, "wb") as f:
            f.seek(size - 1)
            f.write(b"\0")

    