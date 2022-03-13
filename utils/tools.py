import re
import os
import wx
import json
import requests
import subprocess

from utils.config import Config

quality_wrap = {"超高清 8K":127, "真彩 HDR":125, "超清 4K":120, "高清 1080P60":116, "高清 1080P+":112, "高清 1080P":80, "高清 720P":64, "清晰 480P":32, "流畅 360P":16}

def merge_video_audio(out_name: str, on_merge):
    wx.CallAfter(on_merge)

    cmd = 'cd {} && ffmpeg -i audio.mp3 -i video.mp4 -acodec copy -vcodec copy "{}".mp4 && {} video.mp4 audio.mp3'.format(Config.download_path, get_legal_name(out_name), Config._del_cmd)
    
    process = subprocess.Popen(cmd, shell = True)
    process.wait()
    
def process_shortlink(url: str):
    return requests.get(url, headers = get_header()).url

def get_legal_name(name: str):
    return re.sub('[/\:*?"<>|]', "", name)

def get_header(referer_url = None, cookie = None, chunk_list = None) -> str:
    header = {"User-Agent":"Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"}
    
    if referer_url != None:
        header["Referer"] = referer_url

    if chunk_list != None:
        header["Range"] = "bytes={}-{}".format(chunk_list[0], chunk_list[1])

    if cookie != None:
        header["Cookie"] = "SESSDATA=" + cookie

    return header

def get_danmaku(name:str, cid: int):
    if not Config.save_danmaku:
        return

    danmaku_url = "https://api.bilibili.com/x/v1/dm/list.so?oid={}".format(cid)
    req = requests.get(danmaku_url, headers = get_header())
    req.encoding = "utf-8"

    with open(os.path.join(Config.download_path, "{}.xml".format(name)), "w", encoding = "utf-8") as f:
        f.write(req.text)

def remove_file(path: str):
    if os.path.exists(path):
        os.remove(path)

def format_data(data: int) -> str:
    if data >= 100000000:
        return "{:.1f}亿".format(data / 100000000)
    elif data >= 10000:
        return "{:.1f}万".format(data / 10000)
    else:
        return str(data)

def format_duration(duration: int) -> str:
    if str(duration).endswith("000"):
        duration = duration / 1000

    hours = int(duration // 3600)
    mins = int((duration - hours * 3600) // 60)
    secs = int(duration - hours * 3600 - mins * 60)

    hours_ = str(hours) if hours > 9 else "0" + str(hours)
    mins_ = str(mins) if mins > 9 else "0" + str(mins)
    secss_ = str(secs) if secs > 9 else "0" + str(secs)

    return(hours_ + ":" + mins_ + ":" + secss_ if hours != 0 else mins_ + ":" + secss_)

def check_update() -> list:
    url = "https://auth.hanloth.cn/?type=update&pid=39&token=Mjp81YXdxcUk95ad"

    try:
        ver_req = requests.get(url, headers = get_header(), timeout = 2)
    except:
        return None

    ver_json = json.loads(ver_req.text)

    name  = ver_json["name"]
    description = ver_json["description"]
    d_url = ver_json["url"]
    version = ver_json["version"]

    new = True if float(Config._version) < version else False
    return [new, name, description, d_url, version]