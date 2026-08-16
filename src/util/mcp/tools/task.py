from ...common.config import config

from ..invoke import call_in_main_thread

from . import text_result, error_result

import logging
import os

logger = logging.getLogger(__name__)

def _status_name(value: int) -> str:
    from ...common.enum import DownloadStatus

    try:
        return DownloadStatus(value).name.lower()

    except ValueError:
        return f"unknown({value})"

def _task_to_dict(task_info, verbose: bool = False) -> dict:
    data = {
        "task_id": task_info.Basic.task_id,
        "title": task_info.Basic.show_title,
        "status": _status_name(task_info.Download.status),
        "progress": task_info.Download.progress,
    }

    if task_info.Download.total_size:
        data["total_size"] = task_info.Download.total_size
        data["downloaded_size"] = task_info.Download.downloaded_size

    if task_info.Download.speed:
        data["speed"] = task_info.Download.speed

    if verbose:
        data["created_time"] = task_info.Basic.created_time
        data["completed_time"] = task_info.Basic.completed_time

        if task_info.File.name:
            # 不建子文件夹时 folder 是 "."，直接 join 会拼出 "Downloads\.\xxx"；
            # download_path 又是正斜杠，join 后分隔符混用。normpath 一并收拾干净，
            # 免得把这种路径喂给模型后它再原样传回来
            data["file_path"] = os.path.normpath(os.path.join(
                task_info.File.download_path,
                task_info.File.folder,
                task_info.File.name,
            ))

        if task_info.Episode.video_quality:
            data["video_quality"] = task_info.Episode.video_quality

        if task_info.Episode.audio_quality:
            data["audio_quality"] = task_info.Episode.audio_quality

    return data

def _query_tasks(completed: bool):
    """
    读取任务列表

    正在下载的任务，其进度是高频写入、异步落盘的，数据库里的快照会滞后。
    downloader_manager 持有的 TaskInfo 才是实时的，因此优先取内存中的那份。
    """
    from ...download.downloader.manager import downloader_manager
    from ...download.task.manager import task_manager

    task_info_list = task_manager.query(completed)

    result = []

    for task_info in task_info_list:
        live = downloader_manager.downloaders.get(task_info.Basic.task_id)

        result.append(live.task_info if live is not None else task_info)

    return result

def _find_task(task_id: str):
    from ...download.downloader.manager import downloader_manager

    if live := downloader_manager.downloaders.get(task_id):
        return live.task_info

    for completed in (False, True):
        for task_info in _query_tasks(completed):
            if task_info.Basic.task_id == task_id:
                return task_info

    return None

def tool_list_tasks(arguments: dict) -> dict:
    state = arguments.get("state", "downloading")

    if state not in ("downloading", "completed", "all"):
        return error_result("The 'state' argument must be one of: downloading, completed, all.")

    def collect():
        tasks = []

        if state in ("downloading", "all"):
            tasks += [_task_to_dict(t) for t in _query_tasks(False)]

        if state in ("completed", "all"):
            tasks += [_task_to_dict(t) for t in _query_tasks(True)]

        return tasks

    tasks = call_in_main_thread(collect, timeout = 20.0)

    return text_result(f"{len(tasks)} task(s).", {"count": len(tasks), "tasks": tasks})

def tool_get_task_status(arguments: dict) -> dict:
    task_id = (arguments.get("task_id") or "").strip()

    if not task_id:
        return error_result("The 'task_id' argument is required.")

    task_info = call_in_main_thread(_find_task, task_id, timeout = 20.0)

    if task_info is None:
        return error_result(f"No task found with id '{task_id}'. Use list_tasks to see current tasks.")

    return text_result("", _task_to_dict(task_info, verbose = True))

def tool_get_login_status(arguments: dict) -> dict:
    def collect():
        return {
            "logged_in": bool(config.get(config.is_login)),
            "username": config.user_uname,
            "uid": config.user_uid,
            "session_expired": bool(config.is_expired),
        }

    info = call_in_main_thread(collect, timeout = 5.0)

    if not info["logged_in"]:
        summary = "Not logged in. Members-only content and high quality streams are unavailable."

    elif info["session_expired"]:
        summary = "The saved login session has expired; the user needs to sign in again."

    else:
        summary = f"Logged in as {info['username']}."

    return text_result(summary, info)

def register(registry):
    registry.register(
        name = "list_tasks",
        title = "List Download Tasks",
        description = "List download tasks with their current status and progress.",
        input_schema = {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["downloading", "completed", "all"],
                    "description": "Which tasks to list. Defaults to 'downloading'.",
                },
            },
            "additionalProperties": False,
        },
        handler = tool_list_tasks,
    )

    registry.register(
        name = "get_task_status",
        title = "Get Download Task Status",
        description = "Get detailed status for a single download task, including its output file path.",
        input_schema = {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task_id returned by list_tasks or create_download.",
                },
            },
            "required": ["task_id"],
            "additionalProperties": False,
        },
        handler = tool_get_task_status,
    )

    registry.register(
        name = "get_login_status",
        title = "Get Login Status",
        description = (
            "Check whether the user is signed in to Bilibili. Members-only content and the "
            "highest quality streams require a valid login."
        ),
        input_schema = {"type": "object", "additionalProperties": False},
        handler = tool_get_login_status,
    )
