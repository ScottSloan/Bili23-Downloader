import re
import os
import json
import math
import requests

from .config import Config

quality_wrap = {"超高清 8K": 127, "杜比视界": 126, "真彩 HDR": 125, "超清 4K": 120, "高清 1080P60": 116, "高清 1080P+": 112, "高清 1080P": 80, "高清 720P": 64, "清晰 480P": 32, "流畅 360P": 16}
mode_wrap = {"api": 0, "html": 1}
codec_wrap = {"AVC": 0, "HEVC": 1, "AV1": 2}

def process_shortlink(url):
    if not url.startswith("https"):
        url = "https://" + url

    return requests.get(url, headers = get_header(), proxies = get_proxy()).url

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
    proxy = {}

    if Config.enable_proxy:
        proxy["http"] = "{}:{}".format(Config.proxy_ip, Config.proxy_port)

    return proxy

def remove_files(path, name):
    for i in name:
        os.remove(os.path.join(path, i))

def format_size(size):
    if size > 1048576:
        return "{:.1f} GB".format(size / 1024 / 1024)
    elif size > 1024:
        return "{:.1f} MB".format(size / 1024)
    else:
        return "{:.1f} KB".format(size)

def save_pic(contents, path):
    with open(path, "wb") as f:
        f.write(contents)

def get_face_pic(url):
    face_path = os.path.join(os.getcwd(), "res", "face.jpg")
    
    if not os.path.exists(face_path):
        save_pic(requests.get(url).content, face_path)

    return face_path

def get_level_pic(level):
    web_url = "https://scottsloan.github.io/Bili23-Downloader/level/level{}.png".format(level)
    level_path = os.path.join(os.getcwd(), "res", "level.png")
    
    if not os.path.exists(level_path):
        save_pic(requests.get(web_url).content, level_path)
    
    return level_path

def get_file_from_url(url, name, subtitle = False):
    request = requests.get(url, headers = get_header(), proxies = get_proxy())
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
    update_request = requests.get("https://scottsloan.github.io/Bili23-Downloader/update.json")
    update_json = json.loads(update_request.text)
    
    if update_json["version_code"] > Config.app_version_code:
        changelog_request = requests.get("https://scottsloan.github.io/Bili23-Downloader/CHANGELOG")
        changelog_request.encoding = "utf-8"

        update_json["changelog"] = changelog_request.text
    
    return update_json

def get_changelog():
    changelog_request = requests.get("https://scottsloan.github.io/Bili23-Downloader/CHANGELOG")
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
