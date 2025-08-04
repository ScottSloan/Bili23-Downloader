import os
from typing import List

class File:
    @classmethod
    def remove_files(cls, file_path_list: List[str]):
        for file_path in file_path_list:
            cls.remove_file(file_path)

    @staticmethod
    def remove_file(file_path: str):
        while os.path.exists(file_path):
            os.remove(file_path)
