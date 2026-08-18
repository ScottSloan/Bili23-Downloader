from ...common.data import video_quality_map, audio_quality_map, video_codec_map
from ...common.enum import (
    DuplicateDownloadResolution, DanmakuType, SubtitleType, CoverType, MetadataType, VideoContainer
)
from ...common.config import config
from ...download.task.options import pick_option
from ...common.signal_bus import signal_bus

from ..invoke import call_in_main_thread

from . import text_result, error_result
from .parse import get_parse_interface, build_item_index, _media_info_error

from threading import Event, Lock
import logging

logger = logging.getLogger(__name__)

MAX_EPISODES_PER_CALL = 200

def _fold(value: str) -> str:
    # 模型不会严格照抄枚举值的写法（hi_res / Hi-Res / HIRES 都会出现），
    # 归一化后再比对，避免因为一个下划线就报错
    return value.strip().upper().replace(" ", "").replace("-", "").replace("_", "")

def _build_lookup(table: dict, extra: dict = None) -> dict:
    lookup = {_fold(name): value for name, value in table.items()}

    if extra:
        lookup.update({_fold(name): value for name, value in extra.items()})

    return lookup

# 编解码器的正式名称带斜杠（"AVC/H.264"），模型多半只写其中一半，两种都认
_VIDEO_QUALITY_LOOKUP = _build_lookup(video_quality_map)
_AUDIO_QUALITY_LOOKUP = _build_lookup(audio_quality_map)
_VIDEO_CODEC_LOOKUP = _build_lookup(video_codec_map, {
    "AVC": 7, "H.264": 7,
    "HEVC": 12, "H.265": 12,
    "AV1": 13,
})

# 只下音频（听歌、做转录）是常见诉求，因此把媒体流的取舍也开放出来
_MEDIA_LOOKUP = {
    "video+audio": (True, True),
    "video": (True, False),
    "audio": (False, True),
}

# 模型可见的名字 → TaskManager 认识的键。这层映射同时也是白名单：
# 下载线程数、下载目录、命名规则等不在其中，模型无从触及
_FLAG_OPTIONS = {
    "danmaku": "download_danmaku",
    "subtitle": "download_subtitle",
    "cover": "download_cover",
    "metadata": "download_metadata",
    "chapter": "embed_chapter",

    "embed_danmaku": "embed_danmaku",
    "embed_subtitle": "embed_subtitle",
    "attach_cover": "attach_cover",
}

# 附加文件的格式与输出容器。值直接用枚举的 value，模型看到的就是文件扩展名
_ENUM_OPTIONS = {
    "danmaku_format": ("danmaku_type", DanmakuType),
    "subtitle_format": ("subtitle_type", SubtitleType),
    "cover_format": ("cover_type", CoverType),
    "metadata_format": ("metadata_type", MetadataType),
    "container": ("video_container", VideoContainer),
}

_OPTION_CHOICES = {
    "video_quality": list(video_quality_map),
    "audio_quality": list(audio_quality_map),
    "video_codec": list(video_codec_map),
}

