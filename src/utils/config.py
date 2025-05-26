import os
import json
import platform
from typing import Dict

from utils.common.enums import Platform

app_config_group = {
    "Basic": [
        "listen_clipboard",
        "exit_option",
        "auto_popup_option_dialog",
        "auto_show_download_window",
        "remember_window_status",
        "download_danmaku_file",
        "danmaku_file_type",
        "download_subtitle_file",
        "subtitle_file_type",
        "subtitle_lan_option",
        "subtitle_lan_custom_type",
        "download_cover_file",
        "window_pos",
        "window_size",
        "window_maximized",
        "show_exit_dialog"
    ],
    "Download": [
        "path",
        "max_download_count",
        "max_thread_count",
        "video_quality_id",
        "audio_quality_id",
        "video_codec_id",
        "enable_notification",
        "delete_history",
        "auto_add_number",
        "enable_speed_limit",
        "speed_mbps"
    ],
    "Advanced": [
        "enable_switch_cdn",
        "cdn_list",
        "file_name_template",
        "datetime_format",
        "auto_adjust_field",
        "enable_download_sort",
        "sort_by_up",
        "sort_by_collection",
        "sort_by_series",
        "retry_when_download_error",
        "download_error_retry_count",
        "retry_when_download_suspend",
        "download_suspend_retry_interval",
        "always_use_https_protocol",
        "check_md5"
    ],
    "Merge": [
        "ffmpeg_path",
        "ffmpeg_check_available_when_lauch",
        "keep_files_option",
        "override_option",
        "m4a_to_mp3"
    ],
    "Proxy": [
        "proxy_mode",
        "proxy_ip",
        "proxy_port",
        "enable_auth",
        "auth_username",
        "auth_password"
    ],
    "Misc": [
        "episode_display_mode",
        "show_episode_full_name",
        "auto_select",
        "player_preference",
        "player_path",
        "show_user_info",
        "check_update_when_lauch",
        "enable_debug"
    ],
}

user_config_group = {
    "User": [
        "login",
        "face_url",
        "username",
        "login_expires",
        "SESSDATA",
        "DedeUserID",
        "DedeUserID__ckMd5",
        "bili_jct"
    ],
    "Auth": [
        "buvid3",
        "buvid4",
        "buvid_fp",
        "b_nut",
        "bili_ticket",
        "bili_ticket_expires",
        "uuid"
    ]
}

