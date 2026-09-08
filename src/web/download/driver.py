"""
把排队中的任务推上路，并把 aria2 的进度写回任务

这是服务端缺的那一块。此前 `resolver.submit_stream()` 写好了却**没有任何调用方** ——
建出来的任务永远停在「等待下载」，而后端一切正常、日志里也没有错误。
重启对账（`reconcile.py`）只认已经有流记录的任务，帮不上从零开始的那些。

对应桌面版的 `Downloader` + `gui/component/download_list/model.py` 的
`_manageConcurrentDownloads`：前者负责单个任务怎么跑，后者负责同时跑几个。
服务端两件事都在这里。

## 并发额度

与桌面版同一条规则：`download_parallel` 个任务同时在跑，占额度的状态是「解析中」与
「下载中」。**占额度要在派发之前同步做掉** —— `ensure_future` 排的协程要等到下一次
循环迭代才开始，等它自己去改状态的话，同一轮扫描会把额度重复发出去。

## 进度

aria2 不推进度（没有 onProgress 这类通知），`monitor.py` 每秒用 `tellActive` 拉一次。
拉回来的是**流级**的数字，要按 `StreamRegistry` 聚合成任务级的再写进 TaskInfo，
否则前端只能看到一个永远不动的进度条 —— `task.updated` 事件本来就没人发。

## 活的 TaskInfo 只能有一份

同一个任务在内存里出现两个实例的话，两边各改各的，最后谁写库谁赢，
表现是「进度偶尔倒退」「暂停了又自己跑起来」。所以整个服务端共用一份登记表，
就是 `MergeCoordinator` 里那个（`reconcile` 早就在往里放了）——
路由拿任务也必须先问它，问不到才去查库。
"""

from pathlib import Path
from typing import List, Optional
import asyncio
import logging
import threading

from util.common.config import config
from util.common.enum import DownloadStatus, DownloadType, MediaType
from util.common.signal_bus import signal_bus
from util.common.translator import Translator
from util.download.parse.download_info import resolve_download_info, stream_entries
from util.download.task.info import TaskInfo
from util.download.task.manager import task_manager
from util.thread import background

from .resolver import remember_stream, stream_keys, submit_stream
from .streams import TASK_ERROR, TASK_PAUSED

logger = logging.getLogger(__name__)

# 占用下载并发额度的状态
BUSY_STATUS = (DownloadStatus.DOWNLOADING, DownloadStatus.PARSING)

async def _off_loop(func, *args, **kwargs):
    """
    丢到后台线程

    解析下载链接要发好几个 HTTP 请求、CDN 探测的整体预算是 30 秒。直接在协程里做
    会把事件循环占死那么久 —— 期间 aria2 的通知、WebSocket 推送、HTTP 请求
    全部停摆，且没有任何报错
    """
    return await asyncio.wrap_future(background.submit(func, *args, **kwargs))

