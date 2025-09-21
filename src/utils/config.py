import os
import json
import platform
from typing import Dict, List

from utils.common.io.file import File
from utils.common.io.directory import Directory
from utils.common.enums import Platform

app_config_group = {
    "Basic": [
        "language",
        "listen_clipboard",
        "exit_option",
        "auto_popup_option_dialog",
        "auto_show_download_window",
        "remember_window_status",
        "always_on_top",
        "download_danmaku_file",
        "danmaku_file_type",
        "download_subtitle_file",
        "subtitle_file_type",
        "subtitle_lan_option",
        "subtitle_lan_custom_type",
        "download_cover_file",
        "cover_file_type",
        "download_metadata_file",
        "metadata_file_type",
        "window_pos",
        "window_size",
        "window_maximized",
        "is_new_user",
        "no_paid_check",
        "ass_style"
    ],
    "Download": [
        "path",
        "file_name_template_list",
        "strict_naming",
        "max_download_count",
        "max_thread_count",
        "video_quality_priority",
        "audio_quality_priority",
        "video_codec_priority",
        "enable_notification",
        "delete_history",
        "enable_speed_limit",
        "speed_mbps",
        "number_type"
    ],
    "Advanced": [
        "enable_switch_cdn",
        "cdn_list",
        "retry_when_download_error",
        "download_error_retry_count",
        "retry_when_download_suspend",
        "download_suspend_retry_interval",
        "always_use_https_protocol",
        "enable_ssl_verify",
        "user_agent",
        "webpage_option",
        "websocket_port"
    ],
    "Merge": [
        "ffmpeg_path",
        "ffmpeg_check_available_when_launch",
        "override_option",
        "keep_original_files",
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
        "auto_check_episode_item",
        "show_user_info",
        "enable_debug",
        "ignore_version"
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
        "uuid",
        "refresh_token"
    ]
}

