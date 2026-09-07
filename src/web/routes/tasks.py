"""
下载任务的增删改查与排序（S3-11）

全部经由 `task_manager` —— **不要绕过它直接写 task.db**。CLAUDE.md 里那条纪律
（所有写入都走那唯一的 `task-db` 执行线程）对服务端同样成立：绕过去的话，
高频进度更新与结构性写入会乱序，重启后看到的是倒退的进度。

快照接口在 `routes/events.py`（`GET /api/tasks`），那边负责「一次拿全」；
这里负责改动，改完由 signal_bus 上的事件推给前端（S3-9 的链路）。

## 排序在这一层做

桌面版的排序长在 Qt 模型里。服务端没有模型，就地排一遍即可 ——
任务数是几十到几百的量级，不值得为它建索引。**排序键必须与桌面一致**，
否则同一批任务在两边的顺序不同，用户会以为少了什么。
"""

from typing import List, Literal, Optional
import asyncio
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.common.enum import DownloadStatus
from util.download.task.manager import task_manager
from util.thread import background

from ..download.view import task_views

from ..schemas import (
    CreateResult, DeleteResult, PauseResult, RetryResult, TaskCount, TaskList, TaskView,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["tasks"])

# 可用的排序键 → TaskInfo 上的取值方式。与桌面版下载列表的排序选项对应
SORT_KEYS = {
    "created_time": lambda task: task.Basic.created_time,
    "completed_time": lambda task: task.Basic.completed_time,
    "title": lambda task: (task.Basic.show_title or "").lower(),
    "status": lambda task: int(task.Download.status),
    "progress": lambda task: task.Download.progress,
    "total_size": lambda task: task.Download.total_size,
}

class CreateTasksRequest(BaseModel):
    # 解析结果里叶子节点的 episode，前端原样回传
    episodes: List[dict] = Field(min_length = 1, max_length = 2000)
    # 本次任务的下载选项覆盖，不传表示全部沿用全局设置
    options: Optional[dict] = None

class TaskIdsRequest(BaseModel):
    task_ids: List[str] = Field(min_length = 1, max_length = 2000)

async def _off_loop(func, *args, **kwargs):
    return await asyncio.wrap_future(background.submit(func, *args, **kwargs))

def _find(task_ids: List[str]) -> List:
    found = []

    for task_id in task_ids:
        task_info = task_manager.query_by_id(task_id)

        if task_info is not None:
            found.append(task_info)

    return found

@router.get("/tasks/list", response_model = TaskList)
async def list_tasks(completed: bool = Query(default = False),
                     sort_by: str = Query(default = "created_time"),
                     ascending: bool = Query(default = True),
                     limit: int = Query(default = None, ge = 1, le = 5000)):
    """
    列出任务，可排序

    与 `GET /api/tasks` 的区别：那个是给「刷新页面恢复现场」用的全量快照（带事件游标），
    这个是给列表视图用的，可以排序与限量
    """
    if sort_by not in SORT_KEYS:
        return JSONResponse(
            {"detail": f"Unknown sort key: {sort_by}", "allowed": sorted(SORT_KEYS)},
            status_code = 400)

    task_list = await _off_loop(task_manager.query, completed, limit)

    task_list.sort(key = SORT_KEYS[sort_by], reverse = not ascending)

    return {"tasks": task_views(task_list), "sort_by": sort_by, "ascending": ascending}

@router.get("/tasks/count", response_model = TaskCount)
async def count_tasks():
    downloading = await _off_loop(task_manager.count, False)
    completed = await _off_loop(task_manager.count, True)

    return {"downloading": downloading, "completed": completed}

@router.get("/tasks/{task_id}", response_model = TaskView)
async def get_task(task_id: str):
    task_info = await _off_loop(task_manager.query_by_id, task_id)

    if task_info is None:
        return JSONResponse({"detail": "Task not found"}, status_code = 404)

    return task_views([task_info])[0]

