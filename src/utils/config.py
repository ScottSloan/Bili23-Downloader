import os
import platform
from configparser import RawConfigParser
from typing import List

from utils.error import ErrorCallback, process_read_config_exception

class Config:
    class Sys:
        platform: str = platform.system().lower()
        dark_mode: bool = False

    class APP:
        name: str = "Bili23 Downloader"

        version: str = "1.52.0"
        version_code: int = 1520

        release_date: str = "2024/10/20"

    class Proxy:
        proxy_mode: int = 1
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
        episode_display_mode: int = 1

        auto_select: bool = False
        debug: bool = False
        check_update: bool = True

        player_path: str = ""

    class Download:
        path: str = ""
        
        video_quality_id: int = 200
        audio_quality_id: int = 30300
        video_codec: int = 12

        max_thread_count: int = 2
        max_download_count: int = 1

        show_notification: bool = False

        add_number: bool = True

        speed_limit: bool = False
        speed_limit_in_mb: int = 10
    
    class Merge:
        auto_clean: bool = True

    class Type:
        VIDEO: int = 1                               # 用户投稿视频
        BANGUMI: int = 2                             # 番组
        MUSIC: int = 3                               # 音乐 TODO
        LIVE: int = 4                                # 直播 TODO

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

        ErrorCallback.onReadConfigError = self.onError

        if Config.Sys.platform == "windows":
            # Windows 环境下，启用高 DPI 适配
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(2)

        # 检查配置文件是否存在
        if not os.path.exists(self.path):
            self.create_config_ini()

        self.create_user_directory()

        self.load_config()

        self.create_download_directory()

        self.init_ffmpeg()    

    def onError(self):
        # 弹出信息框提示
        import wx

        app = wx.App()

        dlg = wx.MessageDialog(None, "配置文件不兼容\n\n配置文件较旧，不兼容当前版本，继续使用将覆盖旧文件，是否继续？", "警告", wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            os.remove(self.path)

            self.__init__()

        else:
            wx.Exit()

        app.MainLoop()

    def init_ffmpeg(self):
        from utils.tools import check_ffmpeg_available

        check_ffmpeg_available()

    def init_user_config(self):
        match Config.Sys.platform:
            case "windows":
                Config.User.base_path = os.path.join(os.getenv("LOCALAPPDATA"), "Bili23 Downloader")

            case "linux" | "darwin":
                Config.User.base_path = os.path.join(os.path.expanduser("~"), ".Bili23 Downloader")

        Config.User.path = os.path.join(Config.User.base_path, "user.ini")

        Config.User.face_path = os.path.join(Config.User.base_path, "face.jpg")

    @process_read_config_exception
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
        Config.Download.video_quality_id = self.config.getint("download", "video_quality")
        Config.Download.audio_quality_id = self.config.getint("download", "audio_quality")
        Config.Download.video_codec = self.config.getint("download", "video_codec")
        Config.Download.show_notification = self.config.getint("download", "show_notification")
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
        Config.Proxy.proxy_mode = self.config.getint("proxy", "proxy_mode")
        Config.Proxy.proxy_ip_addr = self.config.get("proxy", "ip_addr")
        Config.Proxy.proxy_port = self.config.get("proxy", "port")

        Config.Proxy.auth_enable = self.config.getboolean("proxy", "auth_enable")
        Config.Proxy.auth_uname = self.config.get("proxy", "uname")
        Config.Proxy.auth_passwd = self.config.get("proxy", "passwd")

        # misc
        Config.Misc.episode_display_mode = self.config.getint("misc", "episode_display_mode")
        Config.Misc.auto_select = self.config.getboolean("misc", "auto_select")
        Config.Misc.player_path = self.config.get("misc", "player_path")
        Config.Misc.check_update = self.config.getboolean("misc", "check_update")
        Config.Misc.debug = self.config.getboolean("misc", "debug")

    def create_download_directory(self):
        if not os.path.exists(Config.Download.path):
            os.makedirs(Config.Download.path)

    def create_user_directory(self):
        self.init_user_config()

        if not os.path.exists(Config.User.base_path):
            os.makedirs(Config.User.base_path)

        if not os.path.exists(Config.User.path):
            self.create_user_ini()
    
    def create_config_ini(self):
        self.config = RawConfigParser()
        self.config.read(self.path, encoding = "utf-8")

        # download
        self.config.add_section("download")
        self.config.set("download", "path", Config.Download.path)
        self.config.set("download", "max_download", str(Config.Download.max_download_count))
        self.config.set("download", "max_thread", str(Config.Download.max_thread_count))
        self.config.set("download", "video_quality", str(Config.Download.video_quality_id))
        self.config.set("download", "audio_quality", str(Config.Download.audio_quality_id))
        self.config.set("download", "video_codec", str(Config.Download.video_codec))
        self.config.set("download", "show_notification", str(int(Config.Download.show_notification)))
        self.config.set("download", "add_number", str(int(Config.Download.add_number)))
        self.config.set("download", "speed_limit", str(int(Config.Download.speed_limit)))
        self.config.set("download", "speed_limit_in_mb", str(Config.Download.speed_limit_in_mb))

        # merge
        self.config.add_section("merge")
        self.config.set("merge", "ffmpeg_path", Config.FFmpeg.path)
        self.config.set("merge", "auto_clean", str(int(Config.Merge.auto_clean)))

        # proxy
        self.config.add_section("proxy")
        self.config.set("proxy", "proxy_mode", str(Config.Proxy.proxy_mode))
        self.config.set("proxy", "ip_addr", Config.Proxy.proxy_ip_addr)
        self.config.set("proxy", "port", "")

        self.config.set("proxy", "auth_enable", str(int(Config.Proxy.auth_enable)))
        self.config.set("proxy", "uname", Config.Proxy.auth_uname)
        self.config.set("proxy", "passwd", Config.Proxy.auth_passwd)

        # misc
        self.config.add_section("misc")
        self.config.set("misc", "episode_display_mode", str(Config.Misc.episode_display_mode))
        self.config.set("misc", "auto_select", str(int(Config.Misc.auto_select)))
        self.config.set("misc", "player_path", Config.Misc.player_path)
        self.config.set("misc", "check_update", str(int(Config.Misc.check_update)))
        self.config.set("misc", "debug", str(int(Config.Misc.debug)))

        self.config_save()

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