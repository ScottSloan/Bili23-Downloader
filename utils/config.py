import os
import platform
import configparser

class Config:
    default_path = os.path.join(os.getcwd(), "download")
    download_path = os.path.join(os.getcwd(), "download")
    max_thread = 4
    default_quality = 80
    codec = 0
    show_notification = False

    cookie_sessdata = ""

    save_danmaku = False
    danmaku_format = 0

    save_subtitle = False
    auto_merge_subtitle = False

    show_sections = False
    player_path = ""
    auto_check_update = False
    
    enable_proxy = False
    proxy_address = ""
    proxy_port = ""

    _version = "1.14"
    _date = "2022-4-3"
    _website = "https://github.com/ScottSloan/Bili23-downloader"
    _logo = os.path.join(os.getcwd(), "pic", "logo.ico")
    _platform = platform.platform()
    _ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe") if _platform.startswith("Windows") else "ffmpeg"
    _del_cmd = "del" if _platform.startswith("Windows") else "rm"
    _rename_cmd = "ren" if _platform.startswith("Windows") else "mv"

    _info_base_path = os.path.join(os.getcwd(), "preview_info")
    _info_video_path = os.path.join(_info_base_path, "video_info.html")
    _info_bangumi_path = os.path.join(_info_base_path, "bangumi_info.html")
    _info_html = os.path.join(_info_base_path, "info.html")

class Load_Config:
    conf = configparser.RawConfigParser()
    conf.read(os.path.join(os.getcwd(), "config.conf"))
    
    path = conf.get("download", "path")

    Config.download_path = path if path != "default" else Config.default_path
    Config.max_thread = conf.getint("download", "max_thread")
    Config.default_quality = conf.getint("download", "default_quality")
    Config.codec = conf.getint("download", "codec")
    Config.show_notification = conf.getboolean("download", "show_notification")

    Config.cookie_sessdata = conf.get("cookie", "sessdata")

    Config.save_danmaku = conf.getboolean("danmaku", "save_danmaku")
    Config.danmaku_format = conf.getint("danmaku", "format")

    Config.save_subtitle = conf.getboolean("subtitle", "save_subtitle")
    Config.auto_merge_subtitle = conf.getboolean("subtitle", "auto_merge_subtitle")

    Config.show_sections = conf.getboolean("other", "show_sections")
    Config.player_path = conf.get("other", "player_path")
    Config.auto_check_update = conf.getboolean("other", "auto_check_update")

    Config.enable_proxy = conf.getboolean("proxy", "enable_proxy")
    Config.proxy_address = conf.get("proxy", "ip_address")
    Config.proxy_port = conf.get("proxy", "port")

Load_Config()