def _create_and_collect(episodes: List[dict], options: Optional[dict]) -> List[dict]:
    """
    创建任务并把实际建出来的那些收集回来

    **不能用「建之前 count、建之后再 count」求差**：入库是投递给写线程做的，
    create 返回时还没落盘，count 拿到的是旧数字。改为就地捕获
    `add_to_downloading_list` 事件 —— 那正是 create 用来通知界面的同一个事件。

    订阅要 DIRECT：默认调度器会把它投到事件循环线程去，而这里是在工作线程里同步等
    """
    from util.common.signal_bus import signal_bus
    from util.thread.dispatch import DIRECT

    created = []

    def on_added(task_info_list, *args, **kwargs):
        created.extend(task_info_list)

    signal_bus.download.add_to_downloading_list.connect(on_added, dispatcher = DIRECT)

    try:
        task_manager.create(episodes, False, options)

    finally:
        signal_bus.download.add_to_downloading_list.disconnect(on_added)

    return task_views(created)

@router.post("/tasks", response_model = CreateResult)
async def create_tasks(payload: CreateTasksRequest):
    """
    创建下载任务

    `task_manager.create()` 内部会做**重复下载判定**与**是否需要二次解析**的判断，
    所以实际建出来的可能比传进来的少 —— 返回里如实给出两个数字，
    不然前端会以为「点了没反应」
    """
    created = await _off_loop(_create_and_collect, payload.episodes, payload.options)

    return {
        "requested": len(payload.episodes),
        "created": len(created),
        "tasks": created,
    }

@router.post("/tasks/delete", response_model = DeleteResult)
async def delete_tasks(payload: TaskIdsRequest, completed: bool = Query(default = False)):
    """
    删除任务

    **同时删掉临时文件**（`cancel_many_async` 负责）。只删记录的话，
    下载目录里会留下一堆 `video_<task_id>.m4s`，而且再也没人认得它们属于谁
    """
    task_list = await _off_loop(_find, payload.task_ids)

    if not task_list:
        return JSONResponse({"detail": "No matching task"}, status_code = 404)

    if completed:
        # 已完成的任务没有临时文件要清，直接删记录
        await _off_loop(task_manager.delete_many, task_list, True)

    else:
        await _off_loop(task_manager.cancel_many_async, task_list)

    return {"deleted": len(task_list)}

@router.post("/tasks/retry", response_model = RetryResult)
async def retry_tasks(payload: TaskIdsRequest):
    """
    重新下载

    先 `reset` 把进度与分片记录清干净再 `recreate` —— 只改状态不清记录的话，
    续传会接着上一次那份已经作废的分片表走
    """
    task_list = await _off_loop(_find, payload.task_ids)

    if not task_list:
        return JSONResponse({"detail": "No matching task"}, status_code = 404)

    for task_info in task_list:
        await _off_loop(task_manager.reset, task_info)
        await _off_loop(task_manager.recreate, task_info)

    return {"retried": len(task_list)}

@router.post("/tasks/pause", response_model = PauseResult)
async def pause_tasks(payload: TaskIdsRequest, request: Request):
    """暂停：让 aria2 停下来，并把任务状态置为已暂停"""
    return await _set_paused(request, payload.task_ids, paused = True)

@router.post("/tasks/resume", response_model = PauseResult)
async def resume_tasks(payload: TaskIdsRequest, request: Request):
    """恢复"""
    return await _set_paused(request, payload.task_ids, paused = False)

async def _set_paused(request: Request, task_ids: List[str], paused: bool):
    task_list = await _off_loop(_find, task_ids)

    if not task_list:
        return JSONResponse({"detail": "No matching task"}, status_code = 404)

    registry = getattr(request.app.state, "streams", None)
    client = getattr(request.app.state, "aria2", None)

    status = DownloadStatus.PAUSED if paused else DownloadStatus.QUEUED

    stopped = 0

    for task_info in task_list:
        task_id = task_info.Basic.task_id

        # **先动 aria2 再改状态。** 反过来的话，改完状态但 aria2 没停下来，
        # 界面显示「已暂停」而磁盘上文件还在长 —— 这种不一致最难查
        if registry is not None and client is not None and client.connected:
            for gid in registry.gids_of(task_id):
                try:
                    if paused:
                        await client.pause(gid)

                    else:
                        await client.unpause(gid)

                    stopped += 1

                except Exception as e:
                    # 单个 gid 失败不该让整批操作中断：它可能已经下完或被删了
                    logger.warning("任务 %s 的 gid %s %s失败：%s",
                                   task_id, gid, "暂停" if paused else "恢复", e)

        task_info.Download.status = status

        await _off_loop(task_manager.update, task_info)

    return {"updated": len(task_list), "streams_affected": stopped,
            "status": status.name.lower()}