class DownloadDriver:
    def __init__(self, client, registry, merges):
        self.client = client
        self.registry = registry

        # 兼作进程里那份「活的 TaskInfo」登记表，理由见模块说明
        self.merges = merges

        self._lock = threading.RLock()
        self._scheduling = False

        self._attached = False

    # ---- 生命周期 ----

    def attach(self) -> None:
        if self._attached:
            return

        # 与桌面版订阅的是同一批事件。新建、重试都会发 add_to_downloading_list，
        # 那些 TaskInfo 必须收进登记表，否则调度扫不到它们
        signal_bus.download.add_to_downloading_list.connect(self.on_added)
        signal_bus.download.add_to_completed_list.connect(self.on_completed)
        signal_bus.download.auto_manage_concurrent_downloads.connect(self.schedule)

        # **不订阅 remove_from_downloading_list**：那个事件的意思是「从下载中这个列表里挪走」，
        # 任务下完了也会发一次（`Merger.mark_as_completed`）。拿它当「任务被删了」用的话，
        # 每个正常完成的任务都会被当成删除处理一遍 —— 而且那一下正好发生在 Merger
        # 自己的完成回调里，顺手去 stop() 它等于让线程在自己的回调里自杀。
        # 真正的删除走路由，那里直接调 forget_task

        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return

        signal_bus.download.add_to_downloading_list.disconnect(self.on_added)
        signal_bus.download.add_to_completed_list.disconnect(self.on_completed)
        signal_bus.download.auto_manage_concurrent_downloads.disconnect(self.schedule)

        self._attached = False

    def load(self) -> int:
        """
        把库里未完成的任务收进登记表

        启动时调一次，**排在对账之后** —— 对账已经把还在跑的那些放进去了，
        这里用 adopt 而不是 track，免得给同一个任务再造一份实例
        """
        count = 0

        for task_info in task_manager.query(completed = False):
            self.merges.adopt(task_info)

            count += 1

        return count

    # ---- 事件 ----

    def on_added(self, task_info_list: List[TaskInfo], *args, **kwargs) -> None:
        for task_info in task_info_list:
            self.merges.adopt(task_info)

    def on_completed(self, task_info_list: List[TaskInfo], *args, **kwargs) -> None:
        """
        任务下完了

        把 gid 的登记摘掉即可，**不要去 aria2 那儿撤**（它们本来就完成了），
        也不动登记表 —— 已完成列表还要显示它们。

        摘掉是有必要的：`StreamRegistry` 非空时进度轮询每秒都会去问一次 aria2，
        不摘的话服务开着就一直在问一批早已下完的 gid
        """
        for task_info in task_info_list:
            self.registry.unregister_task(task_info.Basic.task_id)

    async def forget_task(self, task_id: str) -> None:
        """
        任务被删了：登记表清掉，并**告诉 aria2 停下**

        只删记录的话它会继续下，磁盘上的文件还在长大，而界面上这个任务已经不存在了
        —— 用户没有任何办法让它停下来
        """
        self.merges.forget(task_id)

        gids = self.registry.unregister_task(task_id)

        if not gids or self.client is None or not self.client.connected:
            return

        for gid in gids:
            try:
                await self.client.remove(gid)

            except Exception as e:
                # 已经下完或已经被删掉的 gid 会报错，那不是问题
                logger.debug("从 aria2 移除任务 %s 的 gid %s 失败：%s", task_id, gid, e)

    # ---- 调度 ----

    def schedule(self, *args, **kwargs) -> None:
        """
        推进下载队列

        参数一律吃掉：它挂在 `auto_manage_concurrent_downloads` 上，而那个事件
        将来可能带参数。回调由 `web/dispatch.py` 投递到事件循环线程，
        所以这里可以直接 `ensure_future`
        """
        with self._lock:
            if self._scheduling:
                # 重入。被跳过的这一次不会丢：本轮扫描还会往下走，
                # 且每个任务状态变化都会再发一次事件
                return

            self._scheduling = True

        try:
            self._schedule()

        finally:
            with self._lock:
                self._scheduling = False

    def _schedule(self) -> None:
        limit = max(1, int(config.get(config.download_parallel) or 1))

        active = 0
        queued = []

        for task_info in self.merges.tracked():
            status = task_info.Download.status

            if status in BUSY_STATUS:
                active += 1

            elif status == DownloadStatus.QUEUED:
                queued.append(task_info)

        if not queued:
            return

        # 排队中的按创建顺序起，与桌面版列表的默认顺序一致
        queued.sort(key = lambda task: task.Basic.created_time)

        for task_info in queued:
            if active >= limit:
                break

            # **同步占住额度**，理由见模块说明
            task_info.Download.status = DownloadStatus.PARSING

            active += 1

            asyncio.ensure_future(self._start(task_info))

    # ---- 单个任务 ----

    async def _start(self, task_info: TaskInfo) -> None:
        task_id = task_info.Basic.task_id

        try:
            await self._run_start(task_info)

        except Exception as e:
            logger.exception("启动下载任务失败：%s", task_id)

            self._fail(task_info, str(e))

    async def _run_start(self, task_info: TaskInfo) -> None:
        task_id = task_info.Basic.task_id

        if self.client is None or not self.client.connected:
            # aria2 不可用。退回排队而不是判失败 —— 它重连之后这个任务还能自己跑起来
            logger.warning("aria2 未连接，任务 %s 退回排队", task_id)

            task_info.Download.status = DownloadStatus.QUEUED

            return

        has_stream = task_info.Download.type & (DownloadType.VIDEO | DownloadType.AUDIO) != 0

        if not has_stream:
            # 只下弹幕 / 字幕 / 封面这类任务，没有流要交给 aria2，
            # 直接进附加内容阶段（桌面版 Downloader.start() 的同一个分支）
            task_info.Download.info_label = Translator.TIP_MESSAGES("ADDITIONAL_FILES")

            self.merges.adopt(task_info)

            await self.merges.on_download_finished(task_info)

            return

        if stream_keys(task_info) and self.registry.gids_of(task_id):
            # aria2 那边已经有这个任务了（暂停后恢复、对账认回来的），不必重新解析
            await self._resume_streams(task_info)

            return

        task_info.Download.speed = 0

        task_manager.update_async(task_info)

        self._publish(task_info)

        download_info = await _off_loop(resolve_download_info, task_info)

        if download_info is None:
            return

        if task_info.Download.status != DownloadStatus.PARSING:
            # 解析期间被暂停或删除了。这时候再往 aria2 塞任务，用户会看到一个
            # 「已暂停」却在涨的进度条
            logger.info("任务 %s 在解析期间被中止，放弃投递", task_id)

            return

        await self._submit(task_info, download_info)

    async def _submit(self, task_info: TaskInfo, download_info: dict) -> None:
        task_id = task_info.Basic.task_id

        entries = stream_entries(download_info)

        if not entries:
            # 解析成功却一路流都没有。当成下载完成往下走，剩下的附加内容与合并照常
            logger.info("任务 %s 没有需要下载的流，直接进入收尾", task_id)

            self.merges.adopt(task_info)

            await self.merges.on_download_finished(task_info)

            return

        task_info.Download.total_size = download_info["total_size"]

        # 只在 files 为空时设队列（说明是第一次解析而非断点复拉），与桌面版一致
        if not task_info.Download.files:
            task_info.Download.queue = list(download_info["download_queue"])

        self._update_media_info(task_info, download_info)

        directory = Path(task_info.File.download_path, task_info.File.folder)

        await _off_loop(directory.mkdir, parents = True, exist_ok = True)

        for entry in entries:
            file_key = entry["file_key"]

            await submit_stream(
                self.client, self.registry, task_id, file_key,
                entry.get("url", ""), directory, entry.get("file_name", ""),
                referer = task_info.Episode.url, task_info = task_info
            )

            # 落一份预期大小：重启对账要靠它判断磁盘上那个文件是不是完整的
            remember_stream(task_info, file_key, file_size = entry.get("file_size", 0))

        task_info.Download.status = DownloadStatus.DOWNLOADING
        task_info.Download.status_label = ""

        self.merges.adopt(task_info)

        task_manager.update(task_info)

        self._publish(task_info)

    async def _resume_streams(self, task_info: TaskInfo) -> None:
        """aria2 那边还认得这个任务，让它接着下就行"""
        task_id = task_info.Basic.task_id

        for gid in self.registry.gids_of(task_id):
            try:
                await self.client.unpause(gid)

            except Exception as e:
                # 已经在跑的 gid 会报错，那不是问题
                logger.debug("恢复任务 %s 的 gid %s 失败：%s", task_id, gid, e)

        task_info.Download.status = DownloadStatus.DOWNLOADING

        task_manager.update(task_info)

        self._publish(task_info)

    def _update_media_info(self, task_info: TaskInfo, download_info: dict) -> None:
        """对齐桌面版 `Downloader.update_info()`：记下每路流的大小与那行媒体信息"""
        if task_info.Download.files:
            return

        task_info.Download.files = {
            file_key: {
                "file_size": (download_info["download_list"].get(file_key) or {}).get("file_size", 0)
            }
            for file_key in download_info["download_queue"]
        }

        has_video = task_info.Download.type & DownloadType.VIDEO != 0
        has_audio = task_info.Download.type & DownloadType.AUDIO != 0

        if has_video and not has_audio:
            if task_info.Download.media_type == MediaType.MP4:
                task_info.Download.info_label = "MP4"

            elif task_info.Download.media_type == MediaType.FLV:
                task_info.Download.info_label = "FLV"

        # 画质那一行由前端按 `video_quality_id` 自己出文案（D12）——
        # 服务端进程里没有 Qt 的翻译函数，在这里拼只会得到英文
        task_manager._update_media_info(task_info)

    def _fail(self, task_info: TaskInfo, message: str) -> None:
        task_info.Download.status = DownloadStatus.FAILED
        task_info.Download.status_label = message
        task_info.Download.speed = 0

        task_manager.update(task_info)

        self._publish(task_info)

        # 腾出来的额度要立刻给下一个，否则一次失败会让整条队列停住
        self.schedule()

    # ---- 进度回写 ----

    def on_stream_progress(self, snapshot: dict) -> None:
        """
        把聚合后的流状态写进 TaskInfo 并推给前端

        接的是 `StreamMonitor.on_task_progress`（每次轮询都调，与变更通知那条分开）。
        **速度必须走这条**：变更判定里刻意不含 speed，只挂在那边的话，
        界面上的速度要等进度整整跳一个百分点才会更新一次
        """
        task_info = self.merges.get(snapshot.get("task_id"))

        if task_info is None:
            return

        status = snapshot.get("status")

        if task_info.Download.status not in (DownloadStatus.DOWNLOADING, DownloadStatus.PARSING):
            # 已经进了附加内容或合并阶段，那时的进度归 FFmpeg 报，不能被流的数字盖掉
            return

        if status == TASK_ERROR:
            self._fail(task_info, snapshot.get("error_message")
                       or Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"))

            return

        if status == TASK_PAUSED:
            return

        task_info.Download.status = DownloadStatus.DOWNLOADING
        task_info.Download.progress = snapshot.get("progress", 0)
        task_info.Download.speed = snapshot.get("speed", 0)
        task_info.Download.downloaded_size = snapshot.get("downloaded_size", 0)

        total = snapshot.get("total_size", 0)

        if total:
            # aria2 报回来的才是真实大小，解析阶段那个是接口给的估算值
            task_info.Download.total_size = total

        # 进度是高频写入，走合并快照那条路（每个任务只留最新的一份）
        task_manager.update_async(task_info)

        self._publish(task_info)

    def _publish(self, task_info: TaskInfo) -> None:
        signal_bus.download.update_downloading_item.emit(task_info)

    # ---- 查 ----

    def get(self, task_id: str) -> Optional[TaskInfo]:
        return self.merges.get(task_id)
