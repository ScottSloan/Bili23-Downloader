import os
import re
import json
import ctypes
import random
import requests
import subprocess
import requests.auth
from datetime import datetime
from typing import Optional, Callable, List, Dict

from utils.config import Config
from utils.data_type import DownloadTaskInfo

class RequestTool:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"

    @staticmethod
    def request(url: str, error_callback: Optional[Callable] = None):
        try:
            req = requests.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

            return req.content

        except Exception:
            if error_callback is not None:
                error_callback()

    @staticmethod
    def get_real_url(url: str):
        req = requests.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
    
        return req.url

    @staticmethod
    def get_headers(referer_url: Optional[str] = None, sessdata: Optional[str] = None, range: Optional[List[int]] = None):
        headers = {
            "User-Agent": RequestTool.USER_AGENT,
            "Cookie": "CURRENT_FNVAL=4048;"
        }

        if referer_url:
            headers["Referer"] = referer_url

        if sessdata:
            headers["Cookie"] += f"SESSDATA={sessdata}"

        if range:
            headers["Range"] = f"bytes={range[0]}-{range[1]}"

        return headers

    @staticmethod
    def get_proxies():
        match Config.Proxy.proxy_mode:
            case Config.Type.PROXY_DISABLE:
                return {}
            
            case Config.Type.PROXY_FOLLOW:
                return None
            
            case Config.Type.PROXY_MANUAL:
                return {
                    "http": f"{Config.Proxy.proxy_ip_addr}:{Config.Proxy.proxy_port}",
                    "https": f"{Config.Proxy.proxy_ip_addr}:{Config.Proxy.proxy_port}"
                }
    
    @staticmethod
    def get_auth():
        if Config.Proxy.auth_enable:
            return requests.auth.HTTPProxyAuth(Config.Proxy.auth_uname, Config.Proxy.auth_passwd)
        else:
            return None
    
class DirectoryTool:
    @staticmethod
    def open_directory(directory: str):
        match Config.Sys.platform:
            case "windows":
                os.startfile(directory)

            case "linux":
                subprocess.Popen(f'xdg-open "{directory}"', shell = True)

            case "darwin":
                subprocess.Popen(f'open "{directory}"', shell = True)

    @staticmethod
    def open_file_location(path: str):
        match Config.Sys.platform:
            case "windows":
                DirectoryTool._msw_SHOpenFolderAndSelectItems(path)

            case "linux":
                subprocess.Popen(f'xdg-open "{Config.Download.path}"', shell = True)

            case "darwin":
                subprocess.Popen(f'open -R "{path}"', shell = True)
    
    @staticmethod
    def _msw_SHOpenFolderAndSelectItems(path: str):
        def get_pidl(path):
            pidl = ctypes.POINTER(ITEMIDLIST)()
            shell32.SHParseDisplayName(path, None, ctypes.byref(pidl), 0, None)
            
            return pidl
    
        class ITEMIDLIST(ctypes.Structure):
            _fields_ = [("mkid", ctypes.c_byte)]

        ole32 = ctypes.windll.ole32
        shell32 = ctypes.windll.shell32

        shell32.SHParseDisplayName.argtypes = [
            ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.POINTER(ITEMIDLIST)),
            ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)
        ]

        shell32.SHParseDisplayName.restype = ctypes.HRESULT

        ole32.CoInitialize(None)

        try:
            folder_pidl = get_pidl(os.path.dirname(path))
            file_pidl = get_pidl(path)
            
            shell32.SHOpenFolderAndSelectItems(folder_pidl, 1, ctypes.byref(file_pidl), 0)

        finally:
            ole32.CoUninitialize()

class DownloadFileTool:
    # 记录断点续传信息工具类
    def __init__(self, id: Optional[int] = None, file_name: Optional[str] = None):
        def check():
            if not os.path.exists(self.file_path):
                self._write_download_file({})

        if file_name:
            _file = file_name
        else:
            _file = f"info_{id}.json"

        self.file_path = os.path.join(Config.User.download_file_directory, _file)

        # 检查本地文件是否存在
        check()

    def save_download_info(self, info: DownloadTaskInfo):
        # 保存断点续传信息，适用于初次添加下载任务
        contents = self._read_download_file_json()

        contents["task_info"] = info.to_dict()

        # 检查是否已断点续传信息
        if not contents:
            contents["thread_info"] = {}

        self._write_download_file(contents)

    def clear_download_info(self):
        # 清除断点续传信息
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    def update_task_info_kwargs(self, **kwargs):
        contents = self._read_download_file_json()

        if contents is not None:
            for key, value in kwargs.items():
                contents["task_info"][key] = value

            self._write_download_file(contents)

    def update_thread_info(self, thread_info: Dict):
        contents = self._read_download_file_json()

        if contents is not None:
            contents["thread_info"] = thread_info

            self._write_download_file(contents)

    def get_thread_info(self):
        contents = self._read_download_file_json()

        return contents["thread_info"]
    
    def _read_download_file_json(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding = "utf-8") as f:
                try:
                    return json.loads(f.read())
                
                except Exception:
                    return {}

    def _write_download_file(self, contents: Dict):
        with open(self.file_path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False, indent = 4))

