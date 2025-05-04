import os
import wx
import re
import json
import ctypes
import requests
import subprocess
import requests.auth
from datetime import datetime
from typing import Optional, List

from .config import Config
from .common.data_type import DownloadTaskInfo
from .common.enums import ParseType, ProxyMode, Platform
from .common.thread import Thread

class RequestTool:
    # 请求工具类
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"

    @staticmethod
    def request_get(url: str, headers = None, proxies = None, auth = None, stream = False):
        if not headers:
            headers = RequestTool.get_headers()

        if not proxies:
            proxies = RequestTool.get_proxies()

        if not auth:
            auth = RequestTool.get_auth()

        return requests.get(RequestTool.replace_protocol(url), headers = headers, proxies = proxies, auth = auth, stream = stream)

    @staticmethod
    def request_post(url: str, headers = None, params = None, json = None):
        if not headers:
            headers = RequestTool.get_headers()
        
        return requests.post(RequestTool.replace_protocol(url), headers = headers, params = params, json = json, proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

    @staticmethod
    def request_head(url: str, headers = None):
        if not headers:
            headers = RequestTool.get_headers()
        
        return requests.head(RequestTool.replace_protocol(url), headers = headers, proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

    @staticmethod
    def get_headers(referer_url: Optional[str] = None, sessdata: Optional[str] = None, range: Optional[List[int]] = None):
        def cookie():
            if Config.Auth.buvid3:
                _cookie["buvid3"] = Config.Auth.buvid3
                _cookie["b_nut"] = Config.Auth.b_nut
            
            if Config.Auth.bili_ticket:
                _cookie["bili_ticket"] = Config.Auth.bili_ticket

            if Config.Auth.buvid4:
                _cookie["buvid4"] = Config.Auth.buvid4

        headers = {
            "User-Agent": RequestTool.USER_AGENT,
        }

        _cookie = {
            "CURRENT_FNVAL": "4048",
            "b_lsid": Config.Auth.b_lsid,
            "_uuid": Config.Auth.uuid,
            "buvid_fp": Config.Auth.buvid_fp
        }

        if referer_url:
            headers["Referer"] = referer_url

        if sessdata:
            _cookie["SESSDATA"] = Config.User.SESSDATA
            _cookie["DedeUserID"] = Config.User.DedeUserID
            _cookie["DedeUserID__ckMd5"] = Config.User.DedeUserID__ckMd5
            _cookie["bili_jct"] = Config.User.bili_jct

        if range:
            headers["Range"] = f"bytes={range[0]}-{range[1]}"

        cookie()

        headers["Cookie"] = ";".join([f"{key}={value}" for key, value in _cookie.items()])

        return headers

    @staticmethod
    def get_proxies():
        match ProxyMode(Config.Proxy.proxy_mode):
            case ProxyMode.Disable:
                return {}
            
            case ProxyMode.Follow:
                return None
            
            case ProxyMode.Custom:
                return {
                    "http": f"{Config.Proxy.proxy_ip}:{Config.Proxy.proxy_port}",
                    "https": f"{Config.Proxy.proxy_ip}:{Config.Proxy.proxy_port}"
                }

    @staticmethod
    def get_auth():
        if Config.Proxy.enable_auth:
            return requests.auth.HTTPProxyAuth(Config.Proxy.auth_username, Config.Proxy.auth_password)
        else:
            return None

    @staticmethod
    def replace_protocol(url: str):
        if not Config.Advanced.always_use_https_protocol:
            return url.replace("https://", "http://")
        
        return url

class FileDirectoryTool:
    # 文件目录工具类
    @staticmethod
    def open_directory(directory: str):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                os.startfile(directory)

            case Platform.Linux:
                subprocess.Popen(f'xdg-open "{directory}"', shell = True)

            case Platform.macOS:
                subprocess.Popen(f'open "{directory}"', shell = True)

    @staticmethod
    def open_file_location(path: str):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                FileDirectoryTool._msw_SHOpenFolderAndSelectItems(path)

            case Platform.Linux:
                subprocess.Popen(f'xdg-open "{Config.Download.path}"', shell = True)

            case Platform.macOS:
                subprocess.Popen(f'open -R "{path}"', shell = True)

    @staticmethod
    def get_file_ext_associated_app(file_ext: str):
        def _linux():
            _desktop = subprocess.Popen("xdg-mime query default video/mp4", stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True, text = True)

            _desktop_path = os.path.join("/usr/share/applications", _desktop.stdout.read().replace("\n", ""))

            _exec = subprocess.Popen(f"grep '^Exec=' {_desktop_path} | head -n 1 | cut -d'=' -f2", stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True, text = True)

            return _exec.stdout.read().replace("\n", "")

        match Platform(Config.Sys.platform):
            case Platform.Windows:
                result, buffer = FileDirectoryTool._msw_AssocQueryStringW(file_ext)

                if result == 0:
                    return (True, str(buffer.value))
                else:
                    return (False, "")

            case Platform.Linux:
                return (True, _linux())

            case Platform.macOS:
                # macOS 不支持获取默认程序
                return (False, "")

    @staticmethod
    def _msw_SHOpenFolderAndSelectItems(path: str):
        def get_pidl(path):
            pidl = ctypes.POINTER(ITEMIDLIST)()
            ctypes.windll.shell32.SHParseDisplayName(path, None, ctypes.byref(pidl), 0, None)
            
            return pidl
        
        class ITEMIDLIST(ctypes.Structure):
            _fields_ = [("mkid", ctypes.c_byte)]

        ctypes.windll.ole32.CoInitialize(None)

        try:
            folder_pidl = get_pidl(os.path.dirname(path))
            file_pidl = get_pidl(path)
            
            ctypes.windll.shell32.SHOpenFolderAndSelectItems(folder_pidl, 1, ctypes.byref(file_pidl), 0)

        finally:
            ctypes.windll.ole32.CoUninitialize()

    @staticmethod
    def _msw_AssocQueryStringW(file_ext: str):
        from ctypes import wintypes

        buffer = ctypes.create_unicode_buffer(512)
        pcchOut = wintypes.DWORD(512)
        
        result = ctypes.windll.shlwapi.AssocQueryStringW(0x00000000, 1, file_ext, None, buffer, ctypes.byref(pcchOut))

        return (result, buffer)

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
    # 格式化数据类
    def format_duration(episode: dict, flag: int):
        match flag:
            case ParseType.Video:
                if "arc" in episode:
                    duration = episode["arc"]["duration"]
                else:
                    duration = episode["duration"]

            case ParseType.Bangumi:
                if "duration" in episode:
                    duration = episode["duration"] / 1000
                else:
                    return "--:--"

        hours = int(duration // 3600)
        mins = int((duration - hours * 3600) // 60)
        secs = int(duration - hours * 3600 - mins * 60)
        
        return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2) if hours != 0 else str(mins).zfill(2) + ":" + str(secs).zfill(2)

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
    @staticmethod
    def get_user_face():
        if not os.path.exists(Config.User.face_path):
            # 若未缓存头像，则下载头像到本地
            content = RequestTool.request_get(Config.User.face_url).content

            with open(Config.User.face_path, "wb") as f:
                f.write(content)

        return Config.User.face_path

    @staticmethod
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

    @staticmethod
    def get_current_time_str():
        return datetime.strftime(datetime.now(), "%Y/%m/%d %H:%M:%S")

    @staticmethod
    def get_time_str_from_timestamp(timestamp: int):
        return datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d %H:%M:%S")

    @staticmethod
    def get_legal_name(_name: str):
        return re.sub(r'[/\:*?"<>|]', "", _name)

    @staticmethod
    def re_find_string(_pattern: str, _string: str):
        find = re.findall(_pattern, _string)
    
        if find:
            return find[0]
        else:
            return None

    @staticmethod
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

    @staticmethod
    def remove_files(path_list: List):
        def worker():
            for path in path_list:
                while os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        Thread(target = worker).start()

    @staticmethod
    def get_file_path(directory: str, file_name: str):
        return os.path.join(directory, file_name)

    @staticmethod
    def msw_set_dpi_awareness():
        if Config.Sys.platform == Platform.Windows.value:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)

    @staticmethod
    def msw_set_utf8_encode():
        if Config.Sys.platform == Platform.Windows.value:
            subprocess.run("chcp 65001", stdout = subprocess.PIPE, shell = True)
