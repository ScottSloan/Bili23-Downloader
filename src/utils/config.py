import os
import json
import platform
from typing import List, Dict

class Config:
    class Sys:
        platform: str = platform.system().lower()
        dark_mode: bool = False

    class APP:
        name: str = "Bili23 Downloader"

        version: str = "1.54.0"
        version_code: int = 1540

        # 断点续传文件最低支持版本号
        _task_file_min_version_code: int = 1532

        release_date: str = "2024/12/20"

        app_config_path: str = os.path.join(os.getcwd(), "config.json")

    class Proxy:
        proxy_mode: int = 1
        enable_auth: bool = False

        proxy_ip: str = ""
        proxy_port: int = None
        auth_username: str = ""
        auth_password: str = ""
    
    class User:
        directory: str = ""
        download_file_directory: str = ""
        user_config_path: str = ""
        face_path: str = ""

        login: bool = False
        username: str = ""
        face_url: str = ""
        sessdata: str = ""

    class Misc:
        episode_display_mode: int = 1

        show_episode_full_name: bool = True
        auto_select: bool = False
        enable_debug: bool = False
        auto_check_update: bool = True

        player_preference: int = 0
        player_path: str = ""

    class Download:
        path: str = os.path.join(os.getcwd(), "download")
        
        video_quality_id: int = 200
        audio_quality_id: int = 30300
        video_codec_id: int = 7

        max_thread_count: int = 2
        max_download_count: int = 1

        enable_dolby: bool = False

        enable_notification: bool = False
        delete_history: bool = False
        add_number: bool = True

        enable_speed_limit: bool = False
        speed_limit_in_mb: int = 10

        enable_custom_cdn: bool = True
        custom_cdn_mode: int = 0
        custom_cdn: str = "upos-sz-mirror08c.bilivideo.com"
    
    class Merge:
        override_file: bool = False
        m4a_to_mp3: bool = True
        auto_clean: bool = True

    class Type:
        UNDEFINED: int = 0                           # 未定义

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
        PROXY_CUSTOM: int = 2                        # 手动设置

        LIVE_STATUS_0: int = 0                       # 未开播
        LIVE_STATUS_1: int = 1                       # 直播中
        LIVE_STATUS_2: int = 2                       # 轮播中

        DANMAKU_TYPE_XML: int = 0                    # xml 格式弹幕
        DANMAKU_TYPE_PROTOBUF: int = 1               # protobuf 格式弹幕

        SUBTITLE_TYPE_SRT: int = 0                   # srt 格式字幕
        SUBTITLE_TYPE_TXT: int = 1                   # txt 格式字幕
        SUBTITLE_TYPE_JSON: int = 2                  # json 格式字幕

        PLAYER_PREFERENCE_DEFAULT: int = 0           # 系统默认
        PLAYER_PREFERENCE_CUSTOM: int = 1            # 手动设置

        GPU_NVIDIA: int = 0                          # NVIDIA GPU
        GPU_AMD: int = 1                             # AMD GPU
        GPU_INTEL: int = 2                           # INTEL GPU

        CUSTOM_CDN_MODE_AUTO: int = 0                # 自动切换 CDN
        CUSTOM_CDN_MODE_MANUAL: int = 1              # 手动指定 CDN

        DOWNLOAD_STATUS_WAITING: int = 0             # 等待下载
        DOWNLOAD_STATUS_DOWNLOADING: int = 1         # 正在下载
        DOWNLOAD_STATUS_PAUSE: int = 2               # 暂停中
        DOWNLOAD_STATUS_MERGING: int = 3             # 正在合成
        DOWNLOAD_STATUS_FINISHED: int = 4            # 下载完成
        DOWNLOAD_STATUS_DOWNLOAD_FAILED: int = 5     # 下载失败
        DOWNLOAD_STATUS_MERGE_FAILED: int = 6        # 合成失败

        DOWNLOAD_STATUS_ALIVE_LIST: List[int] = [DOWNLOAD_STATUS_WAITING, DOWNLOAD_STATUS_DOWNLOADING, DOWNLOAD_STATUS_PAUSE]
        DOWNLOAD_STATUS_ALIVE_LIST_EX: List[int] = [DOWNLOAD_STATUS_WAITING, DOWNLOAD_STATUS_DOWNLOADING, DOWNLOAD_STATUS_PAUSE, DOWNLOAD_STATUS_MERGE_FAILED, DOWNLOAD_STATUS_DOWNLOAD_FAILED]

    class Temp:
        download_window_pos = None

        update_json = None

    class FFmpeg:
        path: str = ""
        available: bool = False

    class Extra:
        get_danmaku = False
        danmaku_type = 0

        get_subtitle = False
        subtitle_type = 0

        get_cover = False

    class Auth:
        img_key: str = ""
        sub_key: str = ""

        wbi_key: str = ""

