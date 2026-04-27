from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QPixmap

from qfluentwidgets import (
    QConfig, RangeConfigItem, RangeValidator, OptionsValidator, OptionsConfigItem, BoolValidator,
    ConfigItem, EnumSerializer, Theme, qconfig
)

from .serializer import LanguageSerializer, ScalingSerializer
from .enum import (
    Language, WhenClose, DanmakuType, SubtitleType, CoverType, MetadataType, ProxyType, FFmpegSource, NumberingType,
    Scaling, FileConflictResolution, VideoContainer
)

from pathlib import Path
import logging
import sys

logger = logging.getLogger(__name__)

def isWin11():
    return sys.platform == "win32" and sys.getwindowsversion().build >= 22000

class DefaultValue:
    parse_list_column = [
        {
            "attr_key": "number",
            "width": 160,
            "show": True
        },
        {
            "attr_key": "title",
            "width": 350,
            "show": True
        },
        {
            "attr_key": "badge",
            "width": 90,
            "show": True
        },
        {
            "attr_key": "duration",
            "width": 90,
            "show": True
        },
        {
            "attr_key": "dyn_time",
            "width": 130,
            "show": True
        }
    ]

    video_quality_priority = [
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

    audio_quality_priority = [
        30251,
        30250,
        30280,
        30232,
        30216
    ]
    
    video_codec_priority = [
        7,
        12,
        13
    ]

    danmaku_style = {
        "font": {
            "name": "黑体",
            "size": 36,
            "bold": False,
            "italic": False,
            "underline": False,
            "strike": False
        },
        "border": {
            "border": 1.0,
            "shadow": 0,
        },
        "advanced": {
            "display_area": 60,
            "opacity": 80,
            "scroll_duration": 10,
            "static_duration": 5,
            "minimum_gap": 100
        },
        "resolution": {
            "width": 1280,
            "height": 720
        }
    }
    
    subtitle_language = {
        "download_specified": False,
        "specified_language": []
    }

    subtitle_style = {
        "font": {
            "name": "黑体",
            "size": 36,
            "bold": False,
            "italic": False,
            "underline": False,
            "strike": False
        },
        "border": {
            "border": 1.0,
            "shadow": 0.0,
        },
        "color": {
            "primary": "&H00FFFFFF",
            "secondary": "&H000000FF",
            "border": "H00000000",
            "shadow": "H00000000"
        },
        "margin": {
            "left": 10,
            "right": 10,
            "vertical": 20
        },
        "resolution": {
            "width": 1280,
            "height": 720
        },
        "alignment": 2,

    }

    naming_rule_list = [
        {
            "id": "a024c20c-5826-4e65-a1f5-802e3e2dbe4f",
            "name": "DEFAULT_FOR_NORMAL",
            "type": 11,
            "rule": "{leaf_title}",
            "default": True
        },
        {
            "id": "2d98a265-e8e1-4b2a-8133-76bbc65c90fe",
            "name": "DEFAULT_FOR_PART",
            "type": 12,
            "rule": "{parent_title}/P{p}-{leaf_title}",
            "default": True
        },
        {
            "id": "307906bd-86a2-4b6b-bd75-152a8c3e280b",
            "name": "DEFAULT_FOR_COLLECTION",
            "type": 13,
            "rule": "{collection_title}/{section_title}/{parent_title}/{leaf_title}",
            "default": True
        },
        {
            "id": "b1d4e8e3-ca17-4b41-87cf-cda45254701e",
            "name": "DEFAULT_FOR_BANGUMI",
            "type": 20,
            "rule": "{season_title}/{episode_title}",
            "default": True
        },
        {
            "id": "d582ec37-d8c2-44cf-bbd7-b709ea5c2042",
            "name": "DEFAULT_FOR_CHEESE",
            "type": 30,
            "rule": "{series_title}/{episode_title}",
            "default": True
        }
    ]

    cdn_server_list = [
        {
            "host": "upos-sz-mirror08c.bilivideo.com",
            "provider": "HUAWEI"
        },
        {
            "host": "upos-sz-mirrorhw.bilivideo.com",
            "provider": "HUAWEI"
        },
        {
            "host": "upos-sz-mirrorcos.bilivideo.com",
            "provider": "TENCENT"
        },
        {
            "host": "upos-sz-mirrorcosb.bilivideo.com",
            "provider": "TENCENT"
        },
        {
            "host": "upos-sz-mirrorali.bilivideo.com",
            "provider": "ALIYUN"
        },
        {
            "host": "upos-sz-mirroralib.bilivideo.com",
            "provider": "ALIYUN"
        }
    ]

class APPConfig(QConfig):
    # APP
    app_name = "Bili23 Downloader"
    app_version = "2.00.2"
    app_comparable_version = "2.00.2"

    # Interface
    language = OptionsConfigItem("Interface", "language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart = True)
    display_scaling = OptionsConfigItem("Interface", "display_scaling", Scaling.AUTO, OptionsValidator(Scaling), ScalingSerializer(), restart = True)
    mica_effect = ConfigItem("Interface", "mica_effect", False, BoolValidator())

    # Behavior
    auto_check_all = ConfigItem("Behavior", "auto_check_all", False, BoolValidator())
    parse_list_column = ConfigItem("Behavior", "parse_list_column", DefaultValue.parse_list_column)

    silent_start = ConfigItem("Behavior", "silent_start", False, BoolValidator())
    stay_on_top = ConfigItem("Behavior", "stay_on_top", False, BoolValidator())
    monitor_clipboard = ConfigItem("Behavior", "monitor_clipboard", False, BoolValidator())
    parse_history = ConfigItem("Behavior", "parse_history", True, BoolValidator())
    show_download_options_dialog = ConfigItem("Behavior", "show_download_options_dialog", True, BoolValidator())
    when_close_window = OptionsConfigItem("Behavior", "when_close_window", WhenClose.ALWAYS_ASK, OptionsValidator(WhenClose), EnumSerializer(WhenClose))
    file_conflict_resolution = OptionsConfigItem("Behavior", "file_conflict_resolution", FileConflictResolution.AUTO_RENAME, OptionsValidator(FileConflictResolution), EnumSerializer(FileConflictResolution))

    # Download
    download_path = ConfigItem("Download", "download_path", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation))
    download_thread = RangeConfigItem("Download", "download_thread", 4, RangeValidator(1, 10))
    download_parallel = RangeConfigItem("Download", "download_parallel", 1, RangeValidator(1, 10))
    speed_limit_enabled = ConfigItem("Download", "speed_limit_enabled", False, BoolValidator())
    speed_limit_rate = ConfigItem("Download", "speed_limit_rate", 10.0)

    show_notification = ConfigItem("Download", "show_notification", False, BoolValidator())

    video_quality_priority = ConfigItem("Download", "video_quality_priority", DefaultValue.video_quality_priority)
    audio_quality_priority = ConfigItem("Download", "audio_quality_priority", DefaultValue.audio_quality_priority)
    video_codec_priority = ConfigItem("Download", "video_codec_priority", DefaultValue.video_codec_priority)

    video_container = OptionsConfigItem("Download", "video_container", VideoContainer.MP4, OptionsValidator(VideoContainer), EnumSerializer(VideoContainer))
    m4a_to_mp3 = ConfigItem("Download", "m4a_to_mp3", False)

    # Additional
    download_danmaku = ConfigItem("Additional", "download_danmaku", False, BoolValidator())
    danmaku_type = OptionsConfigItem("Additional", "danmaku_type", DanmakuType.ASS, OptionsValidator(DanmakuType), EnumSerializer(DanmakuType))
    danmaku_style = ConfigItem("Additional", "danmaku_style", DefaultValue.danmaku_style)

    download_subtitle = ConfigItem("Additional", "download_subtitle", False, BoolValidator())
    subtitle_type = OptionsConfigItem("Additional", "subtitle_type", SubtitleType.ASS, OptionsValidator(SubtitleType), EnumSerializer(SubtitleType))
    subtitle_language = ConfigItem("Additional", "subtitle_language", DefaultValue.subtitle_language)
    subtitle_style = ConfigItem("Additional", "subtitle_style", DefaultValue.subtitle_style)

    download_cover = ConfigItem("Additional", "download_cover", False, BoolValidator())
    cover_type = OptionsConfigItem("Additional", "cover_type", CoverType.JPG, OptionsValidator(CoverType), EnumSerializer(CoverType))
    attach_cover = ConfigItem("Additional", "attach_cover", False, BoolValidator())

    download_metadata = ConfigItem("Additional", "download_metadata", False, BoolValidator())
    metadata_type = OptionsConfigItem("Additional", "metadata_type", MetadataType.NFO, OptionsValidator(MetadataType), EnumSerializer(MetadataType))

    # File Naming
    naming_rule_list = ConfigItem("File Naming", "naming_convention", DefaultValue.naming_rule_list)
    numbering_type = OptionsConfigItem("File Naming", "numbering_type", NumberingType.CONTINUOUS, OptionsValidator(NumberingType), EnumSerializer(NumberingType))
    starting_number = ConfigItem("File Naming", "starting_number", 1)

    # Advanced
    prefer_cdn_server_provider = ConfigItem("Advanced", "prefer_cdn_server_provider", False, BoolValidator())
    cdn_server_list = ConfigItem("Advanced", "cdn_server_list", DefaultValue.cdn_server_list)

    ffmpeg_source = OptionsConfigItem("Advanced", "ffmpeg_source", FFmpegSource.BUNDLED, OptionsValidator(FFmpegSource), EnumSerializer(FFmpegSource), restart = True)
    custom_ffmpeg_path = ConfigItem("Advanced", "custom_ffmpeg_path", "", restart = True)

    proxy_enabled = ConfigItem("Advanced", "proxy_enabled", False, BoolValidator())
    proxy_type = OptionsConfigItem("Advanced", "proxy_type", ProxyType.HTTP, OptionsValidator(ProxyType), EnumSerializer(ProxyType))
    proxy_server = ConfigItem("Advanced", "proxy_server", "")
    proxy_port = ConfigItem("Advanced", "proxy_port", 80)
    proxy_uname = ConfigItem("Advanced", "proxy_uname", "")
    proxy_password = ConfigItem("Advanced", "proxy_password", "")

    user_agent = ConfigItem("Advanced", "user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0")

    # Update
    include_prerelease = ConfigItem("Update", "include_prerelease", False, BoolValidator())

    # Cookie
    img_key = ConfigItem("Cookie", "img_key", "")
    sub_key = ConfigItem("Cookie", "sub_key", "")

    bili_jct = ConfigItem("Cookie", "bili_jct", "")
    DedeUserID = ConfigItem("Cookie", "DedeUserID", "")
    DedeUserID__ckMd5 = ConfigItem("Cookie", "DedeUserID__ckMd5", "")
    SESSDATA = ConfigItem("Cookie", "SESSDATA", "")

    uuid = ConfigItem("Cookie", "uuid", "")
    b_lsid = ConfigItem("Cookie", "b_lsid", "")
    b_nut = ConfigItem("Cookie", "b_nut", "")
    bili_ticket = ConfigItem("Cookie", "bili_ticket", "")
    bili_ticket_expires = ConfigItem("Cookie", "bili_ticket_expires", 0)
    buvid_fp = ConfigItem("Cookie", "buvid_fp", "")
    buvid3 = ConfigItem("Cookie", "buvid3", "")
    buvid4 = ConfigItem("Cookie", "buvid4", "")
    buvid_expires = ConfigItem("Cookie", "buvid_expires", 0)

    is_login = ConfigItem("Cookie", "is_login", False, BoolValidator())
    is_expired = False

    # User
    user_uname: str = ""
    user_uid: str = ""
    user_avatar_pixmap: QPixmap = None

    accepted_terms = ConfigItem("Application", "accepted_terms", False, BoolValidator())
    skip_version = ConfigItem("Application", "skip_version", "")

    # FFmpeg
    ffmpeg_executable = ""
    bundle_ffmpeg_exist = False

    no_ffmpeg_available = True

    # Download Options
    video_quality_id = 200
    audio_quality_id = 30300
    video_codec_id = 20

    download_video_stream = True
    download_audio_stream = True
    merge_video_audio = True
    keep_original_files = False

    # Misc
    target_naming_rule_id = None
    global_starting_number = 1
    
    current_starting_number = None

    main_window_ready = False

config = APPConfig()
config.themeMode.value = Theme.AUTO

appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
config_path = Path(appdata_path) / "Bili23 Downloader" / "config.json"

if not config_path.exists():
    logger.warning("配置文件不存在，将创建新配置文件")

qconfig.load(config_path, config)