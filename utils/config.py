import os
import sys
import platform
import configparser

class Config:
    default_path = os.path.join(os.getcwd(), "download")
    download_path = os.path.join(os.getcwd(), "download")

    max_thread = 4
    max_task = 2
    default_quality = 80
    codec = 0
    show_notification = False

    cookie_sessdata = ""

    save_danmaku = save_subtitle = False
    danmaku_format = 0

    show_sections = auto_check_update = False
    player_path = ""
    
    enable_proxy = False
    proxy_address = proxy_port = ""

    VERSION = "1.20"
    VERSION_CODE = "120"
    RELEASE_DATE = "2022-4-9"
    WEBSITE = "https://github.com/ScottSloan/Bili23-downloader"

    res_logo = res_pause = res_resume = res_delete = res_open = res_info = res_info_video = res_info_bangumi = res_info_cover = ""

    platform = platform.platform()
    ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe") if platform.startswith("Windows") else "ffmpeg"
    del_cmd = "del" if platform.startswith("Windows") else "rm"
    rename_cmd = "ren" if platform.startswith("Windows") else "mv"

class Load_Config:
    def __init__(self):
        conf = configparser.RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"))
        
        path = conf.get("download", "path")

        Config.download_path = path if path != "default" else Config.default_path
        Config.max_thread = conf.getint("download", "max_thread")
        Config.max_task = conf.getint("download", "max_task")
        Config.default_quality = conf.getint("download", "default_quality")
        Config.codec = conf.getint("download", "codec")
        Config.show_notification = conf.getboolean("download", "show_notification")

        Config.cookie_sessdata = conf.get("cookie", "sessdata")

        Config.save_danmaku = conf.getboolean("danmaku", "save_danmaku")
        Config.danmaku_format = conf.getint("danmaku", "format")

        Config.save_subtitle = conf.getboolean("subtitle", "save_subtitle")

        Config.show_sections = conf.getboolean("other", "show_sections")
        Config.player_path = conf.get("other", "player_path")
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

    def get_resource_path(self, relative_path: str):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.getcwd(), relative_path)

Load_Config()