class FormatTool:
    # 格式化数据类
    @staticmethod
    def format_duration(episode: Dict, flag: int):
        match flag:
            case Config.Type.DURATION_VIDEO_SECTIONS:
                # 合集视频
                duration = episode["arc"]["duration"]

            case Config.Type.DURATION_VIDEO_OTHERS:
                # 非合集视频
                duration = episode["duration"]

            case Config.Type.DURATION_BANGUMI:
                # 番组
                if "duration" in episode:
                    duration = episode["duration"] / 1000
                else:
                    return "--:--"

        hours = int(duration // 3600)
        mins = int((duration - hours * 3600) // 60)
        secs = int(duration - hours * 3600 - mins * 60)
        
        return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2) if hours != 0 else str(mins).zfill(2) + ":" + str(secs).zfill(2)

    @staticmethod
    def format_speed(speed: int):
        if speed > 1024 * 1024 * 1024:
            return "{:.1f} GB/s".format(speed / 1024 / 1024 / 1024)
        
        elif speed > 1024 * 1024:
            return "{:.1f} MB/s".format(speed / 1024 / 1024)
        
        elif speed > 1024:
            return "{:.1f} KB/s".format(speed / 1024)
        
        else:
            return "0 KB/s"

    @staticmethod
    def format_size(size: int):
        if not size:
            return "0 MB"
        
        elif size > 1024 * 1024 * 1024:
            return "{:.1f} GB".format(size / 1024 / 1024 / 1024)
        
        elif size > 1024 * 1024:
            return "{:.1f} MB".format(size / 1024 / 1024)
        
        else:
            return "{:.1f} KB".format(size / 1024)

    @staticmethod
    def format_bangumi_title(episode: Dict):
        from utils.parse.bangumi import BangumiInfo

        if BangumiInfo.type_id == 2:
            return "{} - {}".format(BangumiInfo.title, episode["title"])
        
        else:
            if "share_copy" in episode:
                if Config.Misc.show_episode_full_name:
                    return episode["share_copy"]
                
                else:
                    if "long_title" in episode:
                        if episode["long_title"]:
                            return episode["long_title"]
                    
                    return episode["share_copy"]

            else:
                return episode["report"]["ep_title"]

class UniversalTool:
    @staticmethod
    def get_update_json():
        url = "https://api.scott-sloan.cn/Bili23-Downloader/getLatestVersion"

        req = requests.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        req.encoding = "utf-8"

        update_json = json.loads(req.text)

        Config.Temp.update_json = update_json

    @staticmethod
    def get_user_face():
        if not os.path.exists(Config.User.face_path):
            # 若未缓存头像，则下载头像到本地
            content = RequestTool.request(Config.User.face)

            with open(Config.User.face_path, "wb") as f:
                f.write(content)

        return Config.User.face_path

    @staticmethod
    def get_system_encoding():
        match Config.Sys.platform:
            case "windows":
                return "cp936"
            
            case "linux" | "darwin":
                return "utf-8"

    @staticmethod
    def get_current_time():
        return datetime.strftime(datetime.now(), "%Y/%m/%d %H:%M:%S")

    @staticmethod
    def get_legal_name(_name: str):
        return re.sub(r'[/\:*?"<>|]', "", _name)

    @staticmethod
    def get_random_id():
        return random.randint(10000000, 99999999)
    
    @staticmethod
    def re_find_string(_pattern: str, _string: str):
        find = re.findall(_pattern, _string)
    
        if find:
            return find[0]
        else:
            return None
    
    @staticmethod
    def aid_to_bvid(_aid: int):
        table = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
        map = {}

        s = [11, 10, 3, 8, 4, 6]
        xor = 177451812
        add = 8728348608

        for i in range(58):
            map[table[i]] = i

        _aid = (_aid ^ xor) + add
        r = list("BV1  4 1 7  ")

        for i in range(6):
            r[s[i]] = table[_aid // 58 ** i % 58]

        return "".join(r)

    @staticmethod
    def remove_files(directory: str, file_name_list: List[str]):
        for i in file_name_list:
            _path = os.path.join(directory, i)
            
            if os.path.exists(_path):
                try:
                    os.remove(_path)
                except Exception:
                    pass

class FFmpegCheckTool:
    @staticmethod
    def get_path():
        if not Config.FFmpeg.path:
            # 若未指定 FFmpeg 路径，则自动检测 FFmpeg
            
            cwd_path = FFmpegCheckTool._get_ffmpeg_cwd_path()
            env_path = FFmpegCheckTool._get_ffmpeg_env_path()

            if cwd_path:
                # 优先使用运行目录下的 FFmpeg
                Config.FFmpeg.path = cwd_path

            if env_path and not cwd_path:
                # 使用环境变量中的 FFmpeg
                Config.FFmpeg.path = env_path
    
    @staticmethod
    def check_available():
        FFmpegCheckTool.get_path()

        cmd = f'"{Config.FFmpeg.path}" -version'

        _process = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, text = True)

        if "ffmpeg version" in _process.stdout:
            Config.FFmpeg.available = True

    @staticmethod
    def _get_ffmpeg_env_path():
        # 从 PATH 环境变量中获取 ffmpeg 的路径
        ffmpeg_path = None
        path_env = os.environ.get("PATH", "")
        
        match Config.Sys.platform:
            case "windows":
                file_name = "ffmpeg.exe"

            case "linux" | "darwin":
                file_name = "ffmpeg"

        # 将 PATH 环境变量中的路径分割成各个目录
        for directory in path_env.split(os.pathsep):
            possible_path = os.path.join(directory, file_name)

            if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
                ffmpeg_path = possible_path
                break

        return ffmpeg_path
    
    @staticmethod
    def _get_ffmpeg_cwd_path():
        # 从运行目录中获取 ffmpeg 路径
        ffmpeg_path = None

        match Config.Sys.platform:
            case "windows":
                file_name = "ffmpeg.exe"
            case "linux" | "darwin":
                file_name = "ffmpeg"
        
        possible_path = os.path.join(os.getcwd(), file_name)
        
        if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
            ffmpeg_path = possible_path

        return ffmpeg_path
    