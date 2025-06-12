import os
import wx
import re
import json
from datetime import datetime
from typing import Optional, List

from utils.config import Config

from utils.common.data_type import DownloadTaskInfo
from utils.common.enums import ParseType
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

class FormatTool:
    @classmethod
    def format_duration(cls, episode: dict, flag: int):
        match flag:
            case ParseType.Video:
                if "arc" in episode:
                    duration = episode["arc"]["duration"]
                elif "duration" in episode:
                    duration = episode["duration"]
                else:
                    return "--:--"

            case ParseType.Bangumi:
                if "duration" in episode:
                    duration = episode["duration"] / 1000
                else:
                    return "--:--"

        return cls._format_duration(duration)
                
    def _format_duration(duration: int, show_hour: bool = False):
        hours = int(duration // 3600)
        mins = int((duration - hours * 3600) // 60)
        secs = int(duration - hours * 3600 - mins * 60)

        if show_hour or hours:
            return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2)
        else:
            return str(mins).zfill(2) + ":" + str(secs).zfill(2)
        
    def format_speed(speed: int):
        if speed > 1024 * 1024 * 1024:
            return "{:.1f} GB/s".format(speed / 1024 / 1024 / 1024)
        
        elif speed > 1024 * 1024:
            return "{:.1f} MB/s".format(speed / 1024 / 1024)
        
        elif speed > 1024:
            return "{:.1f} KB/s".format(speed / 1024)
        
        else:
            return "0 KB/s"

    def format_size(size: int):
        if not size:
            return "0 MB"
        
        elif size > 1024 * 1024 * 1024:
            return "{:.2f} GB".format(size / 1024 / 1024 / 1024)
        
        elif size > 1024 * 1024:
            return "{:.1f} MB".format(size / 1024 / 1024)
        
        else:
            return "{:.1f} KB".format(size / 1024)

    def format_bangumi_title(episode: dict, main_episode: bool = False):
        from utils.parse.bangumi import BangumiInfo

        if BangumiInfo.type_id == 2 and main_episode:
            return f"《{BangumiInfo.title}》{episode['title']}"
        
        else:
            if "share_copy" in episode:
                if Config.Misc.show_episode_full_name:
                    return episode["share_copy"]
                
                else:
                    for key in ["show_title", "long_title"]:
                        if key in episode and episode[key]:
                            return episode[key]

                    return episode["share_copy"]

            else:
                return episode["report"]["ep_title"]

    def format_data_count(data: int):
        if data >= 1e8:
            return f"{data / 1e8:.1f}亿"
        
        elif data >= 1e4:
            return f"{data / 1e4:.1f}万"
        
        else:
            return str(data)

    def format_bandwidth(bandwidth: int):
        if bandwidth > 1024 * 1024:
            return "{:.1f} mbps".format(bandwidth / 1024 / 1024)
        
        else:
            return "{:.1f} kbps".format(bandwidth / 1024)

class UniversalTool:
    # 通用工具类
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

    def get_current_time_str():
        return datetime.strftime(datetime.now(), "%Y/%m/%d %H:%M:%S")
    
    def get_time_str_from_timestamp(timestamp: int):
        return datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d %H:%M:%S")

    def get_legal_name(_name: str):
        return re.sub(r'[/\:*?"<>|]', "", _name)

    def re_find_string(_pattern: str, _string: str):
        find = re.findall(_pattern, _string)
    
        if find:
            return find[0]
        else:
            return None
    
    def aid_to_bvid(_aid: int):
        XOR_CODE = 23442827791579
        MAX_AID = 1 << 51
        ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
        ENCODE_MAP = 8, 7, 0, 5, 1, 3, 2, 4, 6

        bvid = [""] * 9
        tmp = (MAX_AID | _aid) ^ XOR_CODE

        for i in range(len(ENCODE_MAP)):
            bvid[ENCODE_MAP[i]] = ALPHABET[tmp % len(ALPHABET)]
            tmp //= len(ALPHABET)

        return "BV1" + "".join(bvid)

    def remove_files(path_list: List):
        def worker():
            for path in path_list:
                while os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        Thread(target = worker).start()

    def get_file_path(directory: str, file_name: str):
        return os.path.join(directory, file_name)
