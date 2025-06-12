import os
import wx
import re
import json
from datetime import datetime
from typing import Optional, List

from utils.config import Config

from utils.common.data_type import DownloadTaskInfo
from utils.common.thread import Thread
from utils.common.request import RequestUtils

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
    def get_user_face():
        if not os.path.exists(Config.User.face_path):
            # 若未缓存头像，则下载头像到本地
            content = RequestUtils.request_get(Config.User.face_url).content

            with open(Config.User.face_path, "wb") as f:
                f.write(content)

        return Config.User.face_path

    def get_user_round_face(image):
        width, height = image.GetSize()
        diameter = min(width, height)
        
        image = image.Scale(diameter, diameter, wx.IMAGE_QUALITY_HIGH)
        
        circle_image = wx.Image(diameter, diameter)
        circle_image.InitAlpha()
        
        for x in range(diameter):
            for y in range(diameter):
                dist = ((x - diameter / 2) ** 2 + (y - diameter / 2) ** 2) ** 0.5
                if dist <= diameter / 2:
                    circle_image.SetRGB(x, y, image.GetRed(x, y), image.GetGreen(x, y), image.GetBlue(x, y))
                    circle_image.SetAlpha(x, y, 255)
                else:
                    circle_image.SetAlpha(x, y, 0)
        
        return circle_image

    def get_time_str_from_timestamp(timestamp: int):
        return datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d %H:%M:%S")

    def re_find_string(_pattern: str, _string: str):
        find = re.findall(_pattern, _string)
    
        if find:
            return find[0]
        else:
            return None
    
    def remove_files(path_list: List):
        def worker():
            for path in path_list:
                while os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        Thread(target = worker).start()
