import os
import json
import platform
from typing import Dict

from utils.common.enums import Platform
from utils.common.map import cdn_map

class Config:
    class Sys:
        platform: str = platform.system().lower()
        dark_mode: bool = False

    class APP:
        name: str = "Bili23 Downloader"

        version: str = "1.61.0"
        version_code: int = 1611

        # 断点续传文件最低支持版本号
        _task_file_min_version_code: int = 1600

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
        login_expires: int = 0

        SESSDATA: str = ""
        DedeUserID: str = ""
        DedeUserID__ckMd5: str = ""
        bili_jct = ""

    class Misc:
        episode_display_mode: int = 2

        show_episode_full_name: bool = True
        auto_select: bool = False
        enable_debug: bool = False
        auto_check_update: bool = True
        show_user_info: bool = True

        player_preference: int = 0
        player_path: str = ""

    class Download:
        path: str = os.path.join(os.getcwd(), "download")
        
        video_quality_id: int = 200
        audio_quality_id: int = 30300
        video_codec_id: int = 7

        max_thread_count: int = 2
        max_download_count: int = 1

        enable_notification: bool = False
        delete_history: bool = False
        add_number: bool = True

        enable_speed_limit: bool = False
        speed_mbps: int = 10

        auto_popup_option_dialog: bool = True
    
    class Merge:
        override_option: int = 1
        m4a_to_mp3: bool = True

    class Temp:
        update_json: dict = None

        change_log: str = None

        need_login: bool = False

    class FFmpeg:
        path: str = ""
        available: bool = False

    class Extra:
        download_danmaku_file = False
        danmaku_file_type = 0

        download_subtitle_file = False
        subtitle_file_type = 0

        download_cover_file = False

    class Auth:
        img_key: str = ""
        sub_key: str = ""

        buvid3: str = ""
        buvid4: str = ""
        buvid_fp: str = ""
        b_nut: str = ""
        bili_ticket: str = ""
        bili_ticket_expires: int = 0
        uuid: str = ""
        b_lsid: str = ""

    class Advanced:
        enable_custom_cdn: bool = True
        custom_cdn_mode: int = 0
        custom_cdn: str = "upos-sz-mirror08c.bilivideo.com"
        custom_cdn_list: list = []

        file_name_template = "{number_with_zero} - {title}"
        date_format = "%Y-%m-%d"
        time_format = "%H-%M-%S"
        auto_adjust_field = True

        retry_when_download_error: bool = True
        download_error_retry_count: int = 3
        retry_when_download_suspend: bool = True
        download_suspend_retry_interval: int = 3
        always_use_https_protocol: bool = True

