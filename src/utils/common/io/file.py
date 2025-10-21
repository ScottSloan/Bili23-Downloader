import os
import time
from typing import List

class File:
    MAX_REMOVE_ATTEMPS = 30

    @classmethod
    def remove_files(cls, file_path_list: List[str]):
        for file_path in file_path_list:
            cls.remove_file(file_path)

    @classmethod
    def remove_files_ex(cls, file_name_list: List[str], cwd: str):
        for file_name in file_name_list:
            cls.remove_file(os.path.join(cwd, file_name))

    @staticmethod
    def remove_file(file_path: str):
        for i in range(File.MAX_REMOVE_ATTEMPS):
            if not os.path.exists(file_path):
                break

            try:
                os.remove(file_path)

            except:
                time.sleep(0.1)
                continue

    @staticmethod
    def rename_file(src: str, dst: str, cwd: str):
        os.rename(os.path.join(cwd, src), os.path.join(cwd, dst))

    @staticmethod
    def find_duplicate_file(path: str):
        directory = os.path.dirname(path)
        file_name = os.path.basename(path)

        base, ext = os.path.splitext(file_name)

        index = 1

        while os.path.exists(os.path.join(directory, f"{base}_{index}{ext}")):
            index += 1

        return f"{base}_{index}{ext}"