class Config:
    class Sys:
        platform: str = platform.system().lower()
        dark_mode: bool = False
        dpi_scale_factor: float = 1

    class APP:
        name: str = "Bili23 Downloader"

        version: str = "1.63.0"
        version_code: int = 1630

        # 断点续传文件最低支持版本号
        task_file_min_version_code: int = 1630
        config_file_min_version_code: int = 1620

        app_config_path: str = os.path.join(os.getcwd(), "config.json")

    class Basic:
        listen_clipboard: bool = True
        exit_option: int = 0
        auto_popup_option_dialog: bool = True
        auto_show_download_window: bool = True
        remember_window_status: bool = False

        download_danmaku_file: bool = False
        danmaku_file_type: int = 0
        download_subtitle_file: bool = False
        subtitle_file_type: int = 0
        subtitle_lan_option: int = 0
        subtitle_lan_custom_type: list = []
        download_cover_file: bool = False

        window_pos: list = []
        window_size: list = []
        window_maximized: bool = False

        show_exit_dialog: bool = True

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
        face_type: str = ""

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
        check_update_when_lauch: bool = True
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
        auto_add_number: bool = True
        number_type: int = 1

        enable_speed_limit: bool = False
        speed_mbps: int = 10

        stream_download_option: list = ["video", "audio"]
    
    class Merge:
        ffmpeg_path: str = ""
        ffmpeg_available: bool = False
        ffmpeg_check_available_when_lauch: bool = True

        keep_files_option: int = 0
        override_option: int = 1
        m4a_to_mp3: bool = True

    class Temp:
        update_json: dict = None
        changelog: str = None

        need_login: bool = False

        cdn_list: list = []

        file_name_template: str = ""
        datetime_format: str = ""
        auto_adjust_field: bool = False

        enable_download_sort: bool = False
        sort_by_up: bool = False
        sort_by_collection: bool = False
        sort_by_series: bool = False

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
        enable_switch_cdn: bool = True
        cdn_list: list = [
            "upos-sz-estgoss.bilivideo.com",
            "upos-sz-mirror08c.bilivideo.com",
            "upos-sz-mirrorcoso1.bilivideo.com",
            "upos-sz-mirrorali02.bilivideo.com",
            "upos-sz-mirrorhw.bilivideo.com",
            "upos-sz-mirror08h.bilivideo.com",
            "upos-sz-mirrorcos.bilivideo.com",
            "upos-sz-mirrorcosb.bilivideo.com",
            "upos-sz-mirrorali.bilivideo.com",
            "upos-sz-mirroralib.bilivideo.com",
            "upos-sz-mirroraliov.bilivideo.com",
            "upos-sz-mirrorcosov.bilivideo.com",
            "upos-hz-mirrorakam.akamaized.net",
            "upos-sz-mirrorcf1ov.bilivideo.com"
        ]

        file_name_template: str = "{number_with_zero} - {title}"
        datetime_format: str = "%Y-%m-%d %H-%M-%S"
        auto_adjust_field: bool = True

        enable_download_sort: bool = False
        sort_by_up: bool = False
        sort_by_collection: bool = False
        sort_by_series: bool = False

        retry_when_download_error: bool = True
        download_error_retry_count: int = 3
        retry_when_download_suspend: bool = True
        download_suspend_retry_interval: int = 3
        always_use_https_protocol: bool = True
        check_md5: bool = True

        ua_option: int = 0
        custom_ua: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"

    @classmethod
    def load_config(cls):
        def after_load_config():
            def create_folder(path_list: list):
                for path in path_list:
                    if not os.path.exists(path):
                        os.makedirs(path)
            
            def create_config(config_list: list):
                for entry in config_list:
                    if not os.path.exists(entry["path"]):
                        cls.write_config_json(entry["path"], entry["config"])

                        cls.save_config_group(Config, entry["config_group"], entry["path"])

            def get_user_face():
                _, file_ext = os.path.splitext(Config.User.face_url)

                Config.User.face_type = file_ext[1:]
                
                Config.User.face_path = os.path.join(Config.User.directory, f"face.{file_ext[1:]}")

            create_folder([Config.Download.path, Config.User.directory, Config.User.download_file_directory])

            create_config([{"path": Config.APP.app_config_path, "config": app_config, "config_group": app_config_group}, {"path": Config.User.user_config_path, "config": user_config, "config_group": user_config_group}])

            get_user_face()

        def check_config():
            def check_config_version(config: Dict[str, dict], file_path: str):
                min_version = config.get("header", {"min_version": 0}).get("min_version", 0)
                
                if min_version < Config.APP.config_file_min_version_code:
                    cls.remove_config_file(file_path)

                    config.clear()

            def check_config_node_name(config: Dict[str, dict], node_name_list: list):
                for node_name in node_name_list:
                    if node_name not in config:
                        config[node_name] = {}

                        if node_name == "header":
                            config[node_name]["min_version"] = Config.APP.config_file_min_version_code
                            config[node_name]["platform"] = Config.Sys.platform

            check_config_version(app_config, Config.APP.app_config_path)
            check_config_version(user_config, Config.User.user_config_path)

            check_config_node_name(app_config, ["header", "basic", "download", "advanced", "merge", "extra", "proxy", "misc"])
            check_config_node_name(user_config, ["header", "user", "auth"])
        
        def get_path():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    Config.User.directory = os.path.join(os.getenv("LOCALAPPDATA"), "Bili23 Downloader")

                case Platform.Linux | Platform.macOS:
                    Config.User.directory = os.path.join(os.path.expanduser("~"), ".Bili23 Downloader")

            Config.User.user_config_path = os.path.join(Config.User.directory, "user.json")
            Config.User.download_file_directory = os.path.join(Config.User.directory, "download")
        
        get_path()

        app_config: Dict[str, dict] = cls.read_config_json(Config.APP.app_config_path)
        user_config: Dict[str, dict] = cls.read_config_json(Config.User.user_config_path)

        check_config()

        cls.read_config_group(Config, app_config, app_config_group)
        cls.read_config_group(Config, user_config, user_config_group)

        after_load_config()

    @staticmethod
    def read_config_group(object, config: Dict[str, dict], config_group: Dict[str, list]):
        for section, name_list in config_group.items():
            for name in name_list:
                setattr(getattr(object, section), name, config.get(section.lower()).get(name, getattr(getattr(object, section), name)))

    @classmethod
    def save_config_group(cls, object, config_group: Dict[str, list], config_file_path: str):
        config = cls.read_config_json(config_file_path)

        for section, name_list in config_group.items():
            for name in name_list:
                config[section.lower()][name] = getattr(getattr(object, section), name)

        cls.write_config_json(config_file_path, config)

    @staticmethod
    def remove_config_file(file_path: str):
        from utils.tool_v2 import UniversalTool

        UniversalTool.remove_files([file_path])

    @staticmethod
    def read_config_json(file_path: str):
        try:
            with open(file_path, "r", encoding = "utf-8") as f:
                return json.loads(f.read())

        except Exception:
                return {}

    @staticmethod
    def write_config_json(file_path: str, contents: dict):
        with open(file_path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False, indent = 4))

Config.load_config()