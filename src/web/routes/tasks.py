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
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.common.config import config
from util.common.enum import DownloadStatus, DuplicateDownloadResolution
from util.common.signal_bus import signal_bus
from util.download.task.manager import task_manager
from util.thread import background

from ..paths import PathNotAllowed, resolve_within_roots

from ..download.view import task_views

from ..schemas import (
    CreateResult, DeleteResult, DownloadOptions, DuplicateCheck, PauseResult, RetryResult,
    TaskCount, TaskList, TaskView,
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
    # 本次任务的下载选项覆盖，不传表示全部沿用全局设置。
    # 认不出的键会被模型当场拒掉（422），不会安静地回落成全局设置 —— 理由见 DownloadOptions
    options: Optional[DownloadOptions] = None

class TaskIdsRequest(BaseModel):
    task_ids: List[str] = Field(min_length = 1, max_length = 2000)

class CheckDuplicatesRequest(BaseModel):
    # 上限比建任务那边宽：一部长番的解析结果就有一千多条，而这里只是查询
    episodes: List[dict] = Field(min_length = 1, max_length = 5000)

async def _off_loop(func, *args, **kwargs):
    return await asyncio.wrap_future(background.submit(func, *args, **kwargs))

def _live(request: Request):
    """进程里那份「活的 TaskInfo」登记表。aria2 没起来时为 None"""
    return getattr(request.app.state, "merges", None)

def _find(task_ids: List[str], live = None) -> List:
    """
    按 id 取任务，**优先取内存里那份**

    查库会造一个新的 TaskInfo 实例。下载调度、合并、进度回写手里拿着的是另一份，
    两边各改各的、谁后写库谁赢 —— 表现是「暂停了又自己跑起来」「进度偶尔倒退」，
    而两处代码单看都没错。所以先问登记表，问不到才查库，查到的也立刻收进去
    """
    found = []

    for task_id in task_ids:
        task_info = live.get(task_id) if live is not None else None

        if task_info is None:
            task_info = task_manager.query_by_id(task_id)

            if task_info is not None and live is not None:
                task_info = live.adopt(task_info)

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
            {"detail": f"Unknown sort key: {sort_by}", "code": "UNKNOWN_SORT_KEY",
             "allowed": sorted(SORT_KEYS)},
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
        return JSONResponse({"detail": "Task not found", "code": "TASK_NOT_FOUND"},
                            status_code = 404)

    return task_views([task_info])[0]

def _resolve_duplicate_option(options: Optional[dict]) -> dict:
    """
    补上重复下载的处理方式，**绝不能让它落到 ALWAYS_ASK**

    `TaskManager._check_duplicate()` 遇到 ALWAYS_ASK 会发一个信号请 GUI 弹窗，
    然后 `done_event.wait()` 无限期等下去。WebUI 进程里没有那个窗口，也没有人去点，
    于是这一次建任务的 HTTP 请求就永远挂着 —— 而 ALWAYS_ASK 恰恰是**默认值**。

    manager.py 里那段注释已经写明「无人值守的调用方必须显式指定处理方式」，MCP 是
    这么做的，WebUI 也照做。选 SKIP 而不是 CONTINUE：已经下过的东西默认不重下，
    符合这个设置本身的意图；跳掉了多少条会在返回里如实给出（requested 与 created 的差）。
    """
    resolved = dict(options or {})

    given = resolved.get("duplicate_resolution")

    if given is not None:
        # 调用方明确说了要怎么处理，尊重它 —— 但必须换成枚举成员再往下传。
        #
        # **`DuplicateDownloadResolution` 是普通 Enum 不是 IntEnum**：JSON 里过来的
        # `1` 与 `DuplicateDownloadResolution.SKIP` 比较恒为 False 且不报错，
        # manager.py 那个 match 会一个分支都不命中，然后按「跳过」处理 ——
        # 于是「继续下载」这个选择被无声地反转（同 CLAUDE.md 里 Qt.CheckState 那条坑）
        resolved["duplicate_resolution"] = _as_resolution(given)

        return resolved

    if config.get(config.duplicate_download_resolution) == DuplicateDownloadResolution.ALWAYS_ASK:
        resolved["duplicate_resolution"] = DuplicateDownloadResolution.SKIP

    return resolved

def _as_resolution(value) -> DuplicateDownloadResolution:
    """把 JSON 传来的取值换成枚举成员。认不出来一律按 SKIP —— 绝不能是 ALWAYS_ASK"""
    if isinstance(value, DuplicateDownloadResolution):
        return DuplicateDownloadResolution.SKIP if value == DuplicateDownloadResolution.ALWAYS_ASK else value

    try:
        member = DuplicateDownloadResolution(value)

    except ValueError:
        logger.warning("认不出的 duplicate_resolution：%r，按跳过处理", value)

        return DuplicateDownloadResolution.SKIP

    return DuplicateDownloadResolution.SKIP if member == DuplicateDownloadResolution.ALWAYS_ASK else member

def _resolve_path_option(options: dict) -> dict:
    """
    校验并规范化本次任务的下载目录

    **越界判定必须在这里做**：`TaskManager` 那边只兜「空串 / 相对路径」这种会把文件
    写进进程工作目录的取值，而「不许写到白名单根目录之外」是 WebUI 独有的安全边界。

    并且要把 `resolve_within_roots()` 的**返回值**传下去 —— 拿请求里的原始字符串
    去落盘，等于这道检查白做（`routes/files.py` 顶上那段说明同理）
    """
    given = options.get("download_path")

    if given is None:
        return options

    if not isinstance(given, str) or not given.strip():
        raise ValueError("download_path must be a non-empty string")

    options["download_path"] = str(resolve_within_roots(given.strip()))

    return options

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
    # exclude_none：没提到的项不能出现在 dict 里。`pick_option` 用 `is not None` 判定，
    # 带着一堆 None 传下去与不传等价，但会让 `options.setdefault` 之类的判断变得别扭
    given = payload.options.model_dump(exclude_none = True) if payload.options else None

    try:
        options = _resolve_path_option(_resolve_duplicate_option(given))

    except PathNotAllowed as e:
        # 403 而不是 400：路径不在白名单根目录内是权限问题，与 files 那边一致
        return JSONResponse({"detail": str(e), "code": "PATH_NOT_ALLOWED"}, status_code = 403)

    except ValueError as e:
        return JSONResponse({"detail": str(e), "code": "INVALID_OPTIONS"}, status_code = 400)

    # 「每批从 1 开始」的编号以**一次 HTTP 请求**为一批。不给这个 id 的话
    # TaskManager 会退到「从 1 开始」，两个标签页同时提交就会各自从 1 数、算出同名文件。
    # setdefault 而不是覆盖：调用方想把多次请求算作同一批时可以自己传
    options.setdefault("numbering_batch_id", uuid4().hex)

    created = await _off_loop(_create_and_collect, payload.episodes, options)

    return {
        "requested": len(payload.episodes),
        "created": len(created),
        "tasks": created,
    }

@router.post("/tasks/duplicates", response_model = DuplicateCheck)
async def check_duplicates(payload: CheckDuplicatesRequest):
    """
    这批条目里哪些已经下载过

    只查不改，也**不触发任何界面交互** —— `task_manager.is_duplicate` 那条路径本身就是
    为无人值守的调用方准备的。

    解析页靠它把已下过的标出来。那不是锦上添花：重复项在服务端是被**静默跳过**的
    （WebUI 没有可询问的对象），不提前标的话，用户点完下载只会看到
    「创建了 3 个，共勾选 10 项」，而不知道另外 7 项去了哪里
    """
    flags = await _off_loop(task_manager.which_are_duplicates, payload.episodes)

    return {"duplicates": flags}

@router.post("/tasks/delete", response_model = DeleteResult)
async def delete_tasks(payload: TaskIdsRequest, request: Request,
                       completed: bool = Query(default = False)):
    """
    删除任务

    **同时删掉临时文件**（`cancel_many_async` 负责）。只删记录的话，
    下载目录里会留下一堆 `video_<task_id>.m4s`，而且再也没人认得它们属于谁。

    **先让 aria2 停下再删文件**：反过来的话，文件删了而 aria2 还在写，
    转眼又长出一个没人认得的半截文件
    """
    task_list = await _off_loop(_find, payload.task_ids, _live(request))

    if not task_list:
        return JSONResponse({"detail": "No matching task", "code": "NO_MATCHING_TASK"},
                            status_code = 404)

    task_ids = [task.Basic.task_id for task in task_list]

    if completed:
        # 已完成的任务没有临时文件要清，直接删记录
        await _off_loop(task_manager.delete_many, task_list, True)

    else:
        await _stop_streams(request, task_ids)

        await _off_loop(task_manager.cancel_many_async, task_list)

    # 显式推一条删除。`delete_many` 什么都不发，`cancel_many_async` 发的那条
    # 又被发布器按「完成」过滤掉了一部分 —— 两条路径都靠这里兜住
    publisher = getattr(request.app.state, "publisher", None)

    if publisher is not None:
        publisher.publish_removed(task_ids)

    return {"deleted": len(task_list)}

async def _stop_streams(request: Request, task_ids: list) -> None:
    """把这些任务名下的 gid 从 aria2 里撤掉，并把它们从登记表里清出去"""
    driver = getattr(request.app.state, "driver", None)

    if driver is None:
        return

    for task_id in task_ids:
        await driver.forget_task(task_id)

@router.post("/tasks/retry", response_model = RetryResult)
async def retry_tasks(payload: TaskIdsRequest, request: Request):
    """
    重新下载

    先 `reset` 把进度与分片记录清干净再 `recreate` —— 只改状态不清记录的话，
    续传会接着上一次那份已经作废的分片表走
    """
    task_list = await _off_loop(_find, payload.task_ids, _live(request))

    if not task_list:
        return JSONResponse({"detail": "No matching task", "code": "NO_MATCHING_TASK"},
                            status_code = 404)

    # 旧的 gid 连同它下到一半的文件一起作废。不撤掉的话，新一轮会和它写同一个文件，
    # 而 aria2 不认为两个下载写同一个文件是错误
    await _stop_streams(request, [task.Basic.task_id for task in task_list])

    for task_info in task_list:
        await _off_loop(task_manager.reset, task_info)
        await _off_loop(task_manager.recreate, task_info)

    # recreate 会发 auto_manage_concurrent_downloads，调度器接着就把它们推上路
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
    task_list = await _off_loop(_find, task_ids, _live(request))

    if not task_list:
        return JSONResponse({"detail": "No matching task", "code": "NO_MATCHING_TASK"},
                            status_code = 404)

    registry = getattr(request.app.state, "streams", None)
    client = getattr(request.app.state, "aria2", None)
    driver = getattr(request.app.state, "driver", None)

    stopped = 0

    for task_info in task_list:
        task_id = task_info.Basic.task_id

        gids = registry.gids_of(task_id) if registry is not None else []

        # **先动 aria2 再改状态。** 反过来的话，改完状态但 aria2 没停下来，
        # 界面显示「已暂停」而磁盘上文件还在长 —— 这种不一致最难查
        if gids and client is not None and client.connected:
            for gid in gids:
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

        if paused:
            task_info.Download.status = DownloadStatus.PAUSED
            task_info.Download.speed = 0

        elif gids:
            # aria2 那边还认得它，unpause 完就已经在下了。这时置成排队的话，
            # 界面会显示「等待下载」而文件在涨
            task_info.Download.status = DownloadStatus.DOWNLOADING

        else:
            # 还没投递过（新建的、失败重置的、gid 已作废的）。退回排队交给调度器，
            # **不要就地起** —— 就地起会绕过 download_parallel，
            # 点一下「全部开始」就是几十个并发
            task_info.Download.status = DownloadStatus.QUEUED

        await _off_loop(task_manager.update, task_info)

        # 状态变了要推给前端。这条链路上没有别人会发：aria2 的事件只在
        # 它自己动的时候来，而「排队中」这个状态它根本不知道
        signal_bus.download.update_downloading_item.emit(task_info)

    if not paused and driver is not None:
        driver.schedule()

    # 报的是**实际落到任务上的**状态：恢复时 aria2 还认得的那些直接就是下载中，
    # 没投递过的才是排队。统一报「排队」的话，界面上会出现一个「等待下载」而字节在涨的任务
    if paused:
        status = DownloadStatus.PAUSED

    else:
        status = DownloadStatus.DOWNLOADING if stopped else DownloadStatus.QUEUED

    return {"updated": len(task_list), "streams_affected": stopped,
            "status": status.name.lower()}
