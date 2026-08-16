from ...common.config import config
from ...common.signal_bus import signal_bus

from ..invoke import call_in_main_thread

from . import text_result, error_result
from .parse import get_parse_interface, build_item_index, _media_info_error

from threading import Event
import logging

logger = logging.getLogger(__name__)

MAX_EPISODES_PER_CALL = 200

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

def tool_create_download(arguments: dict) -> dict:
    episode_ids = arguments.get("episode_ids")

    if not isinstance(episode_ids, list) or not episode_ids:
        return error_result("The 'episode_ids' argument must be a non-empty array of episode_id strings.")

    if not all(isinstance(item, str) for item in episode_ids):
        return error_result("Every entry in 'episode_ids' must be a string.")

    if len(episode_ids) > MAX_EPISODES_PER_CALL:
        return error_result(
            f"Too many episodes in one call ({len(episode_ids)}); the limit is {MAX_EPISODES_PER_CALL}."
        )

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

        signal_bus.download.create_task.emit(found, True)

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

    return text_result(summary, {"created": len(tasks), "tasks": tasks, "notes": notes})

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
            "first, then pass the episode_id values you want. Downloads use the quality, format "
            "and output folder configured in the application."
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
