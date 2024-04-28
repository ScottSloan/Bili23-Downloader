import re
import os
import json
import random
import ctypes
import requests
from requests.auth import HTTPProxyAuth

from .config import Config

resolution_map = {"超高清 8K": 127, "杜比视界": 126, "真彩 HDR": 125, "超清 4K": 120, "高清 1080P60": 116, "高清 1080P+": 112, "高清 1080P": 80, "高清 720P": 64, "清晰 480P": 32, "流畅 360P": 16}
sound_quality_map = {"Hi-Res 无损": 30251, "杜比全景声": 30250, "192K": 30280, "132K": 30232, "64K": 30216}
codec_id_map = {"AVC": 7, "HEVC": 12, "AV1": 13}

def process_shorklink(url):
    req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
    
    return req.url

def get_header(referer_url = None, cookie = None, chunk_list = None) -> dict:
    header = {
        "Cookie": "CURRENT_FNVAL=4048;",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    }
    
    if referer_url:
        header["Referer"] = referer_url

    if chunk_list:
        header["Range"] = "bytes={}-{}".format(chunk_list[0], chunk_list[1])

    if cookie:
        header["Cookie"] += "SESSDATA=" + cookie
    
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

def get_user_face(url):
    req = requests.get(url, proxies = get_proxy(), auth = get_auth())

    return req.content

def remove_files(path, name):
    for i in name:
        file_path = os.path.join(path, i)
        
        if os.path.exists(file_path):
            ctypes.windll.kernel32.SetFileAttributesW(file_path, 128)
            ctypes.windll.kernel32.DeleteFileW(file_path)

def get_update_json():
    url = "http://api.scott-sloan.cn/Bili23-Downloader/update.json"

    try:
        req = requests.get(url, headers = get_header())
        req.encoding = "utf-8"

        update_json = json.loads(req.text)
        update_json["error"] = False
        
        if update_json["version_code"] > Config.APP.version_code:
            update_json["changelog"] = get_changelog(update_json["version_code"])
            update_json["error"] = False

        return update_json
    except:
        return {"error": True}

def get_changelog(version_code: int):
    url = f"http://api.scott-sloan.cn/Bili23-Downloader/CHANGELOG_{version_code}"

    req = requests.get(url, headers = get_header())
    req.encoding = "utf-8"

    return req.text
    
def get_new_id():
    return random.randint(1000, 9999)

def find_str(pattern, string):
    find = re.findall(pattern, string)
    
    if find:
        return find[0]
    else:
        return None