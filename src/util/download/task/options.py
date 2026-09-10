from ...common.enum import DanmakuType, SubtitleType, CoverType, MetadataType, VideoContainer
from ...common.config import config, Item

from copy import deepcopy
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# 可固化的下载选项 → 对应的枚举类型，None 表示取值原样存取（布尔、字典）。
#
# 键名与 config 中同名的配置项一一对应，回落时据此取全局设置，
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

    # 目标命名规则的 id（naming_rule_list 里的 uuid 字符串），None 表示按媒体类型取默认规则。
    #
    # **它必须固化**：`TaskManager.__update_file_name_info()` 在下载真正开始时还会被
    # 调用第二次（`_update_media_info()` 补齐画质变量之后重算文件名），那一刻本次下载的
    # options 早就不在了。不固化就只能去读进程级的 `config.target_naming_rule_id`，
    # 而用户只要重新解析一条链接，`previewer.py` 的 clear_cache 就把它清成 None ——
    # 表现是**下载列表里显示的文件名与磁盘上真正的文件名不一样**，且毫无提示
    "target_naming_rule_id": None,
}

# 只在 options 里过一趟、不进任务快照的键
#
# 它们在建任务当场就被消费掉了：下载目录落进 `TaskInfo.File.download_path`，
# 编号物化成 `TaskInfo.Episode.number`，重复处理方式当场判完即弃。
# 再往 Options 里存一份就是第二个真相源，迟早与正主分叉
_TRANSIENT_KEYS = frozenset({
    "download_path",
    "duplicate_resolution",
    "numbering_type",
    "numbering_batch_id",
    "starting_number",
})

def pick_option(options: dict, key: str, fallback):
    """
    取本次任务指定的下载选项，未指定时回落到给定的默认值

    用 is not None 而不是真值判断，否则显式传入的 False 会被当成未指定。
    """
    if options is not None and options.get(key) is not None:
        return options[key]

    return fallback

def pick_enum(options: dict, key: str, fallback, enum_cls):
    """
    取一个枚举型选项，允许调用方传枚举的 value —— HTTP / JSON 过来的就是它

    **不能把 `pick_option` 的结果直接丢进 match**：`NumberingType` 这类是普通 `Enum`
    不是 `IntEnum`，JSON 里的 `0` 与 `NumberingType.FROM_SPECIFIED` **既不相等也不报错**，
    会一声不响地落到 `case _` 上（与 CLAUDE.md 里 `Qt.CheckState` 那条同一个陷阱）。

    认不出来时回落给定的默认值并记一条日志，不抛 —— 与本模块「纠正而非拒绝」的语义一致
    """
    value = pick_option(options, key, fallback)

    if isinstance(value, enum_cls):
        return value

    try:
        return enum_cls(value)

    except (ValueError, KeyError):
        logger.warning("下载选项 %s 的取值 %r 无法识别，已改用 %r", key, value, fallback)

        return fallback

def _global_value(key: str):
    item = getattr(config, key)

    # config 里混着两类状态：持久化项要经 get() 取值，纯运行时状态
    # （keep_original_files_type 等）本身就是普通类属性，直接用。
    #
    # 这里的键是从 _OPTION_SPEC 动态取的，grep 字段名搜不到这些读取点 ——
    # 换掉配置项的实现类型时**必须同步改这一行**，否则所有下载选项会静默走错分支
    return config.get(item) if isinstance(item, Item) else item

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
