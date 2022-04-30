import re
import os
import json
import math
import requests

from utils.config import Config

quality_wrap = {"超高清 8K":127, "杜比视界":126, "真彩 HDR":125, "超清 4K":120, "高清 1080P60":116, "高清 1080P+":112, "高清 1080P":80, "高清 720P":64, "清晰 480P":32, "流畅 360P":16}

def process_shortlink(url: str):
    return requests.get(url, headers = get_header(), proxies = get_proxy()).url

def get_legal_name(name: str):
    return re.sub('[/\:*?"<>|]', "", name)

def get_header(referer_url = None, cookie = None, chunk_list = None) -> dict:
    header = {"User-Agent":"Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36"}
    header["Cookie"] = "CURRENT_FNVAL=4048"

    if referer_url != None:
        header["Referer"] = referer_url

    if chunk_list != None:
        header["Range"] = "bytes={}-{}".format(chunk_list[0], chunk_list[1])

    if cookie != None and cookie != "":
        header["Cookie"] = header["Cookie"] + ";SESSDATA=" + cookie
    
    return header

def get_proxy() -> dict:
    proxy = {}

    if Config.enable_proxy:
        proxy["https"] = "{}:{}".format(Config.proxy_address, Config.proxy_port)

    return proxy

def get_file_from_url(url: str, filename: str, issubtitle: bool):
    req = requests.get(url, headers = get_header(), proxies = get_proxy())
    req.encoding = "utf-8"
    
    with open(os.path.join(Config.download_path, get_legal_name(filename)), "w", encoding = "utf-8") as f:
        f.write(convert_json_to_srt(req.text) if issubtitle else req.text)

def get_danmaku_subtitle_lyric(name: str, cid: int, bvid: str):
    if Config.save_danmaku:
        danmaku_url = "https://api.bilibili.com/x/v1/dm/list.so?oid={}".format(cid)

        get_file_from_url(danmaku_url, "{}.xml".format(name), False)

    if Config.save_subtitle:
        subtitle_url = "https://api.bilibili.com/x/player.so?id=cid:{}&bvid={}".format(cid, bvid)
        req = requests.get(subtitle_url, headers = get_header(), proxies = get_proxy())

        subtitle_raw = re.findall(r'<subtitle>(.*?)</subtitle>', req.text)[0]
        subtitle_json = json.loads(subtitle_raw)["subtitles"]

        subtitle_num = len(subtitle_json)

        if subtitle_num == 0:
            return

        elif subtitle_num == 1:
            down_url = "https:{}".format(subtitle_json[0]["subtitle_url"])
        
            get_file_from_url(down_url, "{}.srt".format(name), True)

        else:
            for i in range(subtitle_num):
                lan_name = subtitle_json[i]["lan_doc"]
                down_url = "https:{}".format(subtitle_json[i]["subtitle_url"])
            
                get_file_from_url(down_url, "({}) {}.srt".format(lan_name, name), True)
                
    from utils.audio import AudioInfo 
    
    if Config.save_lyric and AudioInfo.lyric != "":
        get_file_from_url(AudioInfo.lyric, "{}.lrc".format(name), False)

def format_size(size: int) -> str:
    if size > 1048576:
        return "{:.1f} GB".format(size / 1024 / 1024)
    elif size > 1024:
        return "{:.1f} MB".format(size / 1024)
    else:
        return "{:.1f} KB".format(size)

def format_data(data: int) -> str:
    if data >= 100000000:
        return "{:.1f}亿".format(data / 100000000)
    elif data >= 10000:
        return "{:.1f}万".format(data / 10000)
    else:
        return str(data)

def format_duration(duration: int) -> str:
    if duration > 10000:
        duration = duration / 1000

    hours = int(duration // 3600)
    mins = int((duration - hours * 3600) // 60)
    secs = int(duration - hours * 3600 - mins * 60)
    
    return str(hours).zfill(2) + ":" + str(mins).zfill(2) + ":" + str(secs).zfill(2) if hours != 0 else str(mins).zfill(2) + ":" + str(secs).zfill(2)

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