def _normalize_options(raw):
    """
    把面向模型的选项翻译成 TaskManager 的 options

    返回 (options, 错误信息)。取值写错时直接报错而不是静默忽略 —— 模型以为
    自己下的是 4K，实际拿到默认画质，它没有任何办法发现这件事。
    """
    if raw is None:
        return None, None

    if not isinstance(raw, dict):
        return None, "The 'options' argument must be an object."

    options = {}

    for name, lookup, key in (
        ("video_quality", _VIDEO_QUALITY_LOOKUP, "video_quality_id"),
        ("audio_quality", _AUDIO_QUALITY_LOOKUP, "audio_quality_id"),
        ("video_codec", _VIDEO_CODEC_LOOKUP, "video_codec_id"),
    ):
        value = raw.get(name)

        if value is None:
            continue

        if not isinstance(value, str):
            return None, f"'{name}' must be a string."

        resolved = lookup.get(_fold(value))

        if resolved is None:
            return None, (
                f"'{value}' is not a valid {name}. Valid values are: "
                + ", ".join(_OPTION_CHOICES[name]) + "."
            )

        options[key] = resolved

    for name, key in _FLAG_OPTIONS.items():
        value = raw.get(name)

        if value is None:
            continue

        if not isinstance(value, bool):
            return None, f"'{name}' must be a boolean."

        options[key] = value

    media = raw.get("media")

    if media is not None:
        if not isinstance(media, str) or media.strip().lower() not in _MEDIA_LOOKUP:
            return None, (
                "'media' must be one of: " + ", ".join(_MEDIA_LOOKUP) + "."
            )

        video, audio = _MEDIA_LOOKUP[media.strip().lower()]

        options["download_video_stream"] = video
        options["download_audio_stream"] = audio

    for name, (key, enum_cls) in _ENUM_OPTIONS.items():
        value = raw.get(name)

        if value is None:
            continue

        if not isinstance(value, str):
            return None, f"'{name}' must be a string."

        lookup = {_fold(member.value): member for member in enum_cls}

        resolved = lookup.get(_fold(value))

        if resolved is None:
            return None, (
                f"'{value}' is not a valid {name}. Valid values are: "
                + ", ".join(member.value for member in enum_cls) + "."
            )

        options[key] = resolved

    languages = raw.get("subtitle_languages")

    if languages is not None:
        if not isinstance(languages, list) or not all(isinstance(item, str) for item in languages):
            return None, "'subtitle_languages' must be an array of language code strings."

        # 空数组表示不作限制，与设置界面「下载全部语言」是同一个含义
        options["subtitle_language"] = {
            "download_specified": bool(languages),
            "specified_language": list(languages),
        }

    if error := _embed_conflict(options):
        return None, error

    return (options or None), None

def _embed_conflict(options: dict):
    """
    嵌入弹幕 / 字幕的前提是否成立，不成立时给出具体原因

    嵌入有三个前提，任何一个不满足，程序都只会静默跳过（见 danmaku.py 的
    _check_embed_danmaku 与 base.py 的 is_embed_available）：字幕轨必须是 ASS、
    输出容器必须是 MKV、而且得真的走一遍合并（只下音频时没有合并步骤）。

    不检查的话，模型开了嵌入开关就会以为嵌进去了，实际什么都没发生，
    它也没有任何途径能发现。这里提前拦下并说清缺的是哪一条。
    """
    for switch, format_key, ass_member, label in (
        ("embed_danmaku", "danmaku_type", DanmakuType.ASS, "danmaku"),
        ("embed_subtitle", "subtitle_type", SubtitleType.ASS, "subtitle"),
    ):
        if not options.get(switch):
            continue

        # 没指定的项按用户当前的设置算，本来就设成 ASS + MKV 时不该报错
        file_format = pick_option(options, format_key, config.get(getattr(config, format_key)))
        container = pick_option(options, "video_container", config.get(config.video_container))

        missing = []

        if file_format != ass_member:
            missing.append(f"{label}_format must be 'ass' (currently '{file_format.value}')")

        if container != VideoContainer.MKV:
            missing.append(f"container must be 'mkv' (currently '{container.value}')")

        # 只下音频时不存在合并步骤，没有容器可供嵌入
        if options.get("download_video_stream") is False:
            missing.append("media must include video")

        if missing:
            return (
                f"Cannot embed the {label}: " + "; ".join(missing) + ". "
                f"Either set those options too, or drop embed_{label} and the {label} "
                "will be saved as a separate file."
            )

    return None

