import os
import platform
import configparser

class Config:
    default_path = os.path.join(os.getcwd(), "download")
    download_path = os.path.join(os.getcwd(), "download")
    max_thread = 4
    default_quality = 80
    show_notification = False

    cookie_sessdata = ""

    show_sections = False
    save_danmaku = False
    save_subtitle = False
    auto_merge_subtitle = False
    auto_check_update = False
    
    enable_proxy = False
    proxy_address = ""
    proxy_port = 0

    _version = "1.14"
    _date = "2022-3-19"
    _website = "https://github.com/ScottSloan/Bili23-downloader"
    _logo = os.path.join(os.getcwd(), "pic", "logo.ico")
    _platform = platform.platform()
    _ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
    _del_cmd = "del" if _platform.startswith("Windows") else "rm"

    _info_base_path = os.path.join(os.getcwd(), "preview_info")
    _info_video_path = os.path.join(_info_base_path, "video_info.html")
    _info_bangumi_path = os.path.join(_info_base_path, "bangumi_info.html")
    _info_html = os.path.join(_info_base_path, "info.html")
    _info_cover = "cover"

class Load_Config:
    conf = configparser.RawConfigParser()
    conf.read(os.path.join(os.getcwd(), "config.conf"))
    
    path = conf.get("download", "path")

    Config.download_path = path if path != "default" else Config.default_path
    Config.max_thread = conf.getint("download", "max_thread")
    Config.default_quality = conf.getint("download", "default_quality")
    Config.show_notification = conf.getboolean("download", "show_notification")

    Config.cookie_sessdata = conf.get("cookie", "sessdata")

    Config.show_sections = conf.getboolean("options", "show_sections")
    Config.save_danmaku = conf.getboolean("options", "save_danmaku")
    Config.save_subtitle = conf.getboolean("options", "save_subtitle")
    Config.auto_merge_subtitle = conf.getboolean("options", "auto_merge_subtitle")
    Config.auto_check_update = conf.getboolean("options", "auto_check_update")

    Config.enable_proxy = conf.getboolean("proxy", "enable_proxy")
    Config.proxy_address = conf.get("proxy", "ip_address")
    Config.proxy_port = conf.get("proxy", "port")

Load_Config()