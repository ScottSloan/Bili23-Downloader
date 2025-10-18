import os

from utils.config import Config

from utils.common.io.file import File
from utils.common.enums import OverrideOption

class NotificationMessage:
    def __init__(self):
        self.video_title: str = ""
        self.status: int = 0
        self.video_merge_type: int = 0

class Command:
    def __init__(self):
        self.command = []
        self.rename_params = []
        self.remove_params = []

    def add(self, command: str):
        self.command.append(command)

    def add_rename(self, src: str, dst: str, cwd: str):
        self.rename_params = [src, dst, cwd]

    def add_remove(self, files: list[str], cwd: str):
        self.remove_params = [os.path.join(cwd, file) for file in files]

    def format(self):
        return " && ".join(self.command)
    
    def rename(self):
        if self.rename_params:
            dst = os.path.join(self.rename_params[2], self.rename_params[1])

            if os.path.exists(dst):
                match OverrideOption(Config.Merge.override_option):
                    case OverrideOption.Rename:
                        self.rename_params[1] = File.find_duplicate_file(dst)

                    case OverrideOption.Override:
                        File.remove_file(dst)

            File.rename_file(self.rename_params[0], self.rename_params[1], self.rename_params[2])

    def remove(self):
        if self.remove_params:
            File.remove_files(self.remove_params)

class Process:
    output: str = None
    return_code: int = None

class CommentData:
    def __init__(self):
        self.start_time: int = 0
        self.end_time: int = 0
        self.text: str = ""
        self.width: int = 0
        self.row: int = 0