class Config:
    app_config = None
    user_config = None

    class Sys:
        platform: str = platform.system().lower()
        dark_mode: bool = False
        dpi_scale_factor: float = 1

        default_font: str = ""

    class APP:
        name: str = "Bili23 Downloader"
        id: str = "B096F0C1-D105-4EF9-86E1-5E87DA884EA4"

        version: str = "1.70.0"
        version_code: int = 170000

        task_file_min_version_code: int = 170000
        live_file_min_version_code: int = 165000
        app_config_file_min_version_code: int = 170000
        user_config_file_min_version_code: int = 166000

        app_config_path: str = ""

    class Basic:
        language: str = "zh_CN"

        listen_clipboard: bool = False
        exit_option: int = 3
        auto_popup_option_dialog: bool = True
        auto_show_download_window: bool = True
        remember_window_status: bool = False
        always_on_top: bool = False

        download_danmaku_file: bool = False
        danmaku_file_type: int = 3

        download_subtitle_file: bool = False
        subtitle_file_type: int = 4
        subtitle_lan_option: int = 0
        subtitle_lan_custom_type: list = []

        download_cover_file: bool = False
        cover_file_type: int = 0

        download_metadata_file: bool = False
        metadata_file_type: int = 0
        scrape_option: dict = {
            "video": {
                "nfo_file_type": 0,
            },
            "episode": {
                "nfo_file_type": 0,
                "download_tvshow_nfo": True,
                "download_season_nfo": True,
                "download_episode_nfo": True
            },
            "movie": {
                "nfo_file_type": 0,
                "download_movie_nfo": True,
                "download_episode_nfo": True
            },
            "lesson": {
                "nfo_file_type": 0,
            }
        }

        ass_style: Dict[str, Dict] = {
            "danmaku": {
                "font_name": "黑体",
                "font_size": 40,
                "bold": 0,
                "italic": 0,
                "underline": 0,
                "strikeout": 0,
                "border": 1.0,
                "shadow": 0.0,
                "non_alpha": False,
                "scale_x": 100,
                "scale_y": 100,
                "angle": 0,
                "spacing": 0.0,
                "subtitle_obstruct": False,
                "area": 5,
                "alpha": 80,
                "speed": 3,
                "density": 1
            },
            "subtitle": {
                "font_name": "黑体",
                "font_size": 48,
                "bold": 0,
                "italic": 0,
                "underline": 0,
                "strikeout": 0,
                "border": 2.0,
                "shadow": 1.0,
                "non_alpha": False,
                "primary_color": "&H00FFFFFF&",
                "secondary_color": "&H00FFFFFF&",
                "border_color": "&H00000000&",
                "shadow_color": "&H00000000&",
                "scale_x": 100,
                "scale_y": 100,
                "angle": 0,
                "spacing": 0.0,
                "marginL": 10,
                "marginR": 10,
                "marginV": 20,
                "alignment": 2
            }
        }

        window_pos: list = []
        window_size: list = []
        window_maximized: bool = False

        is_new_user: bool = True
        no_paid_check: bool = False

    class Proxy:
        proxy_mode: int = 0
        enable_auth: bool = False

        proxy_ip: str = ""
        proxy_port: int = 1
        auth_username: str = ""
        auth_password: str = ""
    
    class User:
        directory: str = ""
        download_file_directory: str = ""
        live_file_directory: str = ""
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
        episode_display_mode: int = 3

        show_episode_full_name: bool = False
        auto_check_episode_item: bool = False
        enable_debug: bool = False
        show_user_info: bool = True

        ignore_version: int = 0

    class Download:
        path: str = os.path.join(os.getcwd(), "download")
        file_name_template_list: list = [
            {
                "template": {
                    "0": "{zero_padding_number} - {title}"
                },
                "type": 1
            },
            {
                "template": {
                    "0": "{part_title}/P{page} - {title}"
                },
                "type": 2
            },
            {
                "template": {
                    "0": "{collection_title}/{section_title}/{part_title}/{zero_padding_number} - {title}"
                },
                "type": 3
            },
            {
                "template": {
                    "0": "{interact_title}/{title}"
                },
                "type": 4
            },
            {
                "template": {
                    "0": "{series_title}/{section_title}/{title}",
                    "1": "{series_title}/{section_title}/{title}"
                },
                "type": 5
            },
            {
                "template": {
                    "0": "{series_title_original}/{section_title_ex}/{episode_tag} - {title}",
                    "1": "{series_title_original}/Extra/{section_title}/{title}"
                },
                "type": 6
            },
            {
                "template": {
                    "0": "{series_title}/{section_title}/{title}"
                },
                "type": 7
            },
            {
                "template": {
                    "0": "{title}"
                },
                "type": 8
            },
            {
                "template": {
                    "0": "{title}"
                },
                "type": 9
            }
        ]
        strict_naming: bool = False

        video_quality_priority: list = [
            127,
            126,
            125,
            120,
            116,
            112,
            100,
            80,
            64,
            32,
            16
        ]
        audio_quality_priority: list = [
            30251,
            30250,
            30280,
            30232,
            30216
        ]
        video_codec_priority: list = [
            13,
            12,
            7
        ]
        
        video_quality_id: int = 200
        audio_quality_id: int = 30300
        video_codec_id: int = 20

        max_thread_count: int = 8
        max_download_count: int = 1

        enable_notification: bool = False
        delete_history: bool = False
        number_type: int = 1

        enable_speed_limit: bool = False
        speed_mbps: int = 10

        stream_download_option: list = ["video", "audio"]
        ffmpeg_merge: bool = True
    
    class Merge:
        ffmpeg_path: str = ""
        ffmpeg_check_available_when_launch: bool = True

        override_option: int = 1
        keep_original_files: bool = False

    class Temp:
        scrape_option: dict = {}

        video_quality_priority: list = []
        audio_quality_priority: list = []
        video_codec_priority: list = []

        cdn_list: list = []

        user_agent: str = ""

        file_name_template_list: list = []
        strict_naming: bool = False

        ass_style: Dict[str, Dict] = {}

        video_width: int = 1920
        video_height: int = 1080
        remember_resolution_settings: bool = False

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

        refresh_token: str = ""

    class Advanced:
        enable_switch_cdn: bool = True
        cdn_list: list = [
            "upos-sz-estgoss.bilivideo.com",
            "upos-sz-mirrorali02.bilivideo.com",
            "upos-sz-mirror08c.bilivideo.com",
            "upos-sz-mirrorcoso1.bilivideo.com",
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

        retry_when_download_error: bool = True
        download_error_retry_count: int = 3
        retry_when_download_suspend: bool = True
        download_suspend_retry_interval: int = 3
        always_use_https_protocol: bool = True
        enable_ssl_verify: bool = True

        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"

        webpage_option: int = 0
        websocket_port: int = 8765

    class ConfigBase:
        def __init__(self):
            self.config: Dict[str, dict] = {}

            self.file_path = ""
            self.min_version = 0

            self.config_group: Dict[str, List[str]] = {}

        def init_config(self):
            self.read()
            self.check()

            self.make()

            self.read_group()

        def read(self):
            try:
                with open(self.file_path, "r", encoding = "utf-8") as f:
                    self.config = json.loads(f.read())

            except Exception:
                    self.config = {}

        def read_group(self):
            for section, name_list in self.config_group.items():
                for name in name_list:
                    setattr(getattr(Config, section), name, self.config.get(section.lower()).get(name, getattr(getattr(Config, section), name)))

        def save(self):
            for section, name_list in self.config_group.items():
                for name in name_list:
                    self.config[section.lower()][name] = getattr(getattr(Config, section), name)

            with open(self.file_path, "w", encoding = "utf-8") as f:
                f.write(json.dumps(self.config, ensure_ascii = False, indent = 4))
        
        def make(self):
            if not os.path.exists(self.file_path):
                self.save()

        def check(self):
            if self.check_version():
                self.reset()

                File.remove_file(self.file_path)

        def check_version(self):
            min_version = self.config.get("header", {"min_version": 0}).get("min_version", 0)

            if min_version < self.min_version:
                return True
            
    class APPConfig(ConfigBase):
        def __init__(self):
            Config.ConfigBase.__init__(self)

            self.file_path = Config.APP.app_config_path
            self.min_version = Config.APP.app_config_file_min_version_code

            self.config_group = app_config_group

            self.init_config()

        def reset(self):
            self.config = {
                "header": {
                    "min_version": self.min_version
                },
                "basic": {},
                "download": {},
                "advanced": {},
                "merge": {},
                "proxy": {},
                "misc": {}
            }
    
    class UserConfig(ConfigBase):
        def __init__(self):
            Config.ConfigBase.__init__(self)

            self.file_path = Config.User.user_config_path
            self.min_version = Config.APP.user_config_file_min_version_code

            self.config_group = user_config_group

            self.init_config()

        def reset(self):
            self.config = {
                "header": {
                    "min_version": self.min_version
                },
                "user": {},
                "auth": {}
            }
            
    @classmethod
    def load_config(cls):
        try:
            cls.init_path()
            
            Directory.create_directories([Config.User.directory, Config.User.download_file_directory, Config.User.live_file_directory])

            cls.app_config = Config.APPConfig()
            cls.user_config = Config.UserConfig()

        except Exception:
            cls.on_error()

    @staticmethod
    def init_path():
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                Config.User.directory = os.path.join(os.environ["APPDATA"], "Bili23 Downloader")

            case Platform.Linux:
                Config.User.directory = os.path.join(os.path.expanduser("~"), ".config", "Bili23 Downloader")

            case Platform.macOS:
                Config.User.directory = os.path.join(os.path.expanduser("~/Library/Application Support"), "Bili23 Downloader")

        Config.APP.app_config_path = os.path.join(Config.User.directory, "config.json")
        Config.User.user_config_path = os.path.join(Config.User.directory, "user.json")
        Config.User.download_file_directory = os.path.join(Config.User.directory, "download")
        Config.User.live_file_directory = os.path.join(Config.User.directory, "live")

    @classmethod
    def save_app_config(cls):
        try:
            cls.app_config.save()
        
        except Exception:
            cls.on_error()

    @classmethod
    def save_user_config(cls):
        try:
            cls.user_config.save()

        except Exception:
            cls.on_error()

    @staticmethod
    def on_error():
        import wx
        import sys
        import traceback

        wx.LogError(f"读取\保存配置文件时出错\n{traceback.format_exc()}")

        sys.exit()

Config.load_config()