def _collect_episode_info(episode_ids: list):
    """
    按 episode_id 从解析树取出条目数据

    返回 (待下载的 dict 列表, 未找到的 id 列表, 需要二次解析的 id 列表)
    """
    from ...parse.episode.tree import Attribute

    interface = get_parse_interface()

    if interface is None:
        return None, [], []

    # 必须与 parse 侧用同一套编号，否则模型拿到的 id 在这里对不上号
    index = build_item_index(interface.parse_list.get_all_items())

    found = []
    found_ids = []
    missing = []
    needs_reparse = []

    for episode_id in episode_ids:
        item = index.get(episode_id)

        if item is None:
            missing.append(episode_id)

            continue

        # 这类条目（收藏夹、个人空间里的视频）还没有 cid，直接建任务会失败
        if item.attribute & Attribute.NEED_PARSE_BIT:
            needs_reparse.append(episode_id)

            continue

        found.append(item.to_dict())
        found_ids.append(episode_id)

    return found, found_ids, missing, needs_reparse

def _split_duplicates(found: list, found_ids: list):
    """
    分出已经下载过的条目

    返回 (待下载的条目, 对应的 id, 重复条目的标题)。查库在当前线程完成：
    每个线程各持有自己的 SQLite 连接，且这里只读不写
    """
    from ...download.task.manager import task_manager

    fresh = []
    fresh_ids = []
    duplicates = []

    for episode, episode_id in zip(found, found_ids):
        try:
            if task_manager.is_duplicate(episode):
                duplicates.append(episode.get("title", ""))

                continue

        except Exception:
            # 查库失败时按未重复处理，后面 TaskManager 还会再判一次，
            # 顶多是多走一遍流程，总好过把能下的条目挡在门外
            logger.exception("预检重复下载失败：%s", episode.get("title", ""))

        fresh.append(episode)
        fresh_ids.append(episode_id)

    return fresh, fresh_ids, duplicates

# 创建任务同样要互斥：中途会改 config.current_starting_number 这个全局编号，
# 并且依赖"解析列表此刻的内容"，两个请求交叠会算错序号、取错条目
_create_lock = Lock()

def tool_create_download(arguments: dict) -> dict:
    if not _create_lock.acquire(timeout = 5.0):
        return error_result("Another download request is being processed. Retry shortly.")

    try:
        return _create_download_locked(arguments)

    finally:
        _create_lock.release()

