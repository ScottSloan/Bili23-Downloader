"""
重启对账（S3-8）

PLAN 把这里标成隐蔽 bug 高发区，要单独写测试。三种情况都要能恢复：
**杀后端 / 杀 aria2 / 两个一起杀**。

## 唯一权威是 task.db

aria2 的 session 文件不能当依据，这是实测出来的：

    Windows 上 Popen.terminate() 就是 TerminateProcess，aria2 没有任何收尾机会，
    --save-session 指定的文件根本不会生成。被强杀、断电时更不用说。

所以 `process.py` 里连 `--input-file` 都刻意不带 —— 让 aria2 自己从 session 捞任务，
会和这里重新投递的那一份撞上：**两个下载写同一个文件，而 aria2 不认为这是错误**。

对账因此是单向的：读 task.db，问 aria2「这些你还认得吗」，不认得就重新交代一遍。

## 认领的三条路径，顺序要紧

1. **按 gid 认领** —— aria2 没重启过，gid 还在，直接接管
2. **按落盘路径认领** —— aria2 重启过，同一个文件拿到了新 gid（sidecar 形态下它可能
   自己从 session 恢复了任务）。不做这一步就会重复投递
3. **按磁盘认领** —— aria2 完全不知道这个文件，但它已经在磁盘上下完了
   （没有 `.aria2` 控制文件且大小对得上）。不做这一步会把已完成的流重下一遍

三条都不成立才重新 `addUri`。续传靠的是磁盘上的 `.aria2` 控制文件，不是 session。

## 合并阶段的死法要分清

合并中被杀，`Merger` 的 FFmpeg 是本进程的子进程，会跟着一起死。重启后简单粗暴地重合并
在两种死法上是错的：

- **死在 rename 之后、删临时文件之前** —— 最终文件已经生成了，重合并会再产出一个副本
- **死在删临时文件之后** —— 流文件没了，重合并只会报「文件不存在」

两者的共同特征是**最终文件已存在而临时输出文件不在**，据此收尾即可，不必重跑 FFmpeg。
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from util.common.enum import DownloadStatus
from util.common.io.file import safe_remove
from util.download.task.info import TaskInfo
from util.download.task.manager import task_manager

from ..aria2 import Aria2Error
from .resolver import build_options, stream_keys, stream_record, remember_stream
from .streams import ARIA2_ACTIVE, ARIA2_COMPLETE, ARIA2_ERROR, ARIA2_PAUSED, ARIA2_WAITING

logger = logging.getLogger(__name__)

# 对账时要问 aria2 拿的字段。files 是按路径认领的依据
RECONCILE_KEYS = ["gid", "status", "totalLength", "completedLength", "errorMessage", "files"]

# 这些状态说明任务还在下载链路上，需要对账。其余（排队中、已暂停、已完成、失败）
# 要么等用户动手，要么已经尘埃落定，都不该在启动时被自动推着走
ACTIVE_STATUS = (
    DownloadStatus.DOWNLOADING,
    DownloadStatus.PARSING,
    DownloadStatus.ADDITIONAL_PROCESSING,
    DownloadStatus.FFMPEG_QUEUED,
    DownloadStatus.MERGING,
    DownloadStatus.CONVERTING,
)

class Reconciler:
    def __init__(self, client, registry, merges):
        self.client = client
        self.registry = registry
        self.merges = merges

    # ---- 入口 ----

    async def run(self, task_list: List[TaskInfo] = None) -> dict:
        """
        对一遍账，返回统计

        task_list 不传就从 task.db 里查未完成的任务
        """
        if task_list is None:
            task_list = task_manager.query(completed = False)

        stats = {"tasks": 0, "adopted": 0, "resubmitted": 0, "from_disk": 0,
                 "merged_already": 0, "requeued": 0, "failed": 0}

        known = await self._collect_known()

        for task_info in task_list:
            if task_info.Download.status not in ACTIVE_STATUS:
                continue

            stats["tasks"] += 1

            try:
                await self._reconcile_task(task_info, known, stats)

            except Exception:
                logger.exception("对账任务 %s 时出错", task_info.Basic.task_id)

                stats["failed"] += 1

        logger.info("重启对账完成：%s", stats)

        return stats

    # ---- aria2 现有的下载 ----

    async def _collect_known(self) -> Tuple[Dict[str, dict], Dict[str, dict]]:
        """
        把 aria2 当前知道的所有下载拉回来，建两个索引：按 gid、按落盘路径

        三种列表都要问：`tellActive` 只给正在跑的，暂停的在 `tellWaiting` 里，
        **我们不在的时候下完的在 `tellStopped` 里** —— 漏掉最后一个，
        已经下完的任务会被判成「aria2 不认识」而重下一遍
        """
        by_gid: Dict[str, dict] = {}
        by_path: Dict[str, dict] = {}

        entries = []

        for fetch in (
            lambda: self.client.tell_active(RECONCILE_KEYS),
            lambda: self.client.tell_waiting(0, 1000, RECONCILE_KEYS),
            lambda: self.client.tell_stopped(0, 1000, RECONCILE_KEYS),
        ):
            try:
                entries.extend(await fetch() or [])

            except Exception as e:
                logger.warning("查询 aria2 现有下载失败：%s", e)

        for entry in entries:
            gid = entry.get("gid")

            if gid:
                by_gid[gid] = entry

            for file_entry in entry.get("files") or []:
                path = file_entry.get("path")

                if path:
                    by_path[_normalize(path)] = entry

        return by_gid, by_path

    # ---- 单个任务 ----

    async def _reconcile_task(self, task_info: TaskInfo, known, stats: dict) -> None:
        by_gid, by_path = known

        task_id = task_info.Basic.task_id

        # 已经在 FFmpeg 阶段的任务不必再问 aria2 —— 流早就下完了
        if task_info.Download.status in (DownloadStatus.MERGING, DownloadStatus.CONVERTING):
            self._recover_merge_stage(task_info, stats)

            self.merges.track(task_info)

            task_manager.update_async(task_info)

            self.merges.schedule()

            return

        if task_info.Download.status == DownloadStatus.FFMPEG_QUEUED:
            self.merges.track(task_info)

            stats["requeued"] += 1

            self.merges.schedule()

            return

        keys = stream_keys(task_info)

        if not keys:
            # 连一路流的记录都没有，说明死在了「解析出链接」之前。
            # 这种只能退回排队，等用户或自动调度重新走一遍解析
            logger.info("任务 %s 没有可恢复的流记录，退回排队", task_id)

            task_info.Download.status = DownloadStatus.QUEUED

            task_manager.update_async(task_info)

            return

        complete = 0

        for file_key in keys:
            outcome = await self._reconcile_stream(task_info, file_key, by_gid, by_path)

            stats[outcome] = stats.get(outcome, 0) + 1

            if outcome in ("from_disk", "adopted_complete"):
                complete += 1

        self.merges.track(task_info)

        if complete == len(keys):
            # 我们不在的时候全部下完了，把剩下的流程接着走完
            logger.info("任务 %s 的所有流在离线期间已完成，继续走附加内容与合并", task_id)

            await self.merges.on_download_finished(task_info)

            return

        task_info.Download.status = DownloadStatus.DOWNLOADING

        task_manager.update_async(task_info)

    # ---- 单路流 ----

    async def _reconcile_stream(self, task_info: TaskInfo, file_key: str,
                                by_gid: dict, by_path: dict) -> str:
        task_id = task_info.Basic.task_id

        record = stream_record(task_info, file_key)

        gid = record.get("gid")
        path = _expected_path(record)

        # 1. 按 gid 认领
        entry = by_gid.get(gid) if gid else None

        # 2. 按落盘路径认领（aria2 重启后 gid 会变）
        if entry is None and path is not None:
            entry = by_path.get(_normalize(str(path)))

            if entry is not None:
                logger.info("任务 %s 的 %s 流按路径认回，gid 由 %s 变为 %s",
                            task_id, file_key, gid, entry.get("gid"))

        if entry is not None:
            new_gid = entry.get("gid")

            self.registry.register(task_id, file_key, new_gid)
            self.registry.update_from_status(entry)

            remember_stream(task_info, file_key, gid = new_gid)

            status = entry.get("status")

            if status == ARIA2_COMPLETE:
                return "adopted_complete"

            if status in (ARIA2_ERROR,):
                # aria2 那边已经失败了，重新投递一次比留着一个死掉的 gid 强
                return await self._resubmit(task_info, file_key, record)

            return "adopted"

        # 3. 按磁盘认领：aria2 不知道它，但文件已经完整躺在那儿
        if path is not None and _looks_complete(path, record):
            logger.info("任务 %s 的 %s 流在磁盘上已完整，无需重下", task_id, file_key)

            return "from_disk"

        # 4. 重新投递
        return await self._resubmit(task_info, file_key, record)

    async def _resubmit(self, task_info: TaskInfo, file_key: str, record: dict) -> str:
        url = record.get("url")

        if not url:
            logger.warning("任务 %s 的 %s 流没有存下链接，无法重新投递",
                           task_info.Basic.task_id, file_key)

            return "failed"

        options = build_options(record.get("dir", ""), record.get("out", ""),
                                referer = record.get("referer"))

        try:
            gid = await self.client.add_uri([url], options)

        except (Aria2Error, Exception) as e:
            logger.warning("重新投递任务 %s 的 %s 流失败：%s",
                           task_info.Basic.task_id, file_key, e)

            return "failed"

        self.registry.register(task_info.Basic.task_id, file_key, gid)

        remember_stream(task_info, file_key, gid = gid)

        logger.info("任务 %s 的 %s 流已重新投递，新 gid=%s",
                    task_info.Basic.task_id, file_key, gid)

        return "resubmitted"

    # ---- 合并阶段 ----

    def _recover_merge_stage(self, task_info: TaskInfo, stats: dict) -> None:
        """
        合并中被杀之后的恢复

        FFmpeg 是本进程的子进程，跟着一起死了。判断合并到底做完没有，
        依据是「最终文件在、临时输出文件不在」—— 理由见模块说明
        """
        from util.download.downloader.merger import Merger

        merger = Merger(task_info)

        cwd = Path(task_info.File.download_path, task_info.File.folder)

        final_path = cwd / merger.final_output_file_name
        temp_output = cwd / merger.temp_output_file_name

        if final_path.is_file() and not temp_output.exists():
            # 合并其实已经成功了，只是没来得及收尾。重跑 FFmpeg 只会多出一个
            # 「名字 (1).mp4」—— 冲突策略默认是自动改名，不会覆盖
            logger.info("任务 %s 的最终文件已存在，判定合并已完成，直接收尾",
                        task_info.Basic.task_id)

            stats["merged_already"] += 1

            # **不能直接调 on_merge_completed**：它头一件事就是把临时输出文件改名成最终文件，
            # 而此刻临时文件正是不存在的那个，safe_rename 会抛 FileNotFoundError，
            # 于是任务被判成合并失败。这里手工做它剩下的那几步
            safe_remove(cwd, *task_info.File.relative_files)

            merger.add_file(merger.final_output_file_name, clear = True)
            merger.mark_as_completed()

            return

        logger.info("任务 %s 的合并未完成，退回 FFmpeg 队列", task_info.Basic.task_id)

        task_info.Download.status = DownloadStatus.FFMPEG_QUEUED
        task_info.Download.progress = 0

        stats["requeued"] += 1

def _normalize(path: str) -> str:
    """
    比较路径用的规范形式

    aria2 回的是它自己拼出来的绝对路径，大小写与分隔符不一定与我们存的一致，
    Windows 上尤其如此
    """
    try:
        return str(Path(path).resolve()).lower()

    except Exception:
        return str(path).lower()

def _expected_path(record: dict) -> Optional[Path]:
    directory = record.get("dir")
    out = record.get("out")

    if not directory or not out:
        return None

    return Path(directory) / out

def _looks_complete(path: Path, record: dict) -> bool:
    """
    磁盘上这个文件下完了吗

    `.aria2` 控制文件的存在与否是 aria2 自己的判据：**下载完成时它会被删掉**。
    还在的话说明中途断了，不能当成完整文件
    """
    if not path.is_file():
        return False

    if path.with_suffix(path.suffix + ".aria2").exists():
        return False

    size = path.stat().st_size

    if size <= 0:
        return False

    expected = record.get("file_size") or record.get("total")

    if expected:
        return size == int(expected)

    # 没存过预期大小时只能认「文件在且控制文件已消失」。
    # 这正是 aria2 判定完成的同一套依据，不额外加戏
    return True
