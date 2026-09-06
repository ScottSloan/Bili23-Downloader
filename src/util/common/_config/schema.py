"""
配置项 schema

S2-2「config 去 qfluentwidgets」的第一步：把原先散落在 APPConfig 类体里的 ConfigItem 声明
抽成一份与框架无关的声明式清单，运行时再据此构造配置项对象。

设计取舍：
- 调用方是 `config.get(config.download_path)` 这种「按项取值」的形态，不是 `settings.download_path`
  的属性形态，所以这里用 ITEMS 清单而非一个巨型模型类。attr 必须与原 APPConfig 的属性名逐字一致。
- 校验语义是「纠正而非拒绝」：范围超界 clamp 到边界，枚举值不认识则回落默认值。
  本文件只负责【声明】范围与可选值，具体纠正逻辑不在这里实现。
- 本文件不引入 Qt 依赖。唯一的例外见下面 language 项的 TODO。
"""

from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum

from ..enum import (
    Language, WhenClose, DanmakuType, SubtitleType, CoverType, MetadataType, ProxyMode, ProxyType, FFmpegSource,
    NumberingType, Scaling, FileConflictResolution, VideoContainer, AutoSelectMode, Area,
    DuplicateDownloadResolution
)

# 配置文件结构版本。唯一来源在 runtime.py，与程序版本号放在一起 ——
# 版本号散成多处是本仓库已知的维护陷阱（CLAUDE.md 里专门写了这一条），不要在这里另起一份
from .runtime import APP_CONFIG_VERSION


class ValueType(Enum):
    """配置项的值类型。只描述「是什么」，不含任何序列化/校验实现"""

    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    LIST = "list"
    DICT = "dict"
    ENUM = "enum"       # options 为一个 Enum 子类
    COLOR = "color"     # 十六进制颜色字符串，仅 QFluentWidgets 组使用


class DynamicDefault:
    """
    默认值需要在运行时求得的占位。

    例如下载目录原本取自 QStandardPaths.DownloadLocation，是平台相关的；
    把它写死在 schema 里既不正确也会引入 Qt 依赖，因此只在这里留一个具名标记，
    由运行时的配置构造代码按 name 解析成实际值。
    """

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"DynamicDefault({self.name!r})"


@dataclass(frozen = True)
class ItemSpec:
    """单个配置项的声明"""

    attr: str                           # Python 属性名，调用方以 config.<attr> 访问，不可改动
    group: str                          # config.json 中的一级键
    key: str                            # config.json 中的二级键，多数与 attr 同名
    default: Any                        # 默认值
    type: ValueType                     # 值类型
    options: Any = None                 # 可选值：Enum 子类，或字面量列表
    range: Optional[tuple] = None       # 取值范围 (min, max)，仅数值项
    restart: bool = False               # 改动后是否需要重启程序才能生效


def _item(attr, group, default, type, *, key = None, options = None, range = None, restart = False):
    # key 省略时与 attr 同名，只有少数历史遗留项（带下划线后缀、大驼峰）需要显式指定
    return ItemSpec(
        attr = attr,
        group = group,
        key = key if key is not None else attr,
        default = default,
        type = type,
        options = options,
        range = range,
        restart = restart
    )


class DefaultValue:
    """
    复杂默认值（列表、字典）。

    自 config.py 原样搬入，S2-2 完成后原文件那份会删除。
    这里不做任何内容改动 —— 其中若干结构（naming_rule_list 的 uuid、cdn 列表）是有语义的，
    改动会影响存量用户配置的迁移。
    """

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
            "id": "b7a4f0c5-1d2e-4a83-9f61-3c0d7e5b8a19",
            "name": "DEFAULT_FOR_LESSON",
            "type": 31,
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


# 默认 User-Agent，跟随 Edge 稳定版更新
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0"