def _create_download_locked(arguments: dict) -> dict:
    episode_ids = arguments.get("episode_ids")

    if not isinstance(episode_ids, list) or not episode_ids:
        return error_result("The 'episode_ids' argument must be a non-empty array of episode_id strings.")

    if not all(isinstance(item, str) for item in episode_ids):
        return error_result("Every entry in 'episode_ids' must be a string.")

    if len(episode_ids) > MAX_EPISODES_PER_CALL:
        return error_result(
            f"Too many episodes in one call ({len(episode_ids)}); the limit is {MAX_EPISODES_PER_CALL}."
        )

    options, option_error = _normalize_options(arguments.get("options"))

    if option_error:
        return error_result(option_error)

    redownload = arguments.get("redownload")

    if redownload is not None and not isinstance(redownload, bool):
        return error_result("The 'redownload' argument must be a boolean.")

    # 先校验 id 再看媒体信息：传错 id 却收到"媒体信息不可用"会把模型引向
    # 完全无关的方向，它会去重新解析而不是纠正 id
    found, found_ids, missing, needs_reparse = call_in_main_thread(
        _collect_episode_info, episode_ids, timeout = 15.0
    )

    if found is None:
        return error_result("The parse list is unavailable. Call parse_url first.")

    if not found:
        detail = []

        if missing:
            detail.append(f"{len(missing)} id(s) were not found in the parse list")

        if needs_reparse:
            detail.append(f"{len(needs_reparse)} id(s) need to be parsed individually first")

        return error_result(
            "No downloadable episodes matched. " + ("; ".join(detail) + "." if detail else
            "Call get_episodes to see the available episode_id values.")
        )

    if reason := call_in_main_thread(_media_info_error, timeout = 5.0):
        return error_result(
            f"Cannot start a download: {reason}. Try parsing the link again; if it keeps "
            "failing, the content may require a login or be region-restricted."
        )

    # 重复下载必须在这里就地决定，不能交给 TaskManager 按用户设置处理：
    # 那边的 ALWAYS_ASK 会弹窗并无限等待用户点击，而这条链路上没有人在看着。
    # 显式指定后，即便预检与实际创建之间又有任务入库，也不会弹窗
    options = dict(options or {})
    options["duplicate_resolution"] = (
        DuplicateDownloadResolution.CONTINUE if redownload else DuplicateDownloadResolution.SKIP
    )

    duplicates = []

    if not redownload:
        # 自己先查一遍，而不是让 TaskManager 静默跳过：被它跳过的条目不会出现在
        # add_to_downloading_list 里，全部重复时这里只能干等到 60s 超时，
        # 且无从告诉模型是哪几条重复了
        found, found_ids, duplicates = _split_duplicates(found, found_ids)

        if not found:
            return text_result(
                f"Nothing to download: all {len(duplicates)} episode(s) have already been "
                "downloaded. Duplicates are matched by video id alone, so quality and format "
                "are not taken into account. Pass redownload=true to download them again.",
                {"created": 0, "duplicates": duplicates},
            )

    created = {}
    done = Event()

    def on_added(task_info_list):
        created["tasks"] = [
            {"task_id": t.Basic.task_id, "title": t.Basic.show_title}
            for t in task_info_list
        ]
        done.set()

    def start():
        from PySide6.QtCore import QTimer

        # 界面上的"已下载"角标。放在这里而不是校验阶段：校验之后仍可能因为
        # 媒体信息缺失而不创建任何任务，那时标记就是假的。
        #
        # 按位置 id 精确标记，不能拿 item.episode_id 去比对：同一视频的分P
        # 共享那个值，只下了第 3P 也会把 10 个分P 全标成已下载
        if interface := get_parse_interface():
            index = build_item_index(interface.parse_list.get_all_items())

            for item_id in found_ids:
                if item := index.get(item_id):
                    item.downloaded = True

        # 起始编号跟着界面的下载入口走，否则文件名里的序号会从上次的位置续下去
        config.current_starting_number = 1

        signal_bus.download.create_task.emit(found, True, options)

        # 与界面的下载入口保持一致：上面改了 item.downloaded，要发一次刷新，
        # 否则"已下载"角标要等用户下次操作才重绘。只发重绘信号，不动勾选数据
        if interface is not None:
            QTimer.singleShot(0, interface.parse_list.update_check_state)

    call_in_main_thread(signal_bus.download.add_to_downloading_list.connect, on_added, timeout = 5.0)

    try:
        call_in_main_thread(start, timeout = 10.0)

        # 任务创建跑在线程池上，还可能被重复下载确认对话框挡住，因此给足时间
        finished = done.wait(60.0)

    finally:
        try:
            call_in_main_thread(
                signal_bus.download.add_to_downloading_list.disconnect, on_added, timeout = 5.0
            )

        except Exception:
            logger.exception("断开下载任务创建信号失败")

    notes = []

    if missing:
        notes.append(f"{len(missing)} id(s) were not found: {', '.join(missing[:5])}")

    if needs_reparse:
        notes.append(f"{len(needs_reparse)} id(s) need to be parsed individually before downloading")

    if duplicates:
        notes.append(
            f"{len(duplicates)} episode(s) were skipped as already downloaded "
            "(pass redownload=true to download them again)"
        )

    if not finished:
        # 全部被判为重复下载时不会有任务入队，信号也就不会发出
        return text_result(
            "Submitted, but no new task was confirmed within 60s. The episodes may already have "
            "been downloaded, or a confirmation dialog may be waiting for the user. "
            "Use list_tasks to check.",
            {"submitted": len(found), "notes": notes},
        )

    tasks = created.get("tasks", [])

    summary = f"Created {len(tasks)} download task(s)."

    if notes:
        summary += " " + "; ".join(notes) + "."

    structured = {"created": len(tasks), "tasks": tasks, "notes": notes}

    if duplicates:
        structured["duplicates"] = duplicates

    return text_result(summary, structured)

