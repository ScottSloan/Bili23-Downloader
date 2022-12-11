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
    res_face = os.path.join(_res_path, "face.jpg")
    res_level = os.path.join(_res_path, "level.png")
    res_badge = os.path.join(_res_path, "badge.png")
    
    download_path = ""

    max_thread = 4
    codec = "HEVC"
    default_quality = 80
    show_notification = False

    enable_proxy = False
    proxy_ip = ""
    proxy_port = ""
    enable_auth = False
    auth_uname = ""
    auth_pwd = ""

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
    user_vip_status = ""
    user_vip_badge = ""
    user_expire = ""
    user_login = False

    app_name = "Bili23 Downloader GUI"
    app_version = "1.36"
    app_version_code = 1361
    app_date = "2022-12-11"
    
    platform = platform.platform()

    ffmpeg_available = False
    ffmpeg_path = ""

    def set_user_info():
        conf = RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")

        conf.set("user", "uid", Config.user_uid)
        conf.set("user", "uname", Config.user_name)
        conf.set("user", "face", Config.user_face)
        conf.set("user", "expire", Config.user_expire)
        conf.set("user", "level", Config.user_level)
        conf.set("user", "vip_status", str(Config.user_vip_status))
        conf.set("user", "vip_badge", Config.user_vip_badge)
        conf.set("user", "sessdata", Config.user_sessdata)

        with open(os.path.join(os.getcwd(), "config.conf"), "w", encoding = "utf-8") as f:
            conf.write(f)

    def reset_user_info():
        Config.user_name = Config.user_uid = Config.user_face = Config.user_expire = Config.user_sessdata = Config.user_level = Config.user_vip_badge = ""
        Config.user_login = False
        Config.user_vip_status = 0

class LoadConfig:
    def __init__(self):
        conf = RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")

        download_path = conf.get("download", "path")

        Config.download_path = download_path if download_path != "" else os.path.join(os.getcwd(), "download")
        Config.max_thread = conf.getint("download", "thread")
        Config.codec = conf.get("download", "codec")
        Config.default_quality = conf.getint("download", "quality")
        Config.show_notification = conf.getboolean("download", "notification")
        
        Config.save_danmaku = conf.getboolean("save", "danmaku")
        Config.save_subtitle = conf.getboolean("save", "subtitle")
        Config.save_lyric = conf.getboolean("save", "lyric")
        
        Config.show_sections = conf.getboolean("misc", "sections")
        Config.player_path = conf.get("misc", "player_path")
        Config.check_update = conf.getboolean("misc", "update")
        Config.debug = conf.getboolean("misc", "debug")
        
        Config.enable_proxy = conf.getboolean("proxy", "enable")
        Config.proxy_ip = conf.get("proxy", "address")
        Config.proxy_port = conf.get("proxy", "port")

        Config.enable_auth = conf.getboolean("auth", "auth")
        Config.auth_uname = conf.get("auth", "uname")
        Config.auth_pwd = conf.get("auth", "pwd")

        Config.user_uid = conf.get("user", "uid")
        Config.user_name = conf.get("user", "uname")
        Config.user_face = conf.get("user", "face")
        Config.user_level = conf.get("user", "level")
        Config.user_expire = conf.get("user", "expire")
        Config.user_vip_status = conf.getint("user", "vip_status")
        Config.user_vip_badge = conf.get("user", "vip_badge")
        Config.user_sessdata = conf.get("user", "sessdata")
        
        if Config.user_name != "":
            Config.user_login = True
            
        self.check_download_path_available()
        self.check_ffmpeg_available()
        
    def check_download_path_available(self):
        if not os.path.exists(Config.download_path):
            os.makedirs(Config.download_path)

    def check_ffmpeg_available(self):
        local_path = os.path.join(os.getcwd(), "ffmpeg.exe")

        if subprocess.call(args = "ffmpeg -version", shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE) == 0:
            Config.ffmpeg_path = "ffmpeg"
            Config.ffmpeg_available = True

        elif os.path.exists(local_path):
            Config.ffmpeg_path = local_path
            Config.ffmpeg_available = True
        else:
            Config.ffmpeg_available = False

LoadConfig()