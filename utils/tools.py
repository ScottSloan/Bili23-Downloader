import re
import os
import json
import math
import requests
from requests.auth import HTTPProxyAuth

from .config import Config

quality_wrap = {"超高清 8K": 127, "杜比视界": 126, "真彩 HDR": 125, "超清 4K": 120, "高清 1080P60": 116, "高清 1080P+": 112, "高清 1080P": 80, "高清 720P": 64, "清晰 480P": 32, "流畅 360P": 16}
mode_wrap = {"api": 0, "html": 1}
codec_wrap = {"AVC": 0, "HEVC": 1, "AV1": 2}

def process_shortlink(url):
    if not url.startswith("https"):
        url = "https://" + url

    return requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth()).url

def process_activity_url(url):
    re_pattern = r"\"videoID\":\"(.*?)\""
        
    request = requests.get(url, headers = get_header(cookie = Config.user_sessdata), proxies = get_proxy(), auth = get_auth())
    
    try:
        return "ep" + re.findall(re_pattern, request.text.replace("\\", ""), re.S)[0]
    except:
        return ""
        
def get_legal_name(name):
    return re.sub('[/\:*?"<>|]', "", name)

def get_header(referer_url = None, cookie = None, chunk_list = None) -> dict:
    header = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.56"}
    header["Cookie"] = "CURRENT_FNVAL=4048;"

    if referer_url != None:
        header["Referer"] = referer_url

    if chunk_list != None:
        header["Range"] = "bytes={}-{}".format(chunk_list[0], chunk_list[1])

    if cookie != None and cookie != "":
        header["Cookie"] += "SESSDATA=" + cookie
    
    return header

def get_proxy():
    if Config.enable_proxy:
        return {
            "http": "{}:{}".format(Config.proxy_ip, Config.proxy_port),
            "https": "{}:{}".format(Config.proxy_ip, Config.proxy_port)
        }
    else:
        return {}

def get_auth():
    if Config.enable_auth:
        return HTTPProxyAuth(Config.auth_uname, Config.auth_pwd)
    else:
        return HTTPProxyAuth(None, None)

def remove_files(path, name):
    for i in name:
        dir_path = os.path.join(path, i)
        
        if os.path.exists(dir_path):
            os.remove(dir_path)

def format_size(size):
    if size > 1048576:
        return "{:.1f} GB".format(size / 1024 / 1024)
    elif size > 1024:
        return "{:.1f} MB".format(size / 1024)
    else:
        return "{:.1f} KB".format(size)

def save_pic(contents, path):
    if os.path.exists(path):
        return

    with open(path, "wb") as f:
        f.write(contents)

def get_face_pic(url):
    request =  requests.get(url = url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
    
    save_pic(request.content, Config.res_face)

    return Config.res_face

def get_level_pic(level):
    request = requests.get(url = Config.app_level.format(level), headers = get_header(), proxies = get_proxy(), auth = get_auth())
    
    save_pic(request.content, Config.res_level)
    
    return Config.res_level

def get_vip_badge_pic(url): 
    request = requests.get(url = url, headers = get_header(), proxies = get_proxy(), auth = get_auth())

    save_pic(request.content, Config.res_badge)

    return Config.res_badge

def get_file_from_url(url, name, subtitle = False):
    request = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
    request.encoding = "utf-8"
    
    with open(os.path.join(Config.download_path, get_legal_name(name)), "w", encoding = "utf-8") as f:
        if subtitle:
            f.write(convert_json_to_srt(request.text))
        else:
            f.write(request.text)

def convert_json_to_srt(data):
    json_data = json.loads(data)

    file = ""

    for index, value in enumerate(json_data["body"]):
        file += "{}\n".format(index)
        start = value["from"]
        end = value["to"]
        file += format_subtitle_timetag(start, False) + " --> " + format_subtitle_timetag(end, True) + "\n"
        file += value["content"] + "\n\n"
    
    return file

def check_update_json():
    update_request = requests.get(url = Config.app_update_json, headers = get_header(), proxies = get_proxy(), auth = get_auth())
    update_json = json.loads(update_request.text)
    
    if update_json["version_code"] > Config.app_version_code:
        changelog_request = requests.get(url = Config.app_changelog, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        changelog_request.encoding = "utf-8"

        update_json["changelog"] = changelog_request.text
    
    return update_json

def get_changelog():
    changelog_request = requests.get(url = Config.app_changelog, headers = get_header(), proxies = get_proxy(), auth = get_auth())
    changelog_request.encoding = "utf-8"

    return changelog_request.text
    
def find_str(pattern, string):
    return True if len(re.findall(pattern, string)) !=  0 else False

def format_bangumi_title(episode):
    from .bangumi import BangumiInfo

    if BangumiInfo.type == "电影":
        return BangumiInfo.title + episode["title"]
    else:
        return episode["share_copy"]

def format_duration(duration):
    if duration > 10000:
        duration = duration / 1000

    hours = int(duration // 3600)
    mins = int((duration - hours * 3600) // 60)
    secs = int(duration - hours * 3600 - mins * 60)
    
    return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2) if hours != 0 else str(mins).zfill(2) + ":" + str(secs).zfill(2)

def format_subtitle_timetag(timetag, end):
    hours = math.floor(timetag) // 3600
    mins = (math.floor(timetag) - hours * 3600) // 60
    secs = math.floor(timetag) - hours * 3600 - mins * 60

    if not end:
        msecs = int(math.modf(timetag)[0] * 100)
    else:
        msecs = abs(int(math.modf(timetag)[0] * 100 -1))

    return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2) + "," + str(msecs).zfill(2)
