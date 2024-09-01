import re
import os
import json
import random
import ctypes
import requests
import subprocess
from datetime import datetime
from requests.auth import HTTPProxyAuth

from utils.config import Config

resolution_map = {"超高清 8K": 127, "杜比视界": 126, "真彩 HDR": 125, "超清 4K": 120, "高清 1080P60": 116, "高清 1080P+": 112, "智能修复": 100, "高清 1080P": 80, "高清 720P": 64, "清晰 480P": 32, "流畅 360P": 16}
sound_quality_map = {"Hi-Res 无损": 30251, "杜比全景声": 30250, "192K": 30280, "132K": 30232, "64K": 30216}
sound_quality_map_set = {"Hi-Res 无损 / 杜比全景声": 30250, "192K": 30280, "132K": 30232, "64K": 30216}
codec_id_map = {"AVC": 7, "HEVC": 12, "AV1": 13}
target_format_map = {"AVI": "avi", "MKV": "mkv", "FLV": "flv", "MOV": "mov", "WMV": "wmv"}
target_codec_map = {"AVC/H.264": 1, "HEVC/H.265": 2, "AV1": 3}
gpu_map = {"NVIDIA": 1, "AMD": 2, "Intel": 3}

def process_shorklink(url):
    req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
    
    return req.url

def get_header(referer_url = None, cookie = None, chunk_list = None, download = False) -> dict:
    header = {
        "Cookie": "CURRENT_FNVAL=4048;",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    }
    
    if referer_url:
        header["Referer"] = referer_url

    if chunk_list:
        header["Range"] = "bytes={}-{}".format(chunk_list[0], chunk_list[1])

    if cookie:
        header["Cookie"] += "SESSDATA=" + cookie

    if download:
        header["Accept"] = "*/*"
        header["Accept-Encoding"] = "identity"
        header["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        header["Origin"] = "https://www.bilibili.com"
        header["Priority"] = "u=1, i"
    
    return header

def get_proxy():
    if Config.Proxy.proxy:
        return {
            "http": f"{Config.Proxy.ip}:{Config.Proxy.port}",
            "https": f"{Config.Proxy.ip}:{Config.Proxy.port}"
        }
    else:
        return {}

def get_auth():
    if Config.Proxy.auth:
        return HTTPProxyAuth(Config.Proxy.uname, Config.Proxy.passwd)
    else:
        return HTTPProxyAuth(None, None)
    
def convert_to_bvid(aid):
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

def format_duration(episode, flag):
    match flag:
        case 0:
            duration = episode["arc"]["duration"]
        case 1:
            duration = episode["duration"]
        case 2:
            if "duration" in episode:
                duration = episode["duration"] / 1000
            else:
                return "--:--"

    hours = int(duration // 3600)
    mins = int((duration - hours * 3600) // 60)
    secs = int(duration - hours * 3600 - mins * 60)
    
    return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2) if hours != 0 else str(mins).zfill(2) + ":" + str(secs).zfill(2)

def format_size(size):
    if size > 1048576:
        return "{:.1f} GB".format(size / 1024 / 1024)
    elif size > 1024:
        return "{:.1f} MB".format(size / 1024)
    else:
        return "{:.1f} KB".format(size)

def format_bangumi_title(episode):
    from .bangumi import BangumiInfo

    if BangumiInfo.type == "电影":
        return "{} - {}".format(BangumiInfo.title, episode["title"])
    else:
        if "share_copy" in episode:
            return episode["share_copy"]
        else:
            return episode["report"]["ep_title"]
    
def get_legal_name(name):
    return re.sub('[/\:*?"<>|]', "", name)

def get_user_face():
    if not os.path.exists(Config.User.face_path):
        # 若未缓存头像，则下载头像到本地
        req = requests.get(Config.User.face, proxies = get_proxy(), auth = get_auth())

        with open(Config.User.face_path, "wb") as f:
            f.write(req.content)

    return os.path.join(os.getenv("LOCALAPPDATA"), "Bili23 Downloader", "face.jpg")

def remove_files(path, name):
    for i in name:
        file_path = os.path.join(path, i)
        
        if os.path.exists(file_path):
            ctypes.windll.kernel32.SetFileAttributesW(file_path, 128)
            ctypes.windll.kernel32.DeleteFileW(file_path)

def check_update():
    url = "https://api.scott-sloan.cn/Bili23-Downloader/getLatestVersion"

    req = requests.get(url, headers = get_header(), timeout = 5)
    req.encoding = "utf-8"

    update_json = json.loads(req.text)
    Config.Temp.update_json = update_json
    
def get_new_id():
    return random.randint(1000, 9999)

def find_str(pattern, string):
    find = re.findall(pattern, string)
    
    if find:
        return find[0]
    else:
        return None

def get_cmd_output(cmd):
    process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    process.wait()

    return process.stdout.read().decode("utf-8")

def get_all_ffmpeg_path():
    # 定位环境变量和运行目录中的 FFmpeg
    output = get_cmd_output("where ffmpeg").split("\r\n")

    cwd_path = env_path = None

    if output[0]:
        if output[1]:
            # 环境变量中存在，运行目录中也存在
            cwd_path = output[0]
            env_path = output[1]
        else:
            if output[0].startswith(os.getcwd()):
                # 只存在于运行目录
                cwd_path = output[0]
            else:
                # 只存在于环境变量
                env_path = output[0]

    return {"cwd_path": cwd_path, "env_path": env_path}

def get_ffmpeg_path():
    if not Config.FFmpeg.path:
        # 若未指定 FFmpeg 路径，则自动检测 FFmpeg
        paths = get_all_ffmpeg_path()

        if paths["cwd_path"]:
            # 优先使用运行目录下的 FFmpeg
            Config.FFmpeg.path = paths["cwd_path"]

        if paths["env_path"] and not paths["cwd_path"]:
            # 使用环境变量中的 FFmpeg
            Config.FFmpeg.path = paths["env_path"]
    
def check_ffmpeg_available():
    get_ffmpeg_path()

    # 获取 FFmpeg 输出信息，进而检测 FFmpeg 可用性
    output = get_cmd_output(f'"{Config.FFmpeg.path}" -version')

    if "ffmpeg version" in output:
        Config.FFmpeg.available = True

def get_current_time():
    return datetime.strftime(datetime.now(), "%Y/%m/%d %H:%M:%S")

def save_log(returncode, output):
    with open("error.log", "w", encoding = "utf-8") as f:
        f.write(f"时间：{get_current_time()} 返回值：{returncode}\n错误信息：\n{output}")