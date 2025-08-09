import os
import time
from typing import List

class File:
    @classmethod
    def remove_files(cls, file_path_list: List[str]):
        for file_path in file_path_list:
            cls.remove_file(file_path)

    @staticmethod
    def remove_file(file_path: str):
        for i in range(30):
            if not os.path.exists(file_path):
                break

            try:
                os.remove(file_path)

            except:
                time.sleep(0.1)
                continue
