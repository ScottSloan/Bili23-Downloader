from ...common.enum import DanmakuType, SubtitleType, CoverType, MetadataType, VideoContainer
from ...common.config import config

from qfluentwidgets import ConfigItem

from copy import deepcopy
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# 可固化的下载选项 → 对应的枚举类型，None 表示取值原样存取（布尔、字典）。
#
# 键名与 APPConfig 中同名的 ConfigItem 一一对应，回落时据此取全局设置，
# 因此增删选项时两边的名字必须保持一致。
_OPTION_SPEC = {
    "video_container": VideoContainer,

    "danmaku_type": DanmakuType,
    "embed_danmaku": None,
    "delete_danmaku_after_embed": None,

    "subtitle_type": SubtitleType,
    "embed_subtitle": None,
    "delete_subtitle_after_embed": None,
    "subtitle_language": None,

    "cover_type": CoverType,
    "attach_cover": None,
    "delete_cover_after_attach": None,

    "metadata_type": MetadataType,

    "m4a_to_mp3": None,

    # 保留原始文件时保留哪一路流。它的两个同伴 merge_video_audio 与
    # keep_original_files 早就固化在 DownloadInfo 里了，唯独它一直是在合并阶段
    # 才去读全局状态，放在这里是为了沿用「缺失即回落全局设置」的兼容处理
    "keep_original_files_type": None,
}

def pick_option(options: dict, key: str, fallback):
    """
    取本次任务指定的下载选项，未指定时回落到给定的默认值

    用 is not None 而不是真值判断，否则显式传入的 False 会被当成未指定。
    """
    if options is not None and options.get(key) is not None:
        return options[key]

    return fallback

def _global_value(key: str):
    item = getattr(config, key)

    # config 里混着两类状态：持久化项要经 get() 取值，纯运行时状态
    # （keep_original_files_type 等）本身就是普通类属性，直接用
    return config.get(item) if isinstance(item, ConfigItem) else item

def snapshot(overrides: dict = None) -> dict:
    """
    把当前的全局设置固化成一份快照，overrides 中指定的项优先

    在生成 TaskInfo 时调用。任务此后一律读这份快照，用户中途改设置不会再
    波及队列里已经排好的任务，与 download_path 的处理保持一致。
    """
    data = {}

    for key in _OPTION_SPEC:
        value = pick_option(overrides, key, _global_value(key))

        if isinstance(value, Enum):
            # 枚举存 value，保证 task.db 里那一列始终是可序列化的 JSON
            data[key] = value.value

        else:
            # subtitle_language 这类字典项，config.get() 返回的是配置里的那一个
            # 对象本身（设置界面也因此要先 .copy() 再改）。不深拷贝的话固化下来的
            # 只是引用，用户之后改设置会连同已建任务的快照一起改掉
            data[key] = deepcopy(value)

    return data

def resolve(task_info, key: str):
    """
    读取任务的下载选项，未固化时回落到全局设置

    旧版本创建的任务没有 Options 这一组，各项都是 None，此时的行为与
    升级前完全一致 —— 仍旧读用户当前的全局设置。
    """
    enum_cls = _OPTION_SPEC[key]

    value = getattr(task_info.Options, key, None)

    if value is None:
        return _global_value(key)

    if enum_cls is None:
        return value

    try:
        return enum_cls(value)

    except ValueError:
        # 降级用的枚举成员被改名或删除时不该让整个下载失败，退回全局设置
        logger.warning("任务中的下载选项 %s 取值 %r 无法识别，已改用全局设置", key, value)

        return _global_value(key)
