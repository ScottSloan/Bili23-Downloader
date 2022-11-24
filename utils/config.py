import os
import platform
import subprocess
from configparser import RawConfigParser

class Config:
    _res_path = os.path.join(os.getcwd(), "res")

    res_icon = os.path.join(_res_path, "icon.ico")
    res_pause = os.path.join(_res_path, "pause.png")
    res_continue = os.path.join(_res_path, "continue.png")
    res_delete = os.path.join(_res_path, "delete.png")

    download_path = ""

    max_thread = 4
    codec = "HEVC"
    default_quality = 80
    show_notification = False

    enable_proxy = False
    proxy_ip = ""
    proxy_port = ""

    show_sections = False
    save_danmaku = False
    save_subtitle = False
    save_lyric = False
    
    player_path = ""
    check_update = False
    debug = True
    
    user_uid = 0
    user_name = ""
    user_face = ""
    user_level = 0
    user_sessdata = ""
    user_expire = ""

    app_name = "Bili23 Downloader"
    app_version = "1.30"
    app_version_code = 1301
    app_date = "2022-11-24"
    app_website = "https://github.com/ScottSloan/Bili23-Downloader"

    platform = platform.platform()
    ffmpeg_available = True if subprocess.call(args = "ffmpeg -version", shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE) == 0 else False

class LoadConfig:
    def __init__(self):
        conf = RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")

        download_path = conf.get("user", "uid")

        Config.download_path = download_path if download_path != "" else os.path.join(os.getcwd(), "download")
        Config.user_uid = conf.get("user", "uid")
        Config.user_name = conf.get("user", "uname")
        Config.user_face = conf.get("user", "face")
        Config.user_level = conf.get("user", "level")
        Config.user_expire = conf.get("user", "expire")
        Config.user_sessdata = conf.get("user", "sessdata")

changelog = ""

LoadConfig()