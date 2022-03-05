import re
import os
import subprocess

from utils.config import Config

def combine_video_audio(out_name: str, on_combine):
    on_combine(out_name)

    cmd = 'cd {} && ffmpeg -i audio.mp3 -i video.mp4 -acodec copy -vcodec copy "{}".mp4 && rm video.mp4 audio.mp3'.format(Config.download_path, get_legal_name(out_name))
    process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, encoding = "gbk")
    process.wait()

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
    secs = int(duration - hours * 3600 - mins * 60) - 1

    hours_ = str(hours) if hours > 9 else "0" + str(hours)
    mins_ = str(mins) if mins > 9 else "0" + str(mins)
    secss_ = str(secs) if secs > 9 else "0" + str(secs)

    return(hours_ + ":" + mins_ + ":" + secss_ if hours != 0 else mins_ + ":" + secss_)