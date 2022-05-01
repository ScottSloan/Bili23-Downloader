import os
import sys
import platform
from configparser import RawConfigParser

class Config:
    default_path = os.path.join(os.getcwd(), "download")
    download_path = os.path.join(os.getcwd(), "download")

    max_thread = 4
    default_quality = 80
    codec = 0
    show_notification = False
    
    user_uuid = user_uname = user_face = user_expire = user_sessdata = ""

    save_danmaku = save_subtitle =  save_lyric = False
    danmaku_format = 0

    show_sections = auto_check_update = show_icon = False
    player_path = ""
    
    enable_proxy = False
    proxy_address = proxy_port = ""

    VERSION = "1.21"
    VERSION_CODE = 121
    RELEASE_DATE = "2022-5-1"
    WEBSITE = "https://github.com/ScottSloan/Bili23-downloader"

    res_logo = res_pause = res_resume = res_delete = res_open = res_info = res_info_video = res_info_bangumi = ""

    platform = platform.platform()
    ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe") if platform.startswith("Windows") else "ffmpeg"
    del_cmd = "del" if platform.startswith("Windows") else "rm"
    rename_cmd = "ren" if platform.startswith("Windows") else "mv"

class Load_Config:
    def __init__(self):
        conf = RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")
        
        path = conf.get("download", "path")

        Config.download_path = path if path != "default" else Config.default_path
        Config.max_thread = conf.getint("download", "max_thread")
        Config.default_quality = conf.getint("download", "default_quality")
        Config.codec = conf.getint("download", "codec")
        Config.show_notification = conf.getboolean("download", "show_notification")

        Config.user_uuid = conf.get("user", "uuid")
        Config.user_uname = conf.get("user", "uname")
        Config.user_face = conf.get("user", "face")
        Config.user_expire = conf.get("user", "expire")
        Config.user_sessdata = conf.get("user", "sessdata")

        Config.save_danmaku = conf.getboolean("danmaku", "save_danmaku")
        Config.danmaku_format = conf.getint("danmaku", "format")

        Config.save_subtitle = conf.getboolean("subtitle", "save_subtitle")
        Config.save_lyric = conf.getboolean("lyric", "save_lyric")

        Config.show_sections = conf.getboolean("other", "show_sections")
        Config.player_path = conf.get("other", "player_path")
        Config.show_icon = conf.getboolean("other", "show_icon")
        Config.auto_check_update = conf.getboolean("other", "auto_check_update")

        Config.enable_proxy = conf.getboolean("proxy", "enable_proxy")
        Config.proxy_address = conf.get("proxy", "ip_address")
        Config.proxy_port = conf.get("proxy", "port")

        self.load_resource()
        
    def load_resource(self):
        Config.res_logo = self.get_resource_path(os.path.join("pic", "logo.ico"))
        Config.res_pause = self.get_resource_path(os.path.join("pic", "pause.png"))
        Config.res_resume = self.get_resource_path(os.path.join("pic", "resume.png"))
        Config.res_delete = self.get_resource_path(os.path.join("pic", "delete.png"))
        Config.res_open = self.get_resource_path(os.path.join("pic", "open.png"))

        Config.res_info = self.get_resource_path(os.path.join("info", "info.html"))
        Config.res_info_video = self.get_resource_path(os.path.join("info", "video_info.html"))
        Config.res_info_bangumi = self.get_resource_path(os.path.join("info", "bangumi_info.html"))

    def get_resource_path(self, relative_path: str) -> str:
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)
        else:
            return os.path.join(os.getcwd(), relative_path)
Load_Config()