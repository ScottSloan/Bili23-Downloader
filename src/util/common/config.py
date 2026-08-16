from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QPixmap

from qfluentwidgets import (
    QConfig, RangeConfigItem, RangeValidator, OptionsValidator, OptionsConfigItem, BoolValidator,
    ConfigItem, EnumSerializer, Theme, qconfig
)

from .serializer import LanguageSerializer, ScalingSerializer
from .enum import (
    Language, WhenClose, DanmakuType, SubtitleType, CoverType, MetadataType, ProxyMode, ProxyType, FFmpegSource,
    NumberingType, Scaling, FileConflictResolution, VideoContainer, AutoSelectMode, Area, DuplicateDownloadResolution
)
from ._json import json_loads

from threading import Lock
from pathlib import Path
import logging
import json
import sys
import os

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

    auto_select_conditions = {
        "user_uploads": 0,
        "bangumi": 0,
        "other": 0
    }

    # width 为 0 表示尚无有效记录，此时窗口按默认尺寸居中显示
    window_state = {
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0,
        "maximized": False
    }

    video_quality_priority = [
        127,
        126,
        125,
        122,
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
            "id": "1fe25f91-caf0-437e-b132-c9367261ff8b",
            "name": "DEFAULT_FOR_INTERACTIVE_VIDEO",
            "type": 14,
            "rule": "{parent_title}/{leaf_title}",
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
        },
        {
            "id": "5913e25f-0bf3-4d3c-a608-8416af778a8a",
            "name": "DEFAULT_FOR_FAVORITE",
            "type": 40,
            "rule": "{favorites_owner_id}_{favorites_owner}/{favorites_name}/{leaf_title}",
            "default": True
        },
        {
            "id": "8c48ac82-14c5-4d48-9de7-225d9b53513f",
            "name": "DEFAULT_FOR_SPACE",
            "type": 50,
            "rule": "{space_owner_id}_{space_owner}/{leaf_title}",
            "default": True
        },
        {
            "id": "307ccc8e-ad2f-4195-94f0-162ee9ff1ac0",
            "name": "DEFAULT_FOR_HISTORY",
            "type": 60,
            "rule": "{parent_title}/{leaf_title}",
            "default": True
        },
        {
            "id": "0a72a82b-5684-448e-9db1-a342de933d3e",
            "name": "DEFAULT_FOR_WATCH_LATER",
            "type": 70,
            "rule": "{parent_title}/{leaf_title}",
            "default": True
        },
        {
            "id": "4d28285d-65ca-4c5c-bbb3-b3b5b570c52a",
            "name": "DEFAULT_FOR_WEEKLY",
            "type": 80,
            "rule": "{parent_title}/{leaf_title}",
            "default": True
        },
        {
            "id": "dc77bd15-be21-4847-856e-68bb3035042f",
            "name": "DEFAULT_FOR_AUDIO",
            "type": 90,
            "rule": "{parent_title}/{uploader} - {leaf_title}",
            "default": True
        }
    ]

    # 国内 CDN 服务器列表
    cn_cdn_server_list = [
        {
            "host": "upos-sz-mirror08c.bilivideo.com",
            "provider": "HUAWEI"
        },
        {
            "host": "upos-sz-mirrorhw.bilivideo.com",
            "provider": "HUAWEI"
        },
        {
            "host": "upos-sz-mirrorhwb.bilivideo.com",
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
            "host": "upos-sz-mirrorcoso1.bilivideo.com",
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
    
    # 海外 CDN 服务器列表
    ov_cdn_server_list = [
        {
            "host": "upos-hz-mirrorakam.akamaized.net",
            "provider": "AKAMAI"
        },
        {
            "host": "upos-sz-mirroraliov.bilivideo.com",
            "provider": "ALIYUN"
        },
        {
            "host": "upos-sz-mirrorcosov.bilivideo.com",
            "provider": "TENCENT"
        }
    ]

class APPConfig(QConfig):
    # APP
    app_name = "Bili23 Downloader"
    app_version = "2.15.0"
    app_comparable_version = "2.15.0"
    app_config_version = 2140
    config_version = ConfigItem("Application", "config_version", app_config_version)

    # Interface
    language = OptionsConfigItem("Interface", "language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart = True)
    display_scaling = OptionsConfigItem("Interface", "display_scaling", Scaling.AUTO, OptionsValidator(Scaling), ScalingSerializer(), restart = True)
    mica_effect = ConfigItem("Interface", "mica_effect", False, BoolValidator())

    # Behavior
    parse_list_column = ConfigItem("Behavior", "parse_list_column", DefaultValue.parse_list_column)
    parse_list_alternate_row_color = ConfigItem("Behavior", "parse_list_alternate_row_color", True, BoolValidator())
    parse_list_show_floating_command_bar = ConfigItem("Behavior", "parse_list_show_floating_command_bar", True, BoolValidator())

    monitor_clipboard = ConfigItem("Behavior", "monitor_clipboard", False, BoolValidator())
    show_download_confirmation_dialog = ConfigItem("Behavior", "show_download_confirmation_dialog", False, BoolValidator())
    auto_select_mode = OptionsConfigItem("Behavior", "auto_select_mode_", AutoSelectMode.CONDITIONAL, OptionsValidator(AutoSelectMode), EnumSerializer(AutoSelectMode))
    auto_select_conditions = ConfigItem("Behavior", "auto_select_conditions", DefaultValue.auto_select_conditions)
    parse_history = ConfigItem("Behavior", "parse_history", True, BoolValidator())

    downloading_list_sort_by = OptionsConfigItem("Behavior", "downloading_list_sort_by", "created_time", OptionsValidator(["created_time", "show_title", "file_size", "progress"]))
    downloading_list_sort_ascending = ConfigItem("Behavior", "downloading_list_sort_ascending", True, BoolValidator())
    completed_list_sort_by = OptionsConfigItem("Behavior", "completed_list_sort_by", "completed_time",OptionsValidator(["completed_time", "show_title", "file_size"]))
    completed_list_sort_ascending = ConfigItem("Behavior", "completed_list_sort_ascending", True, BoolValidator())

    silent_start = ConfigItem("Behavior", "silent_start", False, BoolValidator())
    remember_window_state = ConfigItem("Behavior", "remember_window_state", False, BoolValidator())
    window_state = ConfigItem("Behavior", "window_state", DefaultValue.window_state)
    stay_on_top = ConfigItem("Behavior", "stay_on_top", False, BoolValidator())
    when_close_window = OptionsConfigItem("Behavior", "when_close_window", WhenClose.ALWAYS_ASK, OptionsValidator(WhenClose), EnumSerializer(WhenClose))

    show_download_options_dialog = ConfigItem("Behavior", "show_download_options_dialog", True, BoolValidator())
    show_notification = ConfigItem("Behavior", "show_notification", False, BoolValidator())
    preallocate_file_space = ConfigItem("Behavior", "preallocate_file_space", True, BoolValidator())
    duplicate_download_resolution = OptionsConfigItem("Behavior", "duplicate_download_resolution", DuplicateDownloadResolution.ALWAYS_ASK, OptionsValidator(DuplicateDownloadResolution), EnumSerializer(DuplicateDownloadResolution))
    file_conflict_resolution = OptionsConfigItem("Behavior", "file_conflict_resolution", FileConflictResolution.AUTO_RENAME, OptionsValidator(FileConflictResolution), EnumSerializer(FileConflictResolution))

    # Download
    download_path = ConfigItem("Download", "download_path", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation))
    download_thread = RangeConfigItem("Download", "download_thread", 4, RangeValidator(1, 10))
    download_parallel = RangeConfigItem("Download", "download_parallel", 1, RangeValidator(1, 10))
    speed_limit_enabled = ConfigItem("Download", "speed_limit_enabled", False, BoolValidator())
    speed_limit_rate = ConfigItem("Download", "speed_limit_rate", 10.0)

    video_quality_priority = ConfigItem("Download", "video_quality_priority", DefaultValue.video_quality_priority)
    audio_quality_priority = ConfigItem("Download", "audio_quality_priority", DefaultValue.audio_quality_priority)
    video_codec_priority = ConfigItem("Download", "video_codec_priority", DefaultValue.video_codec_priority)

    video_container = OptionsConfigItem("Download", "video_container", VideoContainer.MP4, OptionsValidator(VideoContainer), EnumSerializer(VideoContainer))
    m4a_to_mp3 = ConfigItem("Download", "m4a_to_mp3", False)

    # Additional
    download_danmaku = ConfigItem("Additional", "download_danmaku", False, BoolValidator())
    danmaku_type = OptionsConfigItem("Additional", "danmaku_type", DanmakuType.ASS, OptionsValidator(DanmakuType), EnumSerializer(DanmakuType))
    danmaku_style = ConfigItem("Additional", "danmaku_style", DefaultValue.danmaku_style)
    embed_danmaku = ConfigItem("Additional", "embed_danmaku", False, BoolValidator())
    delete_danmaku_after_embed = ConfigItem("Additional", "delete_danmaku_after_embed", False, BoolValidator())

    download_subtitle = ConfigItem("Additional", "download_subtitle", False, BoolValidator())
    subtitle_type = OptionsConfigItem("Additional", "subtitle_type", SubtitleType.ASS, OptionsValidator(SubtitleType), EnumSerializer(SubtitleType))
    subtitle_language = ConfigItem("Additional", "subtitle_language", DefaultValue.subtitle_language)
    subtitle_style = ConfigItem("Additional", "subtitle_style", DefaultValue.subtitle_style)
    embed_subtitle = ConfigItem("Additional", "embed_subtitle", False, BoolValidator())
    delete_subtitle_after_embed = ConfigItem("Additional", "delete_subtitle_after_embed", False, BoolValidator())

    download_cover = ConfigItem("Additional", "download_cover", False, BoolValidator())
    cover_type = OptionsConfigItem("Additional", "cover_type", CoverType.JPG, OptionsValidator(CoverType), EnumSerializer(CoverType))
    attach_cover = ConfigItem("Additional", "attach_cover", False, BoolValidator())
    delete_cover_after_attach = ConfigItem("Additional", "delete_cover_after_attach", False, BoolValidator())

    embed_chapter = ConfigItem("Additional", "embed_chapter", False, BoolValidator())

    download_metadata = ConfigItem("Additional", "download_metadata", False, BoolValidator())
    metadata_type = OptionsConfigItem("Additional", "metadata_type", MetadataType.NFO, OptionsValidator(MetadataType), EnumSerializer(MetadataType))

    # File Naming
    naming_rule_list = ConfigItem("File Naming", "naming_rule_list", DefaultValue.naming_rule_list)
    numbering_type = OptionsConfigItem("File Naming", "numbering_type", NumberingType.CONTINUOUS, OptionsValidator(NumberingType), EnumSerializer(NumberingType))

    # Advanced
    prefer_cdn_server_provider = ConfigItem("Advanced", "prefer_cdn_server_provider_", True, BoolValidator())
    area = OptionsConfigItem("Advanced", "area", Area.CN, OptionsValidator(Area), EnumSerializer(Area))
    cn_cdn_server_list = ConfigItem("Advanced", "cn_cdn_server_list", DefaultValue.cn_cdn_server_list)
    ov_cdn_server_list = ConfigItem("Advanced", "ov_cdn_server_list", DefaultValue.ov_cdn_server_list)

    ffmpeg_source = OptionsConfigItem("Advanced", "ffmpeg_source", FFmpegSource.BUNDLED, OptionsValidator(FFmpegSource), EnumSerializer(FFmpegSource), restart = True)
    custom_ffmpeg_path = ConfigItem("Advanced", "custom_ffmpeg_path", "", restart = True)

    proxy_mode = OptionsConfigItem("Advanced", "proxy_mode", ProxyMode.SYSTEM, OptionsValidator(ProxyMode), EnumSerializer(ProxyMode), restart = True)
    proxy_type = OptionsConfigItem("Advanced", "proxy_type", ProxyType.HTTP, OptionsValidator(ProxyType), EnumSerializer(ProxyType))
    proxy_server = ConfigItem("Advanced", "proxy_server", "")
    proxy_port = ConfigItem("Advanced", "proxy_port", 80)
    proxy_uname = ConfigItem("Advanced", "proxy_uname", "")
    proxy_password = ConfigItem("Advanced", "proxy_password", "")

    user_agent = ConfigItem("Advanced", "user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0")

    # MCP
    # 默认关闭。开启后会在本地环回地址上监听一个 HTTP 端点，供 AI 客户端调用，
    # 必须由用户显式启用，且访问需要携带 mcp_token
    mcp_enabled = ConfigItem("MCP", "mcp_enabled", False, BoolValidator())
    mcp_port = RangeConfigItem("MCP", "mcp_port", 23330, RangeValidator(1024, 65535))
    mcp_token = ConfigItem("MCP", "mcp_token", "")
    mcp_allow_download = ConfigItem("MCP", "mcp_allow_download", True, BoolValidator())

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

    # Application
    accepted_terms = ConfigItem("Application", "accepted_terms", False, BoolValidator())
    skip_version = ConfigItem("Application", "skip_version", "")

    # User
    user_uname: str = ""
    user_uid: str = ""
    user_avatar_pixmap: QPixmap = None

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
    keep_original_files_type = 0

    # MCP 运行时状态，仅供界面展示，不落盘
    mcp_running = False
    mcp_last_error = ""

    # Misc
    target_naming_rule_id = None
    global_starting_number = 1
    current_starting_number = None

    main_window_ready = False

    show_auto_parse_dialog = ConfigItem("Misc", "show_auto_parse_dialog", False, BoolValidator())
    auto_add_to_download_list = ConfigItem("Misc", "auto_add_to_download_list", False, BoolValidator())
    auto_parse_interval = ConfigItem("Misc", "auto_parse_interval", 2.0)

    auto_parse_teaching_tip_shown = ConfigItem("Misc", "auto_parse_teaching_tip_shown_", False, BoolValidator())

    tutorial_dialog_shown = ConfigItem("Misc", "tutorial_dialog_shown", False, BoolValidator())
    select_area_dialog_shown = ConfigItem("Misc", "select_area_dialog_shown", False, BoolValidator())

    # 写盘串行化。qfluentwidgets 的 save() 直接 open(..., "w") 覆写整个文件，没有任何保护，
    # 而 config.set() 默认会立即触发写盘 —— 登录相关的请求回调各自跑在自己的工作线程上
    # （cookie_manager.init_cookie_info 在启动时会并发发出三个请求），
    # 两个线程同时打开同一个文件写入，配置会被写成互相交错的内容。
    _save_lock = Lock()

    def save(self):
        with self._save_lock:
            self._cfg.file.parent.mkdir(parents = True, exist_ok = True)

            # 先写临时文件再原子替换。就地截断写一旦在中途被打断，留下的就是一个残缺的配置文件，
            # 用户的全部设置随之丢失；而退出流程走的是 os._exit，不会等待仍在写盘的线程。
            temp_path = self._cfg.file.parent / f"{self._cfg.file.name}.tmp"

            try:
                with open(temp_path, "w", encoding = "utf-8") as f:
                    json.dump(self._cfg.toDict(), f, ensure_ascii = False, indent = 4)

                os.replace(temp_path, self._cfg.file)

            except Exception:
                logger.exception("保存配置文件失败")

                try:
                    temp_path.unlink(missing_ok = True)

                except Exception:
                    pass

def check_need_patch():
    # 检查是否需要修补配置文件
    if config_path.exists():
        with open(config_path, "r", encoding = "utf-8") as f:
            try:
                data = json_loads(f.read())

            except Exception as e:
                data = {}
                
                logger.error(f"读取配置文件时发生错误：{e}")

            if "config_version" in data.get("Application", {}):
                config_version = data.get("Application", {}).get("config_version", 0)

                return config_version < config.app_config_version, config_version, data
            else:
                return True, 0, data
    else:
        return False, 0, {}

def patch_config(config_version: int, data: dict):
    # 配置文件修补
    if config_version < 2130:
        # 2.13.0 起代理设置由 proxy_enabled 开关改为 proxy_mode 三态选择。
        # 旧版开着代理开关的迁移为手动设置，其余保持默认的跟随系统代理
        if data.get("Advanced", {}).get("proxy_enabled"):
            config.set(config.proxy_mode, ProxyMode.MANUAL)

            logger.info("代理设置已迁移为手动设置")

    if config_version < 2140:
        # 2.14.0 起支持 SDR 增强（qn 122）。画质优先级列表是一份完整枚举，
        # 选择画质时只遍历列表内的值，旧配置里没有 122 就永远选不中该画质；
        # 且优先级对话框是按配置列表渲染的，缺项不仅调不了，保存后还会把它彻底丢掉。
        # 因此这里补进列表，位置与默认值一致（HDR 之后、4K 之前），用户自定义过的顺序不受影响
        video_quality_priority = config.get(config.video_quality_priority).copy()

        if 122 not in video_quality_priority:
            if 120 in video_quality_priority:
                video_quality_priority.insert(video_quality_priority.index(120), 122)
            else:
                # 找不到 4K 作为锚点时兜底追加，至少保证该画质可被选中
                video_quality_priority.append(122)

            config.set(config.video_quality_priority, video_quality_priority)

            logger.info("SDR 增强画质已补入画质优先级列表")

    # 完成修补，写入新的 config_version
    config.set(config.config_version, config.app_config_version)
    config.save()

config = APPConfig()
config.themeMode.value = Theme.AUTO

appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
config_path = Path(appdata_path) / "Bili23 Downloader" / "config.json"

if not config_path.exists():
    logger.warning("配置文件不存在，将创建新配置文件")

qconfig.load(config_path, config)

# 判断是否需要修补配置文件
need_patch, config_version, data = check_need_patch()

if need_patch:
    logger.info("检测到旧版本配置文件，正在进行修补")

    patch_config(config_version, data)