class ConfigUtils:
    def __init__(self):
        pass

    def load_config(self):
        def _check():
            if not os.path.exists(Config.Download.path):
                os.makedirs(Config.Download.path)

            if not os.path.exists(Config.User.directory):
                os.makedirs(Config.User.directory)

            if not os.path.exists(Config.User.download_file_directory):
                os.makedirs(Config.User.download_file_directory)

            if not os.path.exists(Config.APP.app_config_path):
                self._write_config_json(Config.APP.app_config_path, app_config)

            if not os.path.exists(Config.User.user_config_path):
                self._write_config_json(Config.User.user_config_path, user_config)

        def _after_read():
            for node_name in ["download", "merge", "extra", "proxy", "misc"]:
                if node_name not in app_config:
                    app_config[node_name] = {}
            
            if "user" not in user_config:
                user_config["user"] = {}
        
        def _init():
            match Config.Sys.platform:
                case "windows":
                    Config.User.directory = os.path.join(os.getenv("LOCALAPPDATA"), "Bili23 Downloader")

                case "linux" | "darwin":
                    Config.User.directory = os.path.join(os.path.expanduser("~"), ".Bili23 Downloader")

            Config.User.user_config_path = os.path.join(Config.User.directory, "user.json")

            Config.User.face_path = os.path.join(Config.User.directory, "face.jpg")

            Config.User.download_file_directory = os.path.join(Config.User.directory, "download")
        
        _init()

        app_config: Dict[str, dict] = self._read_config_json(Config.APP.app_config_path)
        user_config: Dict[str, dict] = self._read_config_json(Config.User.user_config_path)

        _after_read()
        
        # download
        Config.Download.path = app_config["download"].get("path", Config.Download.path)
        Config.Download.max_download_count = app_config["download"].get("max_download_count", Config.Download.max_download_count)
        Config.Download.max_thread_count = app_config["download"].get("max_thread_count", Config.Download.max_thread_count)
        Config.Download.video_quality_id = app_config["download"].get("video_quality_id", Config.Download.video_quality_id)
        Config.Download.audio_quality_id = app_config["download"].get("audio_quality_id", Config.Download.audio_quality_id)
        Config.Download.video_codec_id = app_config["download"].get("video_codec_id", Config.Download.video_codec_id)
        Config.Download.enable_dolby = app_config["download"].get("enable_dolby", Config.Download.enable_dolby)
        Config.Download.enable_notification = app_config["download"].get("show_notification", Config.Download.enable_notification)
        Config.Download.delete_history = app_config["download"].get("delete_history", Config.Download.delete_history)
        Config.Download.add_number = app_config["download"].get("add_number", Config.Download.add_number)
        Config.Download.enable_speed_limit = app_config["download"].get("enable_speed_limit", Config.Download.enable_speed_limit)
        Config.Download.speed_limit_in_mb = app_config["download"].get("speed_limit_in_mb", Config.Download.speed_limit_in_mb)
        Config.Download.enable_custom_cdn = app_config["download"].get("enable_custom_cdn", Config.Download.enable_custom_cdn)
        Config.Download.custom_cdn = app_config["download"].get("custom_cdn", Config.Download.custom_cdn)
        Config.Download.custom_cdn_mode = app_config["download"].get("custom_cdn_mode", Config.Download.custom_cdn_mode)

        # merge
        Config.FFmpeg.path = app_config["merge"].get("ffmpeg_path", Config.FFmpeg.path)
        Config.Merge.override_file = app_config["merge"].get("override_file", Config.Merge.override_file)
        Config.Merge.m4a_to_mp3 = app_config["merge"].get("m4a_to_mp3", Config.Merge.m4a_to_mp3)
        Config.Merge.auto_clean = app_config["merge"].get("auto_clean", Config.Merge.auto_clean)

        # extra
        Config.Extra.get_danmaku = app_config["extra"].get("get_danmaku", Config.Extra.get_danmaku)
        Config.Extra.danmaku_type = app_config["extra"].get("danmaku_type", Config.Extra.danmaku_type)
        Config.Extra.get_subtitle = app_config["extra"].get("get_subtitle", Config.Extra.get_subtitle)
        Config.Extra.subtitle_type = app_config["extra"].get("subtitle_type", Config.Extra.subtitle_type)
        Config.Extra.get_cover = app_config["extra"].get("get_cover", Config.Extra.get_cover)

        # proxy
        Config.Proxy.proxy_mode = app_config["proxy"].get("proxy_mode", Config.Proxy.proxy_mode)
        Config.Proxy.proxy_ip = app_config["proxy"].get("proxy_ip", Config.Proxy.proxy_ip)
        Config.Proxy.proxy_port = app_config["proxy"].get("proxy_port", Config.Proxy.proxy_port)
        Config.Proxy.enable_auth = app_config["proxy"].get("enable_auth", Config.Proxy.enable_auth)
        Config.Proxy.auth_username = app_config["proxy"].get("auth_username", Config.Proxy.auth_username)
        Config.Proxy.auth_password = app_config["proxy"].get("auth_password", Config.Proxy.auth_password)

        # misc
        Config.Misc.episode_display_mode = app_config["misc"].get("episode_display_mode", Config.Misc.episode_display_mode)
        Config.Misc.show_episode_full_name = app_config["misc"].get("show_episode_full_name", Config.Misc.show_episode_full_name)
        Config.Misc.auto_select = app_config["misc"].get("auto_select", Config.Misc.auto_select)
        Config.Misc.player_preference = app_config["misc"].get("player_preference", Config.Misc.player_preference)
        Config.Misc.player_path = app_config["misc"].get("player_path", Config.Misc.player_path)
        Config.Misc.auto_check_update = app_config["misc"].get("auto_check_update", Config.Misc.auto_check_update)
        Config.Misc.enable_debug = app_config["misc"].get("enable_debug", Config.Misc.enable_debug)

        # user
        Config.User.login = user_config["user"].get("login", Config.User.login)
        Config.User.face_url = user_config["user"].get("face_url", Config.User.face_url)
        Config.User.username = user_config["user"].get("username", Config.User.username)
        Config.User.sessdata = user_config["user"].get("sessdata", Config.User.sessdata)

        _check()

    def update_config_kwargs(self, file_path: str, category: str, **kwargs):
        config = self._read_config_json(file_path)

        for key, value in kwargs.items():
            config[category][key] = value

        self._write_config_json(file_path, config)

    def clear_config():
        from utils.tool_v2 import UniversalTool

        UniversalTool.remove_files(os.getcwd(), ["config.json"])
        UniversalTool.remove_files(Config.User.directory, ["user.json"])

    def _read_config_json(self, file_path: str):
        try:
            with open(file_path, "r", encoding = "utf-8") as f:
                return json.loads(f.read())
        except Exception:
                return {}

    def _write_config_json(self, file_path: str, contents: dict):
        with open(file_path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False, indent = 4))

utils = ConfigUtils()
utils.load_config()