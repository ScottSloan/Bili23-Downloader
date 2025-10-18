import os
import json

from utils.config import Config
from utils.common.io.file import File

class LiveRoomInfo:
    def __init__(self):
        self.min_version: int = 0

        self.cover_url: str = ""

        self.room_id: int = 0

        self.up_name: str = ""
        self.title: str = ""

        self.parent_area: str = ""
        self.area: str = ""

        self.live_status: int = 0
        self.recording_status: int = 0

        self.option_setuped: bool = False

        self.base_directory: str = ""
        self.working_directory: str = ""
        self.quality: int = 0
        self.codec: int = 0

        self.total_size: int = 0

        self.file_split: int = 0
        self.split_unit: int = 100

        self.timestamp: int = 0

    def to_dict(self):
        return {
            "min_version": self.min_version,

            "cover_url": self.cover_url,

            "room_id": self.room_id,

            "up_name": self.up_name,
            "title": self.title,

            "parent_area": self.parent_area,
            "area": self.area,

            "live_status": self.live_status,
            "recording_status": self.recording_status,

            "option_setuped": self.option_setuped,

            "base_directory": self.base_directory,
            "working_directory": self.working_directory,
            "quality": self.quality,
            "codec": self.codec,

            "total_size": self.total_size,

            "file_split": self.file_split,
            "split_unit": self.split_unit,

            "timestamp": self.timestamp
        }

    def load_from_dict(self, data: dict):
        self.min_version = data.get("min_version", self.min_version)
        
        self.cover_url = data.get("cover_url", self.cover_url)

        self.room_id = data.get("room_id", self.room_id)

        self.up_name = data.get("up_name", self.up_name)
        self.title = data.get("title", self.title)

        self.parent_area = data.get("parent_area", self.parent_area)
        self.area = data.get("area", self.area)

        self.live_status = data.get("live_status", self.live_status)
        self.recording_status = data.get("recording_status", self.recording_status)

        self.option_setuped = data.get("option_setuped", self.option_setuped)

        self.base_directory = data.get("base_directory", self.base_directory)
        self.working_directory = data.get("working_directory", self.working_directory)
        self.quality = data.get("quality", self.quality)
        self.codec = data.get("codec", self.codec)

        self.total_size = data.get("total_size", self.total_size)

        self.file_split = data.get("file_split", self.file_split)
        self.split_unit = data.get("split_unit", self.split_unit)

        self.timestamp = data.get("timestamp", self.timestamp)

    def load_from_file(self, file_path: str):
        with open(file_path, "r", encoding = "utf-8") as f:
            data = json.loads(f.read())

            self.load_from_dict(data)

    def update(self):
        self.min_version = Config.APP.live_file_min_version_code

        self.write(self.to_dict())

    def remove_file(self):
        File.remove_file(self.file_path)

    def write(self, contents: dict):
        with open(self.file_path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False, indent = 4))

    def is_valid(self):
        return self.min_version >= Config.APP.live_file_min_version_code

    @property
    def file_path(self):
        return os.path.join(Config.User.live_file_directory, f"info_{self.room_id}.json")