# 全部配置项（不含 QFluentWidgets 组，那部分见 QFLUENT_ITEMS）
ITEMS = [
    # ---------------- Application ----------------
    _item("config_version", "Application", APP_CONFIG_VERSION, ValueType.INT),
    _item("accepted_terms", "Application", False, ValueType.BOOL),
    _item("skip_version", "Application", "", ValueType.STR),

    # ---------------- Interface ----------------
    # 成员顺序即语言下拉框的选项顺序，与 setting.py 里的 texts 一一对应，改动前先看那里
    _item("language", "Interface", Language.AUTO, ValueType.ENUM, options = Language, restart = True),
    _item("display_scaling", "Interface", Scaling.AUTO, ValueType.ENUM, options = Scaling, restart = True),
    _item("mica_effect", "Interface", False, ValueType.BOOL),

    # ---------------- Behavior ----------------
    _item("parse_list_column", "Behavior", DefaultValue.parse_list_column, ValueType.LIST),
    _item("parse_list_alternate_row_color", "Behavior", True, ValueType.BOOL),
    _item("parse_list_show_floating_command_bar", "Behavior", True, ValueType.BOOL),

    _item("monitor_clipboard", "Behavior", False, ValueType.BOOL),
    _item("show_download_confirmation_dialog", "Behavior", False, ValueType.BOOL),
    # key 带下划线后缀，是历史上换过默认值时用来作废旧配置的手法，不能改
    _item("auto_select_mode", "Behavior", AutoSelectMode.CONDITIONAL, ValueType.ENUM, key = "auto_select_mode_", options = AutoSelectMode),
    _item("auto_select_conditions", "Behavior", DefaultValue.auto_select_conditions, ValueType.DICT),
    _item("parse_history", "Behavior", True, ValueType.BOOL),

    _item("downloading_list_sort_by", "Behavior", "created_time", ValueType.STR, options = ["created_time", "show_title", "file_size", "progress"]),
    _item("downloading_list_sort_ascending", "Behavior", True, ValueType.BOOL),
    _item("completed_list_sort_by", "Behavior", "completed_time", ValueType.STR, options = ["completed_time", "show_title", "file_size"]),
    _item("completed_list_sort_ascending", "Behavior", True, ValueType.BOOL),

    _item("silent_start", "Behavior", False, ValueType.BOOL),
    _item("remember_window_state", "Behavior", False, ValueType.BOOL),
    _item("window_state", "Behavior", DefaultValue.window_state, ValueType.DICT),
    _item("stay_on_top", "Behavior", False, ValueType.BOOL),
    _item("when_close_window", "Behavior", WhenClose.ALWAYS_ASK, ValueType.ENUM, options = WhenClose),

    _item("show_download_options_dialog", "Behavior", True, ValueType.BOOL),
    _item("show_notification", "Behavior", False, ValueType.BOOL),
    _item("preallocate_file_space", "Behavior", True, ValueType.BOOL),
    _item("duplicate_download_resolution", "Behavior", DuplicateDownloadResolution.ALWAYS_ASK, ValueType.ENUM, options = DuplicateDownloadResolution),
    _item("file_conflict_resolution", "Behavior", FileConflictResolution.AUTO_RENAME, ValueType.ENUM, options = FileConflictResolution),

    # ---------------- Download ----------------
    # 默认下载目录是平台相关的（原先取自 QStandardPaths.DownloadLocation），运行时解析
    _item("download_path", "Download", DynamicDefault("download_path"), ValueType.STR),
    _item("download_thread", "Download", 4, ValueType.INT, range = (1, 10)),
    _item("download_parallel", "Download", 1, ValueType.INT, range = (1, 10)),
    _item("speed_limit_enabled", "Download", False, ValueType.BOOL),
    _item("speed_limit_rate", "Download", 10.0, ValueType.FLOAT),

    _item("video_quality_priority", "Download", DefaultValue.video_quality_priority, ValueType.LIST),
    _item("audio_quality_priority", "Download", DefaultValue.audio_quality_priority, ValueType.LIST),
    _item("video_codec_priority", "Download", DefaultValue.video_codec_priority, ValueType.LIST),

    _item("video_container", "Download", VideoContainer.MP4, ValueType.ENUM, options = VideoContainer),
    # 原先没挂 BoolValidator，但取值语义就是布尔
    _item("m4a_to_mp3", "Download", False, ValueType.BOOL),

    # ---------------- Additional ----------------
    _item("download_danmaku", "Additional", False, ValueType.BOOL),
    _item("danmaku_type", "Additional", DanmakuType.ASS, ValueType.ENUM, options = DanmakuType),
    _item("danmaku_style", "Additional", DefaultValue.danmaku_style, ValueType.DICT),
    _item("embed_danmaku", "Additional", False, ValueType.BOOL),
    _item("delete_danmaku_after_embed", "Additional", False, ValueType.BOOL),

    _item("download_subtitle", "Additional", False, ValueType.BOOL),
    _item("subtitle_type", "Additional", SubtitleType.ASS, ValueType.ENUM, options = SubtitleType),
    _item("subtitle_language", "Additional", DefaultValue.subtitle_language, ValueType.DICT),
    _item("subtitle_style", "Additional", DefaultValue.subtitle_style, ValueType.DICT),
    _item("embed_subtitle", "Additional", False, ValueType.BOOL),
    _item("delete_subtitle_after_embed", "Additional", False, ValueType.BOOL),

    _item("download_cover", "Additional", False, ValueType.BOOL),
    _item("cover_type", "Additional", CoverType.JPG, ValueType.ENUM, options = CoverType),
    _item("attach_cover", "Additional", False, ValueType.BOOL),
    _item("delete_cover_after_attach", "Additional", False, ValueType.BOOL),

    _item("embed_chapter", "Additional", False, ValueType.BOOL),

    _item("download_metadata", "Additional", False, ValueType.BOOL),
    _item("metadata_type", "Additional", MetadataType.NFO, ValueType.ENUM, options = MetadataType),

    # ---------------- File Naming ----------------
    _item("naming_rule_list", "File Naming", DefaultValue.naming_rule_list, ValueType.LIST),
    _item("numbering_type", "File Naming", NumberingType.CONTINUOUS, ValueType.ENUM, options = NumberingType),

    # ---------------- Advanced ----------------
    # key 带下划线后缀，同 auto_select_mode
    _item("prefer_cdn_server_provider", "Advanced", True, ValueType.BOOL, key = "prefer_cdn_server_provider_"),
    _item("area", "Advanced", Area.CN, ValueType.ENUM, options = Area),
    _item("cn_cdn_server_list", "Advanced", DefaultValue.cn_cdn_server_list, ValueType.LIST),
    _item("ov_cdn_server_list", "Advanced", DefaultValue.ov_cdn_server_list, ValueType.LIST),

    _item("ffmpeg_source", "Advanced", FFmpegSource.BUNDLED, ValueType.ENUM, options = FFmpegSource, restart = True),
    _item("custom_ffmpeg_path", "Advanced", "", ValueType.STR, restart = True),

    _item("proxy_mode", "Advanced", ProxyMode.SYSTEM, ValueType.ENUM, options = ProxyMode, restart = True),
    _item("proxy_type", "Advanced", ProxyType.HTTP, ValueType.ENUM, options = ProxyType),
    _item("proxy_server", "Advanced", "", ValueType.STR),
    _item("proxy_port", "Advanced", 80, ValueType.INT),
    _item("proxy_uname", "Advanced", "", ValueType.STR),
    _item("proxy_password", "Advanced", "", ValueType.STR),

    _item("user_agent", "Advanced", DEFAULT_USER_AGENT, ValueType.STR),

    # ---------------- MCP ----------------
    # 默认关闭。开启后会在本地环回地址上监听一个 HTTP 端点，供 AI 客户端调用，
    # 必须由用户显式启用，且访问需要携带 mcp_token
    _item("mcp_enabled", "MCP", False, ValueType.BOOL),
    _item("mcp_port", "MCP", 23330, ValueType.INT, range = (1024, 65535)),
    _item("mcp_token", "MCP", "", ValueType.STR),

    # ---------------- Update ----------------
    _item("include_prerelease", "Update", False, ValueType.BOOL),

    # ---------------- Cookie ----------------
    _item("img_key", "Cookie", "", ValueType.STR),
    _item("sub_key", "Cookie", "", ValueType.STR),

    _item("bili_jct", "Cookie", "", ValueType.STR),
    _item("DedeUserID", "Cookie", "", ValueType.STR),
    _item("DedeUserID__ckMd5", "Cookie", "", ValueType.STR),
    _item("SESSDATA", "Cookie", "", ValueType.STR),

    _item("uuid", "Cookie", "", ValueType.STR),
    _item("b_lsid", "Cookie", "", ValueType.STR),
    _item("b_nut", "Cookie", "", ValueType.STR),
    _item("bili_ticket", "Cookie", "", ValueType.STR),
    _item("bili_ticket_expires", "Cookie", 0, ValueType.INT),
    _item("buvid_fp", "Cookie", "", ValueType.STR),
    _item("buvid3", "Cookie", "", ValueType.STR),
    _item("buvid4", "Cookie", "", ValueType.STR),
    _item("buvid_expires", "Cookie", 0, ValueType.INT),

    _item("is_login", "Cookie", False, ValueType.BOOL),

    # ---------------- Misc ----------------
    _item("show_auto_parse_dialog", "Misc", False, ValueType.BOOL),
    _item("auto_add_to_download_list", "Misc", False, ValueType.BOOL),
    _item("auto_parse_interval", "Misc", 2.0, ValueType.FLOAT),
    # key 带下划线后缀，同 auto_select_mode
    _item("auto_parse_teaching_tip_shown", "Misc", False, ValueType.BOOL, key = "auto_parse_teaching_tip_shown_"),
    _item("tutorial_dialog_shown", "Misc", False, ValueType.BOOL),
    _item("select_area_dialog_shown", "Misc", False, ValueType.BOOL),
]


