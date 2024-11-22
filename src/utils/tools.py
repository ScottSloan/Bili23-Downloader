import re
import os
import wx
import random
import ctypes
import subprocess
from typing import List

from utils.config import Config

def get_exclimbwuzhi_header():
    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": get_login_cookies(),
        "Origin": "https://www.bilibili.com",
        "Priority": "u=1, i",
        "Referer": "https://www.bilibili.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
    }

def get_login_header():
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": get_login_cookies(),
        "Origin": "https://www.bilibili.com",
        "Priority": "u=1, i",
        "Referer": "https://www.bilibili.com/",
        "Sec-Ch-Ua": '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    }

def get_login_cookies():
    from utils.login import LoginCookies

    cookie_dict = {
        "buvid3": LoginCookies.buvid3,
        "b_lsid": LoginCookies.b_lsid,
        "b_nut": LoginCookies.b_nut,
        "_uuid": LoginCookies.uuid,
        "buvid_fp": "a22acd07567177ce6984b9e995a4a6fb",
        "enable_web_push": "DISABLE",
        "home_feed_column": "5",
        "buvid4": LoginCookies.buvid4,
    }

    return "; ".join([f"{key}={value}" for key, value in cookie_dict.items()])
    
def convert_to_bvid(aid: int):
    # 将 avid 转换为 BVid
    table = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
    map = {}

    s = [11, 10, 3, 8, 4, 6]
    xor = 177451812
    add = 8728348608

    for i in range(58):
        map[table[i]] = i

    aid = (aid ^ xor) + add
    r = list("BV1  4 1 7  ")

    for i in range(6):
        r[s[i]] = table[aid // 58 ** i % 58]

    return "".join(r)
    
def get_legal_name(name: str):
    return re.sub(r'[/\:*?"<>|]', "", name)

def remove_files(path: str, name: List):
    for i in name:
        file_path = os.path.join(path, i)
        
        if os.path.exists(file_path):
            match Config.Sys.platform:
                case "windows":
                    ctypes.windll.kernel32.SetFileAttributesW(file_path, 128)
                    ctypes.windll.kernel32.DeleteFileW(file_path)

                case "linux" | "darwin":
                    os.remove(file_path)
    
def get_new_id():
    return random.randint(1000, 9999999)

def find_str(pattern: str, string: str):
    find = re.findall(pattern, string)
    
    if find:
        return find[0]
    else:
        return None

def get_cmd_output(cmd: str):
    # 获取命令输出
    process = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, text = True)

    return process.stdout

def get_ffmpeg_path():
    if not Config.FFmpeg.path:
        # 若未指定 FFmpeg 路径，则自动检测 FFmpeg
        
        cwd_path = get_ffmpeg_cwd_path()
        env_path = get_ffmpeg_env_path()

        if cwd_path:
            # 优先使用运行目录下的 FFmpeg
            Config.FFmpeg.path = cwd_path

        if env_path and not cwd_path:
            # 使用环境变量中的 FFmpeg
            Config.FFmpeg.path = env_path

def get_ffmpeg_env_path():
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

def get_ffmpeg_cwd_path():
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
    
def check_ffmpeg_available():
    get_ffmpeg_path()

    # 获取 FFmpeg 输出信息，进而检测 FFmpeg 可用性
    cmd = f'"{Config.FFmpeg.path}" -version'

    output = get_cmd_output(cmd)

    if "ffmpeg version" in output:
        Config.FFmpeg.available = True

def get_background_color():
    if Config.Sys.dark_mode:
        return wx.Colour(30, 30, 30)
    else:
        return "white"
        
def msw_open_in_explorer(file_path):
    # 仅 Windows 平台可用
    def get_pidl(path):
        pidl = ctypes.POINTER(ITEMIDLIST)()
        shell32.SHParseDisplayName(path, None, ctypes.byref(pidl), 0, None)
        
        return pidl
    
    ole32 = ctypes.windll.ole32
    shell32 = ctypes.windll.shell32

    class ITEMIDLIST(ctypes.Structure):
        _fields_ = [("mkid", ctypes.c_byte)]

    shell32.SHParseDisplayName.argtypes = [
        ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.POINTER(ITEMIDLIST)),
        ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)
    ]

    shell32.SHParseDisplayName.restype = ctypes.HRESULT

    ole32.CoInitialize(None)
    
    try:
        folder_pidl = get_pidl(os.path.dirname(file_path))
        file_pidl = get_pidl(file_path)
        
        shell32.SHOpenFolderAndSelectItems(folder_pidl, 1, ctypes.byref(file_pidl), 0)

    finally:
        ole32.CoUninitialize()