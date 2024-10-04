import os
import wx
import platform
from configparser import RawConfigParser

class Config:
    class Sys:
        platform = platform.system().lower()
        dark_mode = False

    class APP:
        name = "Bili23 Downloader"

        version = "1.51"
        version_code = 1510

        release_date = "2024/10/04"

    class Proxy:
        proxy = 1
        auth = False

        ip = port = uname = passwd = None
    
    class User:
        base_path = path = face_path = None

        login = False
        uname = face = sessdata = None

    class Misc:
        show_episodes = 1

        auto_select = debug = check_update = False

        player_path = None

    class Download:
        path = None
        
        resolution = 80
        sound_quality = 30280
        codec = "HEVC"

        max_thread = 4
        max_download = 1

        show_notification = False

        add_number = False

        speed_limit = False
        speed_limit_in_mb = 10
    
    class Merge:
        auto_clean = False

    class Type:
        VIDEO = 1                               # 用户投稿视频
        BANGUMI = 2                             # 番组

        VIDEO_TYPE_SINGLE = 1                   # 单个视频
        VIDEO_TYPE_PAGES = 2                    # 分 P 视频
        VIDEO_TYPE_SECTIONS = 3                 # 合集

        MERGE_TYPE_V_A = 0                      # 合成视频和音频
        MERGE_TYPE_VIDEO = 1                    # 仅下载视频
        MERGE_TYPE_AUDIO = 2                    # 仅下载音频

        EPISODES_SINGLE = 0                     # 只解析单个视频
        EPISODES_IN_SECTION = 1                 # 解析视频所在合集
        EPISODES_ALL_SECTIONS = 2               # 解析全部合集 

        PROXY_DISABLE = 0                       # 不使用代理
        PROXY_FOLLOW = 1                        # 跟随系统
        PROXY_MANUAL = 2                        # 手动设置
        
        ERROR_CODE_Invalid_URL = 100            # URL 无效
        ERROR_CODE_ParseError = 101             # 解析异常
        ERROR_CODE_VIP_Required = 102           # 需要大会员
        ERROR_CODE_RequestError = 103           # 请求异常
        ERROR_CODE_UnknownError = 104           # 未知错误

        REQUEST_CODE_SSLERROR = 200             # SSLERROR
        REQUEST_CODE_TimeOut = 201              # TimeOut
        REQUEST_CODE_TooManyRedirects = 202     # TooManyRedirects
        REQUEST_CODE_ConnectionError = 203      # ConnectionError
        
        STATUS_CODE_0 = 0                       # 请求成功
        STATUS_CODE_400 = -400                  # 请求错误
        STATUS_CODE_403 = -403                  # 权限不足
        STATUS_CODE_404 = -404                  # 视频不存在
        STATUS_CODE_62002 = 62002               # 稿件不可见
        STATUS_CODE_62004 = 62004               # 稿件审核中
        STATUS_CODE_62012 = 62012               # 仅 UP 主自己可见
    
    class Temp:
        download_window_pos = None

        update_json = None

    class FFmpeg:
        path = None
        available = False

class Audio:
    audio_quality = None

    audio_only = False
    
    # 各音质是否存在
    q_hires = False
    q_dolby = False
    q_192k = False
    q_132k = False
    q_64k = False

class Download:
    current_type = None
    
    download_list = []

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
        Config.Download.max_download = self.config.getint("download", "max_download")
        Config.Download.max_thread = self.config.getint("download", "max_thread")
        Config.Download.resolution = self.config.getint("download", "resolution")
        Config.Download.sound_quality = self.config.getint("download", "sound_quality")
        Config.Download.codec = self.config.get("download", "codec")
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
        Config.Proxy.proxy = self.config.getint("proxy", "proxy")
        Config.Proxy.ip = self.config.get("proxy", "ip")
        Config.Proxy.port = self.config.get("proxy", "port")

        Config.Proxy.auth = self.config.getboolean("proxy", "auth")
        Config.Proxy.uname = self.config.get("proxy", "uname")
        Config.Proxy.passwd = self.config.get("proxy", "passwd")

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