# QFluentWidgets 组的配置项。
# 这三项由桌面侧的桥接层拥有（qfluentwidgets 的 QConfig 自带并自行读写），core 只负责原样透传，
# 不解释其取值，也不参与纠正。因此单独列出，不混进 ITEMS。
QFLUENT_ITEMS = [
    # 取值为 "Light" / "Dark" / "Auto"。
    # 注意：这里记录的是配置项声明的默认值（Light），而 config.py 在实例化后额外做了
    # `config.themeMode.value = Theme.AUTO`，实际运行时首启表现为跟随系统
    _item("themeMode", "QFluentWidgets", "Light", ValueType.STR, key = "ThemeMode", options = ["Light", "Dark", "Auto"]),
    # qfluentwidgets 的默认主题色 #009faa
    _item("themeColor", "QFluentWidgets", "#009faa", ValueType.COLOR, key = "ThemeColor"),
    _item("fontFamilies", "QFluentWidgets", ["Segoe UI", "Microsoft YaHei", "PingFang SC"], ValueType.LIST, key = "FontFamilies"),
]


# 按 attr 索引，便于运行时 O(1) 查表
ITEMS_BY_ATTR = {item.attr: item for item in ITEMS}
QFLUENT_ITEMS_BY_ATTR = {item.attr: item for item in QFLUENT_ITEMS}

ALL_ITEMS = ITEMS + QFLUENT_ITEMS
ALL_ITEMS_BY_ATTR = {item.attr: item for item in ALL_ITEMS}
