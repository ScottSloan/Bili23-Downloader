import re
import os
import wx
import json
import math
import requests

from utils.config import Config

quality_wrap = {"超高清 8K":127, "真彩 HDR":125, "超清 4K":120, "高清 1080P60":116, "高清 1080P+":112, "高清 1080P":80, "高清 720P":64, "清晰 480P":32, "流畅 360P":16}

def merge_video_audio(out_name: str, on_merge):
    wx.CallAfter(on_merge)

    cmd = '''cd {} && {} -i audio.mp3 -i video.mp4 -acodec copy -vcodec copy video_merged.mp4 && {} video.mp4 audio.mp3'''.format(Config.download_path, Config._ffmpeg_path, Config._del_cmd)
    os.system(cmd)

    merge_subtitle(out_name)

    cmd2 = '''cd {} && {} video_merged.mp4 "{}.mp4"'''.format(Config.download_path, Config._rename_cmd, get_legal_name(out_name))
    os.system(cmd2)
    
def merge_subtitle(out_name: str):
    if not (Config.auto_merge_subtitle and os.path.exists(os.path.join(Config.download_path, "{}.srt".format(out_name)))):
        return

    cmd = '''cd {} && {} -i video_merged.mp4 -vf "subtitles='{}.srt'" video_sub.mp4 && {} video_merged.mp4 "{}.srt" && {} video_sub.mp4 video_merged.mp4'''.format(Config.download_path, Config._ffmpeg_path, get_legal_name(out_name), Config._del_cmd, get_legal_name(out_name), Config._rename_cmd)

    os.system(cmd)

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

def get_file_from_url(url: str, filename: str, issubtitle: bool):
    req = requests.get(url, headers = get_header())
    req.encoding = "utf-8"
    
    with open(os.path.join(Config.download_path, filename), "w", encoding = "utf-8") as f:
        f.write(convert_json_to_srt(req.text) if issubtitle else req.text)

def get_danmaku_subtitle(name: str, cid: int, bvid: str):
    if Config.save_danmaku:
        danmaku_url = "https://api.bilibili.com/x/v1/dm/list.so?oid={}".format(cid)
        get_file_from_url(danmaku_url, "{}.xml".format(name), False)

    if Config.save_subtitle:
        subtitle_url = "https://api.bilibili.com/x/player.so?id=cid:{}&bvid={}".format(cid, bvid)
        req = requests.get(subtitle_url, headers = get_header())

        subtitle_raw = re.findall(r'<subtitle>(.*?)</subtitle>', req.text)[0]
        subtitle_json = json.loads(subtitle_raw)["subtitles"]

        if len(subtitle_json) == 0:
            return
            
        down_url = "https:{}".format(subtitle_json[0]["subtitle_url"])
        
        get_file_from_url(down_url, "{}.srt".format(name), True)

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
    if duration > 1000000:
        duration = duration / 1000

    hours = int(duration // 3600)
    mins = int((duration - hours * 3600) // 60)
    secs = int(duration - hours * 3600 - mins * 60)
    
    return(str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2) if hours != 0 else str(mins).zfill(2) + ":" + str(secs).zfill(2))

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

def convert_json_to_srt(data: str) -> str:
    json_data = json.loads(data)

    file = ""
    for index, value in enumerate(json_data["body"]):
        file += "{}\n".format(index)
        start = value["from"]
        end = value["to"]
        file += process_duration(start, False) + " --> " + process_duration(end, True) + "\n"
        file += value["content"] + "\n\n"
    
    return file

def process_duration(duration: int, isend: bool) -> str:
    hours = math.floor(duration) // 3600
    mins = (math.floor(duration) - hours * 3600) // 60
    secs = math.floor(duration) - hours * 3600 - mins * 60

    if not isend:
        msecs = int(math.modf(duration)[0] * 100)
    else:
        msecs = abs(int(math.modf(duration)[0] * 100 -1))

    return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2) + "," + str(msecs).zfill(2)
