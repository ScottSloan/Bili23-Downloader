from PySide6.QtCore import QStandardPaths

from qfluentwidgets import (
    QConfig, RangeConfigItem, RangeValidator, OptionsValidator, OptionsConfigItem, BoolValidator,
    ConfigItem, EnumSerializer, Theme, qconfig
)

from .serializer import LanguageSerializer, ScalingSerializer, SecretSerializer
from .enum import (
    Language, WhenClose, DanmakuType, SubtitleType, CoverType, MetadataType, ProxyMode, ProxyType, FFmpegSource,
    NumberingType, Scaling, FileConflictResolution, VideoContainer, AutoSelectMode, Area, DuplicateDownloadResolution,
    OriginalFileType
)
from ._json import loads, dumps_std
from .runtime import runtime

from threading import Lock
from typing import ClassVar
from pathlib import Path
from copy import deepcopy
import logging
import stat
import sys
import os

logger = logging.getLogger(__name__)

def isWin11():
    return sys.platform == "win32" and sys.getwindowsversion().build >= 22000

class DefaultValue:
    parse_list_column: ClassVar = [
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

    auto_select_conditions: ClassVar = {
        "user_uploads": 0,
        "bangumi": 0,
        "other": 0
    }

    # width 为 0 表示尚无有效记录，此时窗口按默认尺寸居中显示
    window_state: ClassVar = {
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0,
        "maximized": False
    }

    video_quality_priority: ClassVar = [
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

    audio_quality_priority: ClassVar = [
        30251,
        30250,
        30280,
        30232,
        30216
    ]
    
    video_codec_priority: ClassVar = [
        7,
        12,
        13
    ]

    danmaku_style: ClassVar = {
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
    
    subtitle_language: ClassVar = {
        "download_specified": False,
        "specified_language": []
    }

    subtitle_style: ClassVar = {
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
            "border": "&H00000000",
            "shadow": "&H00000000"
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

    naming_rule_list: ClassVar = [
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
            "rule": "{favorites_owner_id}_{favorites_owner}/{favorites_name}/{parent_title}/<P{p:02d}->{leaf_title}",
            "default": True
        },
        {
            "id": "8c48ac82-14c5-4d48-9de7-225d9b53513f",
            "name": "DEFAULT_FOR_SPACE",
            "type": 50,
            "rule": "{space_owner_id}_{space_owner}/{parent_title}/<P{p:02d}->{leaf_title}",
            "default": True
        },
        {
            "id": "307ccc8e-ad2f-4195-94f0-162ee9ff1ac0",
            "name": "DEFAULT_FOR_HISTORY",
            "type": 60,
            "rule": "{source_title}/{parent_title}/<P{p:02d}->{leaf_title}",
            "default": True
        },
        {
            "id": "0a72a82b-5684-448e-9db1-a342de933d3e",
            "name": "DEFAULT_FOR_WATCH_LATER",
            "type": 70,
            "rule": "{source_title}/{parent_title}/<P{p:02d}->{leaf_title}",
            "default": True
        },
        {
            "id": "4d28285d-65ca-4c5c-bbb3-b3b5b570c52a",
            "name": "DEFAULT_FOR_WEEKLY",
            "type": 80,
            "rule": "{source_title}/{leaf_title}",
            "default": True
        },
        {
            "id": "dc77bd15-be21-4847-856e-68bb3035042f",
            "name": "DEFAULT_FOR_AUDIO",
            "type": 90,
            "rule": "{source_title}/{uploader} - {leaf_title}",
            "default": True
        }
    ]

    # 国内 CDN 服务器列表
    cn_cdn_server_list: ClassVar = [
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
    #
    # 这里原先把 Akamai（upos-hz-mirrorakam.akamaized.net）列在首位。它作为**替换目标**
    # 不可用：把别的 host 的签名链接改写过去，无论直连还是经代理一律返回 403，与出口
    # 地区无关。而本列表的用途恰恰是替换 host（见 CDN.replace），留着它只会让每次海外
    # 解析白占一个并发探测位，因此移除。
    #
    # 别把结论扩大化：Akamai 拒绝的是"被改写"的请求，不是 upos 链接本身 —— B 站原生
    # 签发的 Akamai 链接实测返回 206（香港出口下 16MB 读到 10.84 Mbps）。那类链接本来
    # 就出现在 playurl 返回值里，也不在黑名单中，作为原始候选照常参与探测
    ov_cdn_server_list: ClassVar = [
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
    app_version = "2.22.0"
    app_comparable_version = "2.22.0"
    # 配置格式版本。**改动必须在 patch_config 里加对应的门禁并把它 +1**，
    # 否则已有用户配置里那份副本永远不会被更新（DefaultValue 只在配置文件不存在时
    # 作为初值）。与 app_version 不要求逐字对应
    app_config_version = 2200
    config_version = ConfigItem("Application", "config_version", app_config_version)

    # Interface
    language = OptionsConfigItem("Interface", "language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart = True)
    display_scaling = OptionsConfigItem("Interface", "display_scaling", Scaling.AUTO, OptionsValidator(Scaling), ScalingSerializer(), restart = True)
    mica_effect = ConfigItem("Interface", "mica_effect", False, BoolValidator())

    # Behavior
    parse_list_column = ConfigItem("Behavior", "parse_list_column", DefaultValue.parse_list_column)
    parse_list_alternate_row_color = ConfigItem("Behavior", "parse_list_alternate_row_color", True, BoolValidator())
    parse_list_show_floating_command_bar = ConfigItem("Behavior", "parse_list_show_floating_command_bar", True, BoolValidator())
    parse_list_mark_downloaded = ConfigItem("Behavior", "parse_list_mark_downloaded", True, BoolValidator())

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
    show_download_as_single_video_dialog = ConfigItem("Behavior", "show_download_as_single_video_dialog", True, BoolValidator())
    show_notification = ConfigItem("Behavior", "show_notification", False, BoolValidator())
    preallocate_file_space = ConfigItem("Behavior", "preallocate_file_space", True, BoolValidator())
    duplicate_download_resolution = OptionsConfigItem("Behavior", "duplicate_download_resolution", DuplicateDownloadResolution.ALWAYS_ASK, OptionsValidator(DuplicateDownloadResolution), EnumSerializer(DuplicateDownloadResolution))
    file_conflict_resolution = OptionsConfigItem("Behavior", "file_conflict_resolution", FileConflictResolution.AUTO_RENAME, OptionsValidator(FileConflictResolution), EnumSerializer(FileConflictResolution))

    # Download
    download_path = ConfigItem("Download", "download_path", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation))
    download_thread = RangeConfigItem("Download", "download_thread", 4, RangeValidator(1, 10))
    download_parallel = RangeConfigItem("Download", "download_parallel", 1, RangeValidator(1, 10))
    # 同时运行的 FFmpeg 合并/转换任务数（Issue #490）。默认且推荐保持 1：并行合并曾把机器
    # 拖到卡死 —— 流拷贝几乎全是磁盘读写，多个 FFmpeg 同时读写同一块盘时会互相抢占，
    # 转 MP3 这类重编码还会吃满 CPU。上限刻意定得很低，只给磁盘性能足够的用户留出余地
    merge_parallel = RangeConfigItem("Download", "merge_parallel", 1, RangeValidator(1, 4))
    speed_limit_enabled = ConfigItem("Download", "speed_limit_enabled", False, BoolValidator())
    speed_limit_rate = ConfigItem("Download", "speed_limit_rate", 10.0)

    # 任务级自动重试（Issue #469）。只对网络类可重试错误生效，403/404 这类永久错误
    # 仍直接进终态，因此默认开启是安全的 —— 网络差的用户不必先去设置里找开关。
    # 退避节奏写死在 Downloader 里，不在这里暴露：它与分片级重试是两层概念
    auto_retry_enabled = ConfigItem("Download", "auto_retry_enabled", True, BoolValidator())
    auto_retry_max_count = RangeConfigItem("Download", "auto_retry_max_count", 5, RangeValidator(1, 20))

    video_quality_priority = ConfigItem("Download", "video_quality_priority", DefaultValue.video_quality_priority)
    audio_quality_priority = ConfigItem("Download", "audio_quality_priority", DefaultValue.audio_quality_priority)
    video_codec_priority = ConfigItem("Download", "video_codec_priority", DefaultValue.video_codec_priority)

    video_container = OptionsConfigItem("Download", "video_container", VideoContainer.MP4, OptionsValidator(VideoContainer), EnumSerializer(VideoContainer))
    m4a_to_mp3 = ConfigItem("Download", "m4a_to_mp3", False)

    # 下载哪几路流、下完之后怎么处理。
    #
    # 这几个值原先放在 runtime.download 上（下载选项对话框的「本次选择」），
    # 3cfb1a4d 把进程级运行时状态从 APPConfig 剥离时一并迁了过去，理由是
    # 「它们只是下一个任务用什么参数的暂存」。但它们同样是用户实打实的偏好：
    # 只想收音频的人不该每下载一个稿件都去对话框里勾一次，而对话框本身
    # 也只有下载时才打得开。改为配置项后两个入口改的是同一份值，重启后仍保留。
    #
    # 单次下载仍由下载选项对话框的值固化进 TaskInfo（见 task/options.py），
    # 改动这里不会波及已经排进队列的任务
    download_video_stream = ConfigItem("Download", "download_video_stream", True, BoolValidator())
    download_audio_stream = ConfigItem("Download", "download_audio_stream", True, BoolValidator())
    merge_video_audio = ConfigItem("Download", "merge_video_audio", True, BoolValidator())
    keep_original_files = ConfigItem("Download", "keep_original_files", False, BoolValidator())
    keep_original_files_type = OptionsConfigItem("Download", "keep_original_files_type", OriginalFileType.BOTH, OptionsValidator(OriginalFileType), EnumSerializer(OriginalFileType))

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
    # 令牌落盘加密，理由与下方登录 Cookie 相同；stdio 桥接读它时同样走 util.common.secret 解密
    mcp_token = ConfigItem("MCP", "mcp_token", "", serializer = SecretSerializer())

    # Update
    include_prerelease = ConfigItem("Update", "include_prerelease", False, BoolValidator())

    # Cookie
    img_key = ConfigItem("Cookie", "img_key", "")
    sub_key = ConfigItem("Cookie", "sub_key", "")

    # 登录凭据落盘加密（Windows DPAPI，见 util/common/secret.py）。SESSDATA 足以完整
    # 登录账号，bili_jct 可以代替用户发起操作，明文躺在配置文件里，用户把 config.json
    # 附进 issue 或同步进网盘就等于交出了账号。
    #
    # 每项各自一个 SecretSerializer 实例，不能共用：实例上缓存着该字段的明文与密文。
    # buvid、b_lsid 这类设备指纹不涉及账号，不加密
    bili_jct = ConfigItem("Cookie", "bili_jct", "", serializer = SecretSerializer())
    DedeUserID = ConfigItem("Cookie", "DedeUserID", "", serializer = SecretSerializer())
    DedeUserID__ckMd5 = ConfigItem("Cookie", "DedeUserID__ckMd5", "", serializer = SecretSerializer())
    SESSDATA = ConfigItem("Cookie", "SESSDATA", "", serializer = SecretSerializer())

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

    # Application
    accepted_terms = ConfigItem("Application", "accepted_terms", False, BoolValidator())
    skip_version = ConfigItem("Application", "skip_version", "")

    # Misc
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
                with _open_private(temp_path) as f:
                    f.write(dumps_std(self._cfg.toDict(), indent = 4))

                os.replace(temp_path, self._cfg.file)

            except Exception:
                logger.exception("保存配置文件失败")

                try:
                    temp_path.unlink(missing_ok = True)

                except OSError:
                    # 临时文件清理失败不影响主流程，下次保存会覆盖它
                    pass

    def export_to(self, path) -> bool:
        """
        导出配置到指定文件，返回是否成功

        登录态（login_state_items）一律以默认值写出：导出的文件是拿去备份、换电脑、
        附进 issue 排查问题的，带着凭据只有风险；Windows 上的 DPAPI 密文换台电脑
        也解不开，留着同样没有用处。

        直接从 toDict() 生成而不是另建一个 APPConfig 去 load —— 配置项是类属性，
        两个实例共用同一批 ConfigItem，「临时实例」的 load 其实是把磁盘内容读回了
        全局配置，save = False 写入的值（如 wbi 密钥）会被磁盘上的旧值覆盖。
        """
        # 与 save 互斥：toDict 会经 SecretSerializer 读写各字段的密文缓存
        with self._save_lock:
            data = self._cfg.toDict()

        for item in login_state_items():
            data[item.group][item.name] = item.serializer.serialize(item.defaultValue)

        try:
            with open(path, "w", encoding = "utf-8") as f:
                f.write(dumps_std(data, indent = 4))

        except OSError:
            logger.exception("导出配置失败，路径：%s", path)

            return False

        return True

    def import_from(self, path) -> bool:
        """
        从指定文件导入配置并保存，返回是否成功

        登录态（login_state_items）保留本机当前值，不被导入文件覆盖：别的电脑导出的
        DPAPI 密文在这里解不开，照搬只会把本机有效的登录清空；旧版导出文件里的明文
        Cookie 也不再接收 —— 换电脑重新登录一次，好过让凭据随配置文件流转。

        不用 qfluentwidgets 的 load()：它会把文件里的每一项都反序列化进来（解不开的
        密文还会记一条误导性的告警），并改写 self.file，要事后再改回去。这里按与
        load() 相同的「分组.名称」规则逐项写入，跳过登录态即可。
        """
        try:
            with open(path, "r", encoding = "utf-8") as f:
                data = loads(f.read())

        except (OSError, ValueError):
            logger.exception("读取导入的配置文件失败，路径：%s", path)

            return False

        if not isinstance(data, dict):
            logger.error("导入的配置文件格式不正确，路径：%s", path)

            return False

        items = {
            item.key: item
            for item in (getattr(self._cfg.__class__, name) for name in dir(self._cfg.__class__))
            if isinstance(item, ConfigItem)
        }

        skipped = {item.key for item in login_state_items()}

        def apply(key: str, value):
            item = items.get(key)

            if item is not None and key not in skipped:
                item.deserializeFrom(value)

        for group, value in data.items():
            if isinstance(value, dict):
                for name, item_value in value.items():
                    apply(f"{group}.{name}", item_value)

            else:
                apply(group, value)

        self.save()

        return True

def login_state_items() -> list:
    """
    不随配置导入导出迁移的配置项：所有挂着 SecretSerializer 的敏感字段，加上 is_login

    按 serializer 类型自动收集而不是写死名单，新增敏感字段时导入导出自动跟上。
    is_login 必须与凭据同进退：凭据被剔除而它还是 True，界面会显示已登录，
    请求却不带有效的 SESSDATA。
    """
    items = [
        item for item in (getattr(APPConfig, name) for name in dir(APPConfig))
        if isinstance(item, ConfigItem) and isinstance(item.serializer, SecretSerializer)
    ]

    items.append(APPConfig.is_login)

    return items

def restrict_permission(path: Path):
    """
    非 Windows 平台上把已有配置文件的权限收紧到仅当前用户可读写

    save() 写出的文件本身就是 0600，但旧版留下的配置是按默认 umask 创建的（通常 0644），
    要等到下次写盘才会被替换掉 —— 而启动时不一定有设置项改动，这期间凭据对同机其他用户可读。
    只去掉组与其他用户的权限位，不重写文件
    """
    if sys.platform == "win32":
        return

    try:
        mode = stat.S_IMODE(path.stat().st_mode)

        if mode & 0o077:
            os.chmod(path, mode & ~0o077)

            logger.info("已收紧配置文件权限：%o → %o", mode, mode & ~0o077)

    except FileNotFoundError:
        pass

    except OSError:
        logger.warning("收紧配置文件权限失败：%s", path, exc_info = True)

def _open_private(path: Path):
    """
    以仅当前用户可读写的权限打开文件用于写入

    非 Windows 平台上敏感字段不加密（见 util/common/secret.py），文件权限是唯一的保护，
    必须在创建时就给 0600：先按默认权限写完再 chmod，中间有一段其他用户可读的窗口。
    fchmod 是为了收紧上次异常退出残留的临时文件 —— O_CREAT 遇到已有文件不会改它的权限。
    写入后经 os.replace 换上去，配置文件本身随之继承这个权限。

    Windows 上 %APPDATA% 本就只对当前用户开放，且敏感字段已由 DPAPI 加密，照常打开即可
    """
    if sys.platform == "win32":
        return open(path, "w", encoding = "utf-8")

    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)

    try:
        os.fchmod(fd, 0o600)

    except OSError:
        os.close(fd)

        raise

    return os.fdopen(fd, "w", encoding = "utf-8")

def settle_secrets():
    """
    配置加载完成后，收拾敏感字段的两种遗留状态

    * 登录凭据解不开（配置来自别的电脑或用户账户，SecretSerializer 已按空值处理），
      而 is_login 仍为 True：不纠正的话界面显示已登录，请求却带着空的 SESSDATA 发出去，
      用户只会看到一串莫名其妙的「未登录」错误，而不是一个干脆的「请重新登录」；
    * 读到了旧版遗留的明文：立即保存一次转成密文，不等下一次碰巧有设置被改动。
    """
    need_save = False

    if config.get(config.is_login) and not config.get(config.SESSDATA):
        config.set(config.is_login, False, save = False)

        need_save = True

        logger.warning("登录凭据缺失或无法解密，已重置为未登录状态")

    if SecretSerializer.legacy_plaintext_found:
        SecretSerializer.legacy_plaintext_found = False

        need_save = True

        logger.info("已将明文保存的登录凭据与访问令牌转为加密存储")

    if need_save:
        config.save()

def check_need_patch():
    # 检查是否需要修补配置文件
    if config_path.exists():
        with open(config_path, "r", encoding = "utf-8") as f:
            try:
                data = loads(f.read())

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

    if config_version < 2200:
        # 命名规则的内置默认值在本版本连着变过两次：先是改用 <> 可选段（段内变量取
        # 空值时整段连同字面量前后缀一并丢弃 —— 个人空间、收藏夹这几类里单P与多P
        # 混在一起，旧写法只能顾及一种形态，多P视频会丢掉稿件标题，GitHub #461），
        # 随后又把入口标签从 {parent_title} 拆进了 {source_title}（此前这个变量
        # 兼着「来源列表入口标签」与「稿件标题」两种含义）。
        #
        # 这里不再维护「旧默认值」对照表逐条比对、只替换用户没改过的那几条 ——
        # 命名规则是用户可见、随时可改的东西，留一条已经用错变量的旧规则在配置里，
        # 出问题时比「规则没了」更难排查。整张表换成新默认值：用户自建的规则与
        # 改过的内置规则一并舍弃，置一个标志由主窗口起来后提示他重新设置
        config.set(config.naming_rule_list, deepcopy(DefaultValue.naming_rule_list))

        runtime.naming.rules_reset = True

        logger.info("命名规则已重置为内置默认值")

        # 默认海外 CDN 列表中移除了 Akamai（upos-hz-mirrorakam.akamaized.net）：
        # 它不能作为替换目标 —— 把别的 host 的签名链接改写过去一律返回 403，与出口
        # 地区无关（成因详见 DefaultValue.ov_cdn_server_list 上的那段说明）。
        # 老配置里原样继承下来的那条留着，只会让每次海外解析都白占一个并发探测位
        #
        # 只按 host 精确匹配剔除这一条。用户自行增删或改过的其他节点一律不动 ——
        # 这份列表在设置界面里可编辑，不能假设它还是默认值
        ov_cdn_server_list = deepcopy(config.get(config.ov_cdn_server_list))

        filtered_list = [
            entry for entry in ov_cdn_server_list
            if entry.get("host") != "upos-hz-mirrorakam.akamaized.net"
        ]

        if len(filtered_list) != len(ov_cdn_server_list):
            config.set(config.ov_cdn_server_list, filtered_list)

            logger.info("已从海外 CDN 服务器列表中移除 Akamai")

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

restrict_permission(config_path)
settle_secrets()

# 判断是否需要修补配置文件
need_patch, config_version, data = check_need_patch()

if need_patch:
    logger.info("检测到旧版本配置文件，正在进行修补")

    patch_config(config_version, data)