def _get_downloading_model():
    """
    取下载界面「正在下载」列表的 model

    控制任务一律经它转发，而不是直接去动 Downloader：界面的
    togglePauseResume / cancelDownload 里还带着并发调度、界面行刷新、
    正在下载时先停分片线程再删文件等一串副作用，绕过去就会出现
    "任务停了但排队的任务不顶上""取消后临时文件残留" 这类问题
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    window = getattr(app, "window", None)

    if window is None:
        return None

    interface = getattr(window, "download_interface", None)

    if interface is None:
        return None

    return interface.downloading_list_view._model

def _control_task(task_id: str, action: str):
    """
    对单个任务执行暂停 / 继续 / 取消

    必须在 GUI 线程调用：Downloader 持有 QTimer 与线程池对象
    """
    from ...download.downloader.manager import downloader_manager
    from ...common.enum import DownloadStatus

    downloader = downloader_manager.downloaders.get(task_id)

    if downloader is None:
        return f"No active task with id '{task_id}'. Only tasks that are still in the download queue can be controlled."

    model = _get_downloading_model()

    if model is None:
        return "The download interface is not ready yet."

    task_info = downloader.task_info

    status = task_info.Download.status

    match action:
        case "pause":
            if status != DownloadStatus.DOWNLOADING:
                return f"Task is not downloading (current status: {DownloadStatus(status).name.lower()})."

            model.togglePauseResume(task_info)

        case "resume":
            if status != DownloadStatus.PAUSED:
                return f"Task is not paused (current status: {DownloadStatus(status).name.lower()})."

            model.togglePauseResume(task_info)

        case "cancel":
            # 合并 / 转换中的任务界面上不允许取消，这里保持一致；
            # 其余状态交给 cancelDownload，由它决定是否要先等分片线程停下
            if status in (DownloadStatus.MERGING, DownloadStatus.CONVERTING):
                return "Task is being merged or converted and cannot be cancelled. Wait for it to finish."

            model.cancelDownload(task_info)

    return None

# 回执文案里的过去式。不要退回成 f"{action}d" 那种拼接：
# 那样 cancel 会变成 "canceld"，拼错的英文会削弱模型对结果的理解
_ACTION_DONE = {
    "pause": "paused",
    "resume": "resumed",
    "cancel": "cancelled",
}

def _make_control_handler(action: str):
    def handler(arguments: dict) -> dict:
        task_id = (arguments.get("task_id") or "").strip()

        if not task_id:
            return error_result("The 'task_id' argument is required.")

        if reason := call_in_main_thread(_control_task, task_id, action, timeout = 20.0):
            return error_result(reason)

        return text_result(
            f"Task {task_id} {_ACTION_DONE[action]}.", {"task_id": task_id, "action": action}
        )

    return handler

_TASK_ID_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "The task_id returned by list_tasks or create_download.",
        },
    },
    "required": ["task_id"],
    "additionalProperties": False,
}

def register(registry):
    registry.register(
        name = "create_download",
        title = "Create Download Tasks",
        description = (
            "Create download tasks for episodes currently in the parse list. Call parse_url "
            "first, then pass the episode_id values you want. Anything left out of 'options' "
            "follows the user's own settings, and 'options' applies only to the tasks created "
            "by this call. The output folder and file naming are always the user's and cannot "
            "be changed here. Episodes that were already downloaded are skipped unless "
            "redownload is set."
        ),
        input_schema = {
            "type": "object",
            "properties": {
                "episode_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "episode_id values from parse_url or get_episodes.",
                    "minItems": 1,
                    "maxItems": MAX_EPISODES_PER_CALL,
                },
                "options": {
                    "type": "object",
                    "description": (
                        "Per-task download settings. Omitted fields follow the user's settings. "
                        "Check the 'available' field from parse_url first: requesting a quality "
                        "the content does not offer silently falls back to the closest available "
                        "one, so the download will not match what was asked for."
                    ),
                    "properties": {
                        "video_quality": {
                            "type": "string",
                            "enum": _OPTION_CHOICES["video_quality"],
                            "description": "Video quality; 'auto' follows the user's priority list.",
                        },
                        "audio_quality": {
                            "type": "string",
                            "enum": _OPTION_CHOICES["audio_quality"],
                            "description": "Audio quality; 'auto' follows the user's priority list.",
                        },
                        "video_codec": {
                            "type": "string",
                            "enum": _OPTION_CHOICES["video_codec"],
                            "description": "Video codec; 'auto' follows the user's priority list.",
                        },
                        "media": {
                            "type": "string",
                            "enum": list(_MEDIA_LOOKUP),
                            "description": "Which streams to download. Use 'audio' for audio-only.",
                        },
                        "container": {
                            "type": "string",
                            "enum": [member.value for member in VideoContainer],
                            "description": "Output container for the merged file.",
                        },
                        "danmaku": {"type": "boolean", "description": "Download the danmaku (bullet comments) file."},
                        "danmaku_format": {
                            "type": "string",
                            "enum": [member.value for member in DanmakuType],
                            "description": "Format of the danmaku file.",
                        },
                        "embed_danmaku": {
                            "type": "boolean",
                            "description": (
                                "Embed the danmaku into the video as a subtitle track. Requires "
                                "danmaku_format 'ass' and container 'mkv'."
                            ),
                        },
                        "subtitle": {"type": "boolean", "description": "Download the subtitle file."},
                        "subtitle_format": {
                            "type": "string",
                            "enum": [member.value for member in SubtitleType],
                            "description": "Format of the subtitle file.",
                        },
                        "subtitle_languages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Only download subtitles in these languages, using Bilibili's own "
                                "codes (zh-CN, zh-Hant, en-US, ai-zh ...). An empty array downloads "
                                "every available language. Codes the video does not provide simply "
                                "yield no subtitle file."
                            ),
                        },
                        "embed_subtitle": {
                            "type": "boolean",
                            "description": (
                                "Embed the subtitle into the video as a subtitle track. Requires "
                                "subtitle_format 'ass' and container 'mkv'."
                            ),
                        },
                        "cover": {"type": "boolean", "description": "Download the cover image."},
                        "cover_format": {
                            "type": "string",
                            "enum": [member.value for member in CoverType],
                            "description": "Format of the cover image file.",
                        },
                        "attach_cover": {
                            "type": "boolean",
                            "description": "Attach the cover to the output file as embedded artwork.",
                        },
                        "metadata": {"type": "boolean", "description": "Write a metadata file."},
                        "metadata_format": {
                            "type": "string",
                            "enum": [member.value for member in MetadataType],
                            "description": "Format of the metadata file.",
                        },
                        "chapter": {"type": "boolean", "description": "Embed chapter markers into the output file."},
                    },
                    "additionalProperties": False,
                },
                "redownload": {
                    "type": "boolean",
                    "description": (
                        "Download episodes even if they were downloaded before. Duplicates are "
                        "matched by video id alone, so an episode already downloaded at a "
                        "different quality still counts as a duplicate; set this to download it "
                        "again at another quality."
                    ),
                },
            },
            "required": ["episode_ids"],
            "additionalProperties": False,
        },
        handler = tool_create_download,
        requires_download = True,
    )

    for action, title, description in (
        ("pause", "Pause Download", "Pause a download task that is currently downloading."),
        ("resume", "Resume Download", "Resume a paused download task."),
        ("cancel", "Cancel Download", "Cancel a download task and remove it from the queue. Partial files are deleted. A task that is already merging or converting cannot be cancelled."),
    ):
        registry.register(
            name = f"{action}_task",
            title = title,
            description = description,
            input_schema = _TASK_ID_SCHEMA,
            handler = _make_control_handler(action),
            requires_download = True,
        )
