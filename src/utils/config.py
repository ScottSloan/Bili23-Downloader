import os
import platform
from configparser import RawConfigParser
from typing import List

class Config:
    class Sys:
        platform: str = platform.system().lower()
        dark_mode: bool = False

    class APP:
        name: str = "Bili23 Downloader"

        version: str = "1.51.0"
        version_code: int = 1510

        release_date: str = "2024/10/14"

    class Proxy:
        proxy_enable_status: int = 1
        auth_enable: bool = False

        proxy_ip_addr: str = ""
        proxy_port: int = 0
        auth_uname: str = ""
        auth_passwd: str = ""
    
    class User:
        base_path: str = ""
        path: str = ""
        face_path: str = ""

        login: bool = False
        uname: str = ""
        face: str = ""
        sessdata: str = ""

    class Misc:
        show_episodes: int = 1

        auto_select: bool = False
        debug: bool = False
        check_update: bool = False

        player_path: str = ""

    class Download:
        path: str = ""
        
        video_quality_id: int = 200
        audio_quality_id: int = 30300
        video_codec: int = 12

        max_thread_count: int = 4
        max_download_count: int = 1

        show_notification: bool = False

        add_number: bool = False

        speed_limit: bool = False
        speed_limit_in_mb: int = 10
    
    class Merge:
        auto_clean: bool = False

    class Type:
        VIDEO: int = 1                               # 用户投稿视频
        BANGUMI: int = 2                             # 番组

        VIDEO_TYPE_SINGLE: int = 1                   # 单个视频
        VIDEO_TYPE_PAGES: int = 2                    # 分 P 视频
        VIDEO_TYPE_SECTIONS: int = 3                 # 合集

        MERGE_TYPE_ALL: int = 0                      # 合成视频和音频
        MERGE_TYPE_VIDEO: int = 1                    # 仅下载视频
        MERGE_TYPE_AUDIO: int = 2                    # 仅下载音频

        EPISODES_SINGLE: int = 0                     # 只解析单个视频
        EPISODES_IN_SECTION: int = 1                 # 解析视频所在合集
        EPISODES_ALL_SECTIONS: int = 2               # 解析全部合集 

        PROXY_DISABLE: int = 0                       # 不使用代理
        PROXY_FOLLOW: int = 1                        # 跟随系统
        PROXY_MANUAL: int = 2                        # 手动设置
    
    class Temp:
        download_window_pos = None

        update_json = None

    class FFmpeg:
        path: str = ""
        available: bool = False

class Audio:
    audio_quality_id: int = 0

    # 仅下载音频标识符
    audio_only: bool = False
    
    # 各音质标识符
    q_hires: bool = False
    q_dolby: bool = False
    q_192k: bool = False
    q_132k: bool = False
    q_64k: bool = False

class Download:
    current_parse_type: int = 0
    
    download_list: List = []

class ConfigUtils:
    def __init__(self):
        self.path = os.path.join(os.getcwd(), "config.ini")

        self.create_user_dirs()

        self.load_config()

        self.create_download_dirs()

        self.init_ffmpeg()

    def init_ffmpeg(self):
        from utils.tools import check_ffmpeg_available

        check_ffmpeg_available()

    def init_user(self):
        match Config.Sys.platform:
            case "windows":
                Config.User.base_path = os.path.join(os.getenv("LOCALAPPDATA"), "Bili23 Downloader")

            case "linux" | "darwin":
                Config.User.base_path = os.path.join(os.path.expanduser("~"), ".Bili23 Downloader")

        Config.User.path = os.path.join(Config.User.base_path, "user.ini")

        Config.User.face_path = os.path.join(Config.User.base_path, "face.jpg")

    def load_config(self):
        self.config = RawConfigParser()
        self.config.read(self.path, encoding = "utf-8")

        self.user_config = RawConfigParser()
        self.user_config.read(Config.User.path, encoding = "utf-8")

        download_path = self.config.get("download", "path")

        # download
        Config.Download.path = download_path if download_path else os.path.join(os.getcwd(), "download")
        Config.Download.max_download_count = self.config.getint("download", "max_download")
        Config.Download.max_thread_count = self.config.getint("download", "max_thread")
        Config.Download.video_quality_id = self.config.getint("download", "resolution")
        Config.Download.audio_quality_id = self.config.getint("download", "sound_quality")
        Config.Download.video_codec = self.config.getint("download", "codec")
        Config.Download.show_notification = self.config.getint("download", "notification")
        Config.Download.add_number = self.config.getboolean("download", "add_number")
        Config.Download.speed_limit = self.config.getboolean("download", "speed_limit")
        Config.Download.speed_limit_in_mb = self.config.getint("download", "speed_limit_in_mb")

        # merge
        Config.FFmpeg.path = self.config.get("merge", "ffmpeg_path")
        Config.Merge.auto_clean = self.config.getboolean("merge", "auto_clean")

        # user
        Config.User.login = self.user_config.getboolean("user", "login")
        Config.User.face = self.user_config.get("user", "face")
        Config.User.uname = self.user_config.get("user", "uname")
        Config.User.sessdata = self.user_config.get("user", "sessdata")

        # proxy
        Config.Proxy.proxy_enable_status = self.config.getint("proxy", "proxy")
        Config.Proxy.proxy_ip_addr = self.config.get("proxy", "ip")
        Config.Proxy.proxy_port = self.config.get("proxy", "port")

        Config.Proxy.auth_enable = self.config.getboolean("proxy", "auth")
        Config.Proxy.auth_uname = self.config.get("proxy", "uname")
        Config.Proxy.auth_passwd = self.config.get("proxy", "passwd")

        # misc
        Config.Misc.show_episodes = self.config.getint("misc", "show_episodes")
        Config.Misc.auto_select = self.config.getboolean("misc", "auto_select")
        Config.Misc.player_path = self.config.get("misc", "player_path")
        Config.Misc.check_update = self.config.getboolean("misc", "check_update")
        Config.Misc.debug = self.config.getboolean("misc", "debug")

    def create_download_dirs(self):
        if not os.path.exists(Config.Download.path):
            os.makedirs(Config.Download.path)

    def create_user_dirs(self):
        self.init_user()

        if not os.path.exists(Config.User.base_path):
            os.makedirs(Config.User.base_path)

        if not os.path.exists(Config.User.path):
            self.create_user_ini()
    
    def create_user_ini(self):
        user_conf = RawConfigParser()
        user_conf.read(Config.User.path, encoding = "utf-8")

        user_conf.add_section("user")
        user_conf.set("user", "login", "0")
        user_conf.set("user", "face", "")
        user_conf.set("user", "uname", "")
        user_conf.set("user", "sessdata", "")

        with open(Config.User.path, "w", encoding = "utf-8") as f:
            user_conf.write(f)

    def config_save(self):
        with open(self.path, "w", encoding = "utf-8") as f:
            self.config.write(f)

    def user_config_save(self):
        with open(Config.User.path, "w", encoding = "utf-8") as f:
            self.user_config.write(f)
    
    def save_all_user_config(self):
        conf.user_config.set("user", "login", str(int(Config.User.login)))
        conf.user_config.set("user", "face", Config.User.face)
        conf.user_config.set("user", "uname", Config.User.uname)
        conf.user_config.set("user", "sessdata", Config.User.sessdata)

        conf.user_config_save()

conf = ConfigUtils()