class ConfigUtils:
    def __init__(self):
        pass

    def load_config(self):
        def _after_load():
            _check()

            for index, cdn in enumerate(Config.Advanced.custom_cdn_list):
                cdn_map[index + len(cdn_map)] = {
                    "cdn": cdn,
                    "provider": "自定义",
                    "order": index + len(cdn_map) + 1
                }

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
            for node_name in ["download", "advanced","merge", "extra", "proxy", "misc"]:
                if node_name not in app_config:
                    app_config[node_name] = {}
            
            if "user" not in user_config:
                user_config["user"] = {}
            
            if "cookie_params" not in user_config:
                user_config["cookie_params"] = {}
        
        def _init():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    Config.User.directory = os.path.join(os.getenv("LOCALAPPDATA"), "Bili23 Downloader")

                case Platform.Linux | Platform.macOS:
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
        Config.Download.enable_notification = app_config["download"].get("show_notification", Config.Download.enable_notification)
        Config.Download.delete_history = app_config["download"].get("delete_history", Config.Download.delete_history)
        Config.Download.add_number = app_config["download"].get("add_number", Config.Download.add_number)
        Config.Download.enable_speed_limit = app_config["download"].get("enable_speed_limit", Config.Download.enable_speed_limit)
        Config.Download.speed_mbps = app_config["download"].get("speed_mbps", Config.Download.speed_mbps)
        Config.Download.auto_popup_option_dialog = app_config["download"].get("auto_popup_option_dialog", Config.Download.auto_popup_option_dialog)

        # advanced
        Config.Advanced.enable_custom_cdn = app_config["advanced"].get("enable_custom_cdn", Config.Advanced.enable_custom_cdn)
        Config.Advanced.custom_cdn = app_config["advanced"].get("custom_cdn", Config.Advanced.custom_cdn)
        Config.Advanced.custom_cdn_mode = app_config["advanced"].get("custom_cdn_mode", Config.Advanced.custom_cdn_mode)
        Config.Advanced.custom_cdn_list = app_config["advanced"].get("custom_cdn_list", Config.Advanced.custom_cdn_list)
        Config.Advanced.file_name_template = app_config["advanced"].get("file_name_template", Config.Advanced.file_name_template)
        Config.Advanced.date_format = app_config["advanced"].get("date_format", Config.Advanced.date_format)
        Config.Advanced.time_format = app_config["advanced"].get("time_format", Config.Advanced.time_format)
        Config.Advanced.auto_adjust_field = app_config["advanced"].get("auto_adjust_field", Config.Advanced.auto_adjust_field)
        Config.Advanced.retry_when_download_error = app_config["advanced"].get("retry_when_download_error", Config.Advanced.retry_when_download_error)
        Config.Advanced.download_error_retry_count = app_config["advanced"].get("download_error_retry_count", Config.Advanced.download_error_retry_count)
        Config.Advanced.retry_when_download_suspend = app_config["advanced"].get("retry_when_download_suspend", Config.Advanced.retry_when_download_suspend)
        Config.Advanced.download_suspend_retry_interval = app_config["advanced"].get("download_suspend_retry_interval", Config.Advanced.download_suspend_retry_interval)
        Config.Advanced.always_use_https_protocol = app_config["advanced"].get("always_use_http_protocol", Config.Advanced.always_use_https_protocol)

        # merge
        Config.FFmpeg.path = app_config["merge"].get("ffmpeg_path", Config.FFmpeg.path)
        Config.Merge.override_option = app_config["merge"].get("override_option", Config.Merge.override_option)
        Config.Merge.m4a_to_mp3 = app_config["merge"].get("m4a_to_mp3", Config.Merge.m4a_to_mp3)

        # extra
        Config.Extra.download_danmaku_file = app_config["extra"].get("download_danmaku_file", Config.Extra.download_danmaku_file)
        Config.Extra.danmaku_file_type = app_config["extra"].get("danmaku_file_type", Config.Extra.danmaku_file_type)
        Config.Extra.download_subtitle_file = app_config["extra"].get("download_subtitle_file", Config.Extra.download_subtitle_file)
        Config.Extra.subtitle_file_type = app_config["extra"].get("subtitle_file_type", Config.Extra.subtitle_file_type)
        Config.Extra.download_cover_file = app_config["extra"].get("download_cover_file", Config.Extra.download_cover_file)

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
        Config.Misc.show_user_info = app_config["misc"].get("show_user_info", Config.Misc.show_user_info)
        Config.Misc.auto_check_update = app_config["misc"].get("auto_check_update", Config.Misc.auto_check_update)
        Config.Misc.enable_debug = app_config["misc"].get("enable_debug", Config.Misc.enable_debug)

        # user
        Config.User.login = user_config["user"].get("login", Config.User.login)
        Config.User.face_url = user_config["user"].get("face_url", Config.User.face_url)
        Config.User.username = user_config["user"].get("username", Config.User.username)
        Config.User.login_expires = user_config["user"].get("login_expires", Config.User.login_expires)
        Config.User.SESSDATA = user_config["user"].get("SESSDATA", Config.User.SESSDATA)
        Config.User.DedeUserID = user_config["user"].get("DedeUserID", Config.User.DedeUserID)
        Config.User.DedeUserID__ckMd5 = user_config["user"].get("DedeUserID__ckMd5", Config.User.DedeUserID__ckMd5)
        Config.User.bili_jct = user_config["user"].get("bili_jct", Config.User.bili_jct)

        # auth
        Config.Auth.buvid3 = user_config["cookie_params"].get("buvid3", Config.Auth.buvid3)
        Config.Auth.buvid4 = user_config["cookie_params"].get("buvid4", Config.Auth.buvid4)
        Config.Auth.buvid_fp = user_config["cookie_params"].get("buvid_fp", Config.Auth.buvid_fp)
        Config.Auth.b_nut = user_config["cookie_params"].get("b_nut", Config.Auth.b_nut)
        Config.Auth.bili_ticket = user_config["cookie_params"].get("bili_ticket", Config.Auth.bili_ticket)
        Config.Auth.bili_ticket_expires = user_config["cookie_params"].get("bili_ticket_expires", Config.Auth.bili_ticket_expires)
        Config.Auth.uuid = user_config["cookie_params"].get("uuid", Config.Auth.uuid)

        _after_load()

    def update_config_kwargs(self, file_path: str, category: str, **kwargs):
        config = self._read_config_json(file_path)

        if category not in config:
            config[category] = {}

        for key, value in kwargs.items():
            config[category][key] = value

        self._write_config_json(file_path, config)

    @staticmethod
    def clear_config():
        from utils.tool_v2 import UniversalTool

        UniversalTool.remove_files(os.getcwd(), ["config.json"])

    def _read_config_json(self, file_path: str):
        try:
            with open(file_path, "r", encoding = "utf-8") as f:
                return json.loads(f.read())
        except Exception:
                return {}

    def _write_config_json(self, file_path: str, contents: dict):
        with open(file_path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False, indent = 4))

config_utils = ConfigUtils()
config_utils.load_config()