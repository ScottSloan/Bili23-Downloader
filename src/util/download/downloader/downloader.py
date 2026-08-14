from PySide6.QtCore import QRunnable, QThreadPool, QObject, QTimer, Slot, QMetaObject, Q_ARG
from PySide6.QtCore import Qt

from ...common.enum import DownloadStatus, DownloadType, MediaType, ToastNotificationCategory
from ...common.data import reversed_video_quality_map
from ...common.io.directory import Directory
from ...common.translator import Translator
from ...common.signal_bus import signal_bus
from ...common._json import json_loads
from ...common.config import config
from ...common.io.file import File

from ...parse.additional.worker import AdditionalParseWorker
from ...parse.additional.chapter import ChapterParser
from ...thread.pool import GlobalThreadPoolTask
from ...network.request import get_cookies, get_proxy_mounts, get_ssl_context
from ...thread.async_ import AsyncTask

from ..task.manager import task_manager
from ..task.info import TaskInfo

from .parse_worker import ParseWorker
from .merger import Merger

from threading import Event, Lock, Thread
from pathlib import Path
import logging
import errno
import httpx
import time

logger = logging.getLogger(__name__)

class TokenBucket:
    """线程安全的令牌桶，用于平滑限制下载速度"""
    def __init__(self, rate: float):
        """
        :param rate: 令牌产生速率（字节/秒），若为0则不限速
        """
        self.rate = rate
        self.tokens = rate
        self.last_update = time.monotonic()
        self.lock = Lock()

    def consume(self, amount: int, stop_event: Event = None):
        if self.rate <= 0:
            return

        sleep_time = 0
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            self.tokens += elapsed * self.rate
            if self.tokens > self.rate:
                self.tokens = self.rate
            
            self.tokens -= amount
            if self.tokens < 0:
                sleep_time = -self.tokens / self.rate

        if sleep_time > 0:
            # 分段休眠，防止阻塞暂停信号
            while sleep_time > 0:
                if stop_event and stop_event.is_set():
                    break
                s = min(0.1, sleep_time)
                time.sleep(s)
                sleep_time -= s

    def set_rate(self, rate: float):
        with self.lock:
            self.rate = rate
            self.tokens = rate
            self.last_update = time.monotonic()

class ChunkWorker(QRunnable):
    max_retries = 5
    # 每写满这么多字节就 flush 一次并记录断点。进程崩溃时 Python 缓冲区里的数据会丢，
    # flush 之后数据已交给操作系统，即便进程被强杀也仍在磁盘上，断点因此是可信的。
    flush_interval = 1024 * 1024
    retryable_status_codes = {408, 429, 500, 502, 503, 504}
    permanent_status_codes = {400, 401, 403, 404, 405, 410, 416}
    permanent_errnos = {
        errno.EACCES,
        errno.EPERM,
        errno.ENOENT,
        errno.ENOSPC,
        errno.EROFS,
        errno.EISDIR,
        errno.ENOTDIR,
    }
    retryable_errnos = {
        errno.EAGAIN,
        errno.EWOULDBLOCK,
        errno.EINTR,
        errno.ETIMEDOUT,
        errno.ECONNRESET,
        errno.ECONNABORTED,
        errno.ECONNREFUSED,
        errno.ENETDOWN,
        errno.ENETUNREACH,
        errno.EHOSTUNREACH,
        errno.EPIPE,
    }

    def __init__(self, session: httpx.Client, file_key: str, chunk_index: int, chunk_range: tuple[int, int], file_path: Path, url: str, referer: str, task_info: TaskInfo, stop_event: Event, lock: Lock, token_bucket: TokenBucket, generation: int, parent=None, on_chunk_start=None, on_chunk_end=None):
        super().__init__()
        self.session = session
        self.file_key = file_key
        self.chunk_index = chunk_index
        self.offset_key = str(chunk_index)      # 断点表随任务快照走 JSON，键统一用字符串
        self.chunk_range = chunk_range
        self.chunk_size = chunk_range[1] - chunk_range[0]
        self.file_path = file_path
        self.url = url
        self.referer = referer
        self.task_info = task_info
        self.stop_event = stop_event
        self.lock = lock
        self.token_bucket = token_bucket
        self.generation = generation
        self.parent = parent
        self.on_chunk_start = on_chunk_start
        self.on_chunk_end = on_chunk_end

    def _invoke_download_error(self, message: str):
        if self.parent:
            logger.error(message)

            QMetaObject.invokeMethod(
                self.parent,
                "on_download_error",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, message)
            )

    def _is_retryable_exception(self, exc: Exception):
        if isinstance(exc, StopIteration):
            return True

        if isinstance(exc, httpx.HTTPStatusError):
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in self.permanent_status_codes:
                return False
            if status_code in self.retryable_status_codes:
                return True
            return bool(status_code and status_code >= 500)

        if isinstance(exc, httpx.RequestError):
            return True

        if isinstance(exc, OSError):
            return exc.errno in self.retryable_errnos

        return False

    def _build_error_message(self, exc: Exception):
        if isinstance(exc, httpx.HTTPStatusError):
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            return f"请求返回异常状态码 {status_code}: {exc}"

        if isinstance(exc, httpx.RequestError):
            return str(exc)

        if isinstance(exc, OSError):
            return f"文件读写失败: {exc}"

        if isinstance(exc, StopIteration):
            return str(exc)

        return f"未知异常: {exc}"

    def _report_download_failure(self, exc: Exception, attempt: int, retryable: bool):
        reason = self._build_error_message(exc)

        if retryable:
            message = f"分片 {self.chunk_index + 1} 下载失败，已尝试 {attempt} 次仍未成功：{reason}"
        else:
            message = f"分片 {self.chunk_index + 1} 遇到不可重试错误：{reason}"

        self.stop_event.set()
        self._invoke_download_error(message)

    def _notify_chunk_finished(self):
        QMetaObject.invokeMethod(
            self.parent, "on_chunk_finished",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.file_key),
            Q_ARG(int, self.chunk_index)
        )

    def _interruptible_sleep(self, seconds: float):
        # 分段休眠，保证暂停、取消能够及时生效，而不必等满整个退避时间
        while seconds > 0:
            if self.stop_event.is_set() or not self.parent.is_generation_active(self.generation):
                return

            interval = min(0.1, seconds)

            time.sleep(interval)

            seconds -= interval

    def run(self):
        if self.stop_event.is_set() or not self.parent.is_generation_active(self.generation):
            return

        if self.on_chunk_start:
            self.on_chunk_start()

        try:
            self._download_chunk()
        finally:
            if self.on_chunk_end:
                self.on_chunk_end()

    def _get_offsets(self):
        # 分片断点表由 calc_chunk_list 预先建好，此处只会改写已有键的值
        file_info = self.task_info.Download.files.get(self.file_key)

        if isinstance(file_info, dict):
            offsets = file_info.get("chunk_offsets")

            if isinstance(offsets, dict):
                return offsets

        return None

    def _commit_offset(self, written: int):
        # 记录本分片已 flush 落盘的字节数。只在 flush/close 成功之后调用，
        # 保证记录的断点绝不会超过磁盘上真实存在的数据。
        offsets = self._get_offsets()

        if offsets is None:
            return

        with self.lock:
            offsets[self.offset_key] = written

    def _load_offset(self):
        offsets = self._get_offsets()

        if offsets is None:
            return 0

        with self.lock:
            try:
                return max(min(int(offsets.get(self.offset_key, 0)), self.chunk_size), 0)

            except (TypeError, ValueError):
                return 0

    def _download_chunk(self):
        chunk_start, chunk_end = self.chunk_range

        # 本分片已确认落盘的字节数。重试时从这里断点续传，而不是整片重下：
        # 原先一次网络抖动就会让最多 4MB 已下载的数据作废，界面上直接表现为进度回退。
        # 该值同时会写进任务快照，进程崩溃后重启也能从这里继续，而不是退回到上一个整片边界。
        written = self._load_offset()
        attempt = 0

        while (
            not self.stop_event.is_set()
            and self.parent.is_generation_active(self.generation)
            and attempt < self.max_retries
        ):
            if written >= self.chunk_size:
                # 整片已写满。服务端返回的 Content-Length 大于分片实际剩余时会走到这里，
                # 此时再发请求只会得到一个非法 Range（416），直接按完成处理。
                self._notify_chunk_finished()

                break

            headers = {
                "Range": f"bytes={chunk_start + written}-{chunk_end - 1}"
            }

            downloaded = 0      # 本轮从服务端收到的字节数
            pending = 0         # 已 write 但尚未 flush、因而还不能计入断点的字节数
            expected_size = 0
            flushed = False

            try:
                f = open(self.file_path, "r+b")

                try:
                    f.seek(chunk_start + written)

                    with self.session.stream("GET", self.url, headers = headers, follow_redirects = True, timeout = 10) as response:
                        response.raise_for_status()

                        if written and response.status_code != 206:
                            # 服务端忽略了 Range，续传位置无从谈起，只能整片从头重来
                            with self.lock:
                                self.task_info.Download.downloaded_size = max(self.task_info.Download.downloaded_size - written, 0)

                            written = 0
                            self._commit_offset(0)

                            raise StopIteration("服务端未按 Range 返回 206，分片将从头重新下载")

                        # 获取服务端实际承诺下发的体量。若是最后一个切片且 CDN 数据缩水，它将以实际值为准
                        expected_size = int(response.headers.get("Content-Length", self.chunk_size - written))

                        for chunk in response.iter_bytes(chunk_size = 8192):
                            if (
                                self.stop_event.is_set()
                                or not self.parent.is_generation_active(self.generation)
                            ):
                                break

                            if chunk:
                                chunk_len = len(chunk)
                                if self.token_bucket:
                                    self.token_bucket.consume(chunk_len, self.stop_event)

                                f.write(chunk)
                                downloaded += chunk_len
                                pending += chunk_len

                                with self.lock:
                                    self.task_info.Download.downloaded_size += chunk_len

                                if pending >= self.flush_interval:
                                    # 定期把缓冲区交给操作系统并推进断点，
                                    # 这样崩溃后恢复最多只损失 flush_interval 字节，而不是整个分片
                                    f.flush()

                                    written += pending
                                    pending = 0

                                    self._commit_offset(written)

                finally:
                    # 无论正常结束还是中途抛错，都要先关闭文件（隐含 flush）。
                    # 这一步必须在外层 except 之前完成：关闭成功即代表本轮写入的字节
                    # 确实落盘，可以计入断点，重试时从这里续传而不是整片重下。
                    try:
                        f.close()

                        written += pending
                        pending = 0
                        flushed = True

                        self._commit_offset(written)

                    except Exception:
                        logger.exception("关闭分片文件失败，本轮数据将重新下载: %s", self.file_path)

                # 如果中途被停止，跳出循环退出
                if (
                    self.stop_event.is_set()
                    or not self.parent.is_generation_active(self.generation)
                ):
                    break

                # 检查区块是否真下载到了服务端承诺的大小（原为严格检测 self.chunk_size）
                if downloaded >= expected_size:
                    self._notify_chunk_finished()

                    break
                else:
                    # 提前结束但没有报错，说明连接意外断开，触发重试
                    raise StopIteration(f"Chunk mismatch (Expected: {expected_size}, Got: {downloaded}), triggering retry.")

            except Exception as exc:
                if self.stop_event.is_set():
                    break

                if not flushed and pending:
                    # 文件没能正常关闭，只有最后一次 flush 之后的那部分数据无法确认落盘，
                    # 回退这部分计数并从上一个确认过的断点重来；已 flush 的部分依旧有效
                    with self.lock:
                        self.task_info.Download.downloaded_size = max(self.task_info.Download.downloaded_size - pending, 0)

                attempt += 1
                retryable = self._is_retryable_exception(exc)

                if not retryable or attempt >= self.max_retries:
                    self._report_download_failure(exc, attempt, retryable)
                    break

                self._interruptible_sleep(min(2 ** (attempt - 1), 8))

# 正在销毁流程中的下载器。
#
# ParseWorker / ChunkWorker 都持有 Downloader 的引用，并且是在自己的线程上结束的。
# 一旦 DownloaderManager 已经把它移出字典，最后一个 Python 引用就可能落在工作线程手里，
# 对象随之在工作线程被回收 —— 而它是 GUI 线程的 QObject，成员里还有 QTimer，
# 跨线程析构会触发 "Timers cannot be stopped from another thread" 并破坏 Qt 内部状态。
# 这里在销毁流程期间替它保管一份引用，直到 _finalize_delete 在 GUI 线程上执行完毕。
_pending_delete: set = set()

class Downloader(QObject):
    def __init__(self, task_info: TaskInfo):
        super().__init__()
        self.task_info = task_info
        self.init_session()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(config.get(config.download_thread))

        # 实例化令牌桶（0 为不限速，单位：字节/秒）。此处从已有配置文件中取值或直接扩展
        if config.get(config.speed_limit_enabled):
            rate = config.get(config.speed_limit_rate) * 1024 * 1024
        else:
            rate = 0
        
        self.token_bucket = TokenBucket(rate = rate)

        self.chunk_size = 4 * 1024 * 1024
        self.download_list = {}
        self.merger = None

        # 线程池交由 GUI 线程释放，见 _release_thread_pool
        self._releasing_pool = None

        self._stop_event = Event()
        self.update_lock = Lock()
        self.count_lock = Lock()

        self.active_workers = 0
        self.last_sampled_size = 0
        self.wait_flag = False
        self.wait_callback = None
        self.start_worker_lock = Lock()
        self.start_worker_pending = False
        self.start_worker_requested = False
        self.download_generation = 0
        
        self._completion_triggered = False
        self._download_error_triggered = False

        # ChunkWorker / ParseWorker / _start_worker_in_background 都持有本对象的裸引用，
        # 并在自己的线程上通过 QMetaObject.invokeMethod 回调过来。若在它们跑完之前就
        # deleteLater()，C++ 对象会先一步析构，跨线程的回调就落到已释放的内存上。
        # 这里记录还有多少外部线程持有引用，全部归零后才真正销毁。
        self._ref_lock = Lock()
        self._external_refs = 0
        self._delete_pending = False
        self._delete_finalized = False

        self.last_sampled_time = 0.0

        # 必须挂在本对象的 parent 链上：QTimer 的 affinity 在 GUI 线程，若不设 parent，
        # 它的 C++ 生命周期就完全由 Python wrapper 的引用计数决定。本对象在销毁流程中
        # 仍可能被工作线程持有（FuncRunnable 在调用 _release_ref 之后、被线程池删除之前
        # 一直握着一份引用），一旦 GUI 线程抢先跑完 _finalize_delete，最后一份引用就落在
        # 那个线程，QTimer 会被跨线程析构。设了 parent 之后，它随 deleteLater 一起
        # 由 Qt 在 GUI 线程删除，wrapper 之后在哪回收都不再影响 C++ 对象。
        self.speed_timer = QTimer(self)
        self.speed_timer.setInterval(1000)
        self.speed_timer.timeout.connect(self._calculate_speed)

    def start(self):
        if self.session is None:
            self.init_session()

        self._completion_triggered = False
        self._download_error_triggered = False

        # 如果队列空了则说明下载完成（进度 100）
        if self.task_info.Download.progress >= 100 or (not self.task_info.Download.queue and self.task_info.Download.total_size > 0 and self.task_info.Download.status != DownloadStatus.FAILED):
            self.on_download_completed()
        else:
            download_video = self.task_info.Download.type & DownloadType.VIDEO != 0
            download_audio = self.task_info.Download.type & DownloadType.AUDIO != 0

            if download_video or download_audio:
                self.task_info.Download.status = DownloadStatus.PARSING
                self._stop_event.clear()

                # 对象正在销毁时不再启动解析，否则回调会落到已析构的对象上
                if not self._acquire_ref():
                    return

                # 解析失败会自动重试，等待期间用户可能暂停或取消任务，
                # 因此把停止标记一并交给 worker，让它能及时放弃
                parse_worker = ParseWorker(self.task_info, self, on_finished = self._release_ref, stop_event = self._stop_event)

                try:
                    GlobalThreadPoolTask.run(parse_worker)

                except Exception:
                    self._release_ref()

                    raise
            else:
                self.task_info.Download.info_label = Translator.TIP_MESSAGES("ADDITIONAL_FILES")
                self.update_item(self.task_info)
                self.on_download_completed()

    @Slot(str)
    def on_parse_finished(self, download_info_json: str):
        if self._stop_event.is_set():
            return
        
        download_info = json_loads(download_info_json)
        self.download_list = download_info["download_list"]
        self.task_info.Download.status = DownloadStatus.DOWNLOADING
        self.task_info.Download.total_size = download_info["total_size"]

        # 只有在 files 信息为空时才设置下载队列（说明是第一次物理解析而非断点复拉）
        # 彻底弃用 progress == 0 的判断，防止大文件前 1% 下载途中暂停造成的队列误重置
        if not self.task_info.Download.files:
            self.task_info.Download.queue = download_info["download_queue"]

        self.update_info(download_info)

        self.start_download()

    @Slot(str)
    def on_parse_error(self, error_message: str):
        self._close_session()
        self.task_info.Download.status = DownloadStatus.FAILED

        self.update_item(self.task_info)

        signal_bus.download.auto_manage_concurrent_downloads.emit()

        signal_bus.toast.show_long_message.emit(
            ToastNotificationCategory.ERROR,
            Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
            error_message
        )

    @Slot(str)
    def on_download_error(self, error_message: str):
        if self._download_error_triggered:
            return

        self._download_error_triggered = True
        self.task_info.Download.status = DownloadStatus.FAILED
        self._stop_event.set()

        # 提升代次，令仍排在线程池里的分片作废。否则用户点重试时 start() 会先清掉
        # stop_event，这批旧分片就可能在新代次分配之前被唤醒，拿着已关闭的会话乱写计数。
        with self.start_worker_lock:
            self.download_generation += 1
            self.start_worker_requested = False

        self._close_session()
        self.speed_timer.stop()

        self.update_item(self.task_info)

        signal_bus.download.auto_manage_concurrent_downloads.emit()

        # 
        signal_bus.toast.show_long_message.emit(
            ToastNotificationCategory.ERROR,
            Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
            error_message
        )

    @Slot()
    def start_download(self):
        try:
            if (
                self._stop_event.is_set()
                or self.task_info.Download.status != DownloadStatus.DOWNLOADING
                or not self.task_info.Download.queue
            ):
                return

            self.start_timer()

            with self.start_worker_lock:
                # A small file can finish while its preparation worker is still
                # unwinding. Remember the next-file request instead of dropping it.
                self.start_worker_requested = True

            self._dispatch_start_worker()

        except Exception as e:
            self.on_download_error(str(e))

    @Slot()
    def _dispatch_start_worker(self):
        try:
            with self.start_worker_lock:
                if self.start_worker_pending or not self.start_worker_requested:
                    return

                if (
                    self._stop_event.is_set()
                    or self.task_info.Download.status != DownloadStatus.DOWNLOADING
                    or not self.task_info.Download.queue
                ):
                    self.start_worker_requested = False
                    return

                self.start_worker_requested = False
                self.start_worker_pending = True
                self.download_generation += 1
                generation = self.download_generation

            # 磁盘检查、预分配和启动分片属于准备工作，不能阻塞 GUI 事件循环。
            # 对象正在销毁时直接放弃，避免后台任务回调到已析构的对象上
            if not self._acquire_ref():
                with self.start_worker_lock:
                    self.start_worker_pending = False

                return

            try:
                GlobalThreadPoolTask.run_func(
                    self._start_worker_in_background,
                    generation
                )

            except Exception:
                self._release_ref()

                raise

        except Exception as e:
            with self.start_worker_lock:
                self.start_worker_pending = False
            self.on_download_error(str(e))

    def _start_worker_in_background(self, generation: int):
        try:
            if not self.is_generation_active(generation) or self._stop_event.is_set():
                return

            self.start_worker(generation)
        except Exception as e:
            QMetaObject.invokeMethod(
                self,
                "on_download_error",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, str(e))
            )
        finally:
            with self.start_worker_lock:
                self.start_worker_pending = False
                should_restart = self.start_worker_requested and not self._stop_event.is_set()

            if should_restart:
                QMetaObject.invokeMethod(
                    self,
                    "_dispatch_start_worker",
                    Qt.ConnectionType.QueuedConnection
                )

            self._queue_wait_callback_if_idle()

            # 必须放在最后：释放引用后本对象随时可能被销毁
            self._release_ref()

    def is_generation_active(self, generation: int):
        return generation == self.download_generation

    def start_worker(self, generation: int):
        if (
            not self.task_info.Download.queue
            or not self.is_generation_active(generation)
            or self._stop_event.is_set()
        ):
            return
            
        file_key = self.task_info.Download.queue[0]
        info = self.download_list.get(file_key, {})

        path = Path(self.task_info.File.download_path, self.task_info.File.folder, info.get("file_name", ""))
        path.parent.mkdir(parents = True, exist_ok = True)

        # 计算文件所需空间
        file_size = info.get("file_size", 0)
        file_exists = path.exists()
        current_size = path.stat().st_size if file_exists else 0
        required_space = max(file_size - current_size, 0)

        if not file_exists:
            # 目标文件已不存在（被手动删除或清理工具移除），此前记录的分片进度全部作废。
            # 否则只会补下剩余分片，最终拼出一个中间全是空洞的文件。
            self._reset_file_progress(file_key)

        # 检查磁盘空间并预分配文件
        self._check_disk_space(path, required_space)

        info["file_path"] = path
        chunk_list = self.calc_chunk_list(file_key, file_size, self.chunk_size)
        self.calc_downloaded_size()

        if not chunk_list:
            # 该文件其实已经下载完毕，只是出队记录没能落盘（例如出队前进程被杀）。
            # 直接补做出队并处理下一个文件，切勿重建分片表把整个文件重下一遍。
            QMetaObject.invokeMethod(
                self,
                "on_file_completed",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, file_key)
            )

            return

        # 对于每个区块，启动一个下载线程。区块下载完成后会从 chunk_list 中移除，直到全部完成。
        for chunk_index in chunk_list:
            if (
                not self.is_generation_active(generation)
                or self._stop_event.is_set()
            ):
                break

            chunk_range = self.calc_chunk_range(chunk_index, self.chunk_size, file_size)
            worker = ChunkWorker(
                session = self.session,
                file_key = file_key,
                chunk_index = chunk_index,
                chunk_range = chunk_range,
                file_path = path,
                url = info.get("url", ""),
                referer = self.task_info.Episode.url,
                task_info = self.task_info,
                stop_event = self._stop_event,
                lock = self.update_lock,
                token_bucket = self.token_bucket,
                generation = generation,
                parent = self,
                on_chunk_start = self.on_chunk_start,
                on_chunk_end = self.on_chunk_end
            )
            self.thread_pool.start(worker)

        task_manager.update_async(self.task_info)

    def _reset_file_progress(self, file_key: str):
        file_info = self.task_info.Download.files.get(file_key)

        if not isinstance(file_info, dict):
            return

        with self.update_lock:
            file_info["chunks_list"] = []
            file_info["total_chunks"] = 0
            file_info["finished_chunks"] = 0
            file_info["chunk_offsets"] = {}

    def start_merge(self):
        # 合并失败后可以重试，上一次的 Merger 不再需要。它挂在本对象的 parent 链上，
        # 不主动释放就会一直累积到任务结束
        self._release_merger()

        self.task_info.Download.status = DownloadStatus.MERGING

        self.merger = Merger(self.task_info, parent = self)
        self.merger.start()

    def _release_merger(self):
        # 先停掉 FFmpeg 线程再释放对象：Merger 与其中的 FFmpegRunner 都挂在
        # 本对象的 parent 链上，销毁 Downloader 会连带析构它们，
        # 而销毁一个仍在运行的 QThread 会让 Qt 直接 qFatal 中止进程
        merger = self.merger
        self.merger = None

        if merger is None:
            return

        try:
            merger.stop()
            merger.deleteLater()

        except RuntimeError:
            # C++ 侧已经析构，无需再处理
            pass

    def pause(self):
        with self.start_worker_lock:
            self.download_generation += 1
            self.start_worker_requested = False

        self.task_info.Download.status = DownloadStatus.PAUSED
        self._stop_event.set()

        self._close_session()
        self.speed_timer.stop()

        # 暂停后测速定时器不再触发，这里补一次快照，否则最近一秒内完成的分片不会落盘
        task_manager.update_async(self.task_info)

    def resume(self):
        self.task_info.Download.status = DownloadStatus.DOWNLOADING
        self._stop_event.clear()
        self.start()

    def retry(self):
        match self.task_info.Download.status:
            case DownloadStatus.FAILED:
                self.start()
            case DownloadStatus.FFMPEG_FAILED:
                self.start_merge()

    def calc_chunk_list(self, file_key: str, total_size: int, chunk_size: int) -> list:
        file_info = self.task_info.Download.files[file_key]

        with self.update_lock:
            # 以 total_chunks 判断分片表是否已建立，切勿判断 chunks_list 是否为空：
            # 分片全部完成后 chunks_list 会被清空，按空值重建等于把整个文件当作从未下载过，
            # 崩溃恰好发生在「最后一片完成」与「文件出队」之间时就会整片重下。
            if file_info.get("total_chunks"):
                # 返回副本：调用方会边遍历边启动分片，而 on_chunk_finished 会在 GUI 线程上
                # 从同一个列表里移除已完成的分片，直接遍历原列表会漏启动一部分分片。
                chunk_list = list(file_info.get("chunks_list") or [])

            else:
                total_chunks = (total_size + chunk_size - 1) // chunk_size if total_size > 0 else 0
                if total_chunks == 0:
                    total_chunks = 1

                chunk_list = list(range(total_chunks))
                file_info["total_chunks"] = total_chunks
                file_info["chunks_list"] = chunk_list.copy()

            # 预先为每个分片建好断点条目。ChunkWorker 之后只改写已有键的值，
            # 不会在别的线程序列化任务快照的同时增删键。
            offsets = file_info.get("chunk_offsets")

            if not isinstance(offsets, dict):
                offsets = {}
                file_info["chunk_offsets"] = offsets

            for index in chunk_list:
                offsets.setdefault(str(index), 0)

        return chunk_list

    def calc_chunk_range(self, chunk_index: int, chunk_size: int, total_size: int):
        start = chunk_index * chunk_size
        end = min(start + chunk_size, total_size) if total_size > 0 else 0
        return start, end

    def calc_downloaded_size(self):
        downloaded_size = 0

        with self.update_lock:
            for file_info in self.task_info.Download.files.values():
                total_chunks = file_info.get("total_chunks", 0)
                file_size = file_info.get("file_size", 0)
                chunks_list = file_info.get("chunks_list", [])
                offsets = file_info.get("chunk_offsets") or {}

                if total_chunks > 0:
                    remaining = set(chunks_list)

                    for i in range(total_chunks):
                        start = i * self.chunk_size
                        end = min(start + self.chunk_size, file_size) if file_size > 0 else 0

                        if i not in remaining:
                            # 已完整下载的区块，累加其实际大小
                            downloaded_size += (end - start)

                        else:
                            # 未完成的区块也把已确认落盘的部分算进来，
                            # 否则恢复下载时进度会退回到上一个整片边界
                            try:
                                offset = int(offsets.get(str(i), 0))

                            except (TypeError, ValueError):
                                offset = 0

                            downloaded_size += max(min(offset, end - start), 0)

            self.task_info.Download.downloaded_size = downloaded_size
    
    @Slot(str, int)
    def on_chunk_finished(self, file_key: str, chunk_index: int):
        with self.update_lock:
            file_info = self.task_info.Download.files.get(file_key, {})
            if chunk_index in file_info.get("chunks_list", []):
                file_info["finished_chunks"] += 1
                file_info["chunks_list"].remove(chunk_index)

            # 以剩余分片是否为空判断文件是否下载完成。finished_chunks 只是展示用的计数，
            # 一旦因为历史数据异常而与实际分片数对不上，就会提前把文件判定为完成。
            file_completed = file_info.get("total_chunks", 0) > 0 and not file_info.get("chunks_list")

        if file_completed:
            self.on_file_completed(file_key)
            return

        task_manager.update_async(self.task_info)

        # 若队列全空，且任务没被暂停/取消，意味着所有文件下载完成
        if not self.task_info.Download.queue and self.task_info.Download.status == DownloadStatus.DOWNLOADING:
            self.on_download_completed()

    @Slot(str)
    def on_file_completed(self, file_key: str):
        # 出队必须与分片状态在同一个快照里落盘。若先写库再出队，崩溃窗口内保存下来的记录
        # 会是「分片全部完成但文件仍在队列中」，重启后该文件会被当作从未下载过而整片重下。
        if file_key in self.task_info.Download.queue:
            self.task_info.Download.queue.remove(file_key)

        task_manager.update_async(self.task_info)

        if self.task_info.Download.queue and not self._stop_event.is_set():
            self.start_download()
            return

        if not self.task_info.Download.queue and self.task_info.Download.status == DownloadStatus.DOWNLOADING:
            self.on_download_completed()

    def update_info(self, download_info: dict):
        if not self.task_info.Download.files:
            self.task_info.Download.files = {
                file_key: {
                    "chunks_list": [],
                    "total_chunks": 0,
                    "finished_chunks": 0,
                    "chunk_offsets": {},
                    "file_size": download_info["download_list"][file_key].get("file_size", 0)
                } for file_key in download_info["download_queue"]
            }

            has_video = self.task_info.Download.type & DownloadType.VIDEO != 0
            has_audio = self.task_info.Download.type & DownloadType.AUDIO != 0

            if has_video and has_audio:
                self.task_info.Download.info_label = Translator.VIDEO_QUALITY(reversed_video_quality_map.get(self.task_info.Download.video_quality_id, ""))

            elif has_video and not has_audio:
                if self.task_info.Download.media_type == MediaType.MP4:
                    self.task_info.Download.info_label = "MP4"
                    
                elif self.task_info.Download.media_type == MediaType.FLV:
                    self.task_info.Download.info_label = "FLV"

            elif not has_video and has_audio:
                self.task_info.Download.info_label = self.tr("Audio")

            task_manager._update_media_info(self.task_info)

    def init_session(self):
        # SSL 上下文全局复用，避免每次创建 Client 时重新加载 CA 证书（约 170ms，且发生在 GUI 线程）
        ssl_context = get_ssl_context()

        limits = httpx.Limits(max_keepalive_connections = config.get(config.download_thread), max_connections = config.get(config.download_thread))
        transport = httpx.HTTPTransport(retries = 5, verify = ssl_context)
        # 与解析请求共用同一套代理模式判定
        mounts = get_proxy_mounts()

        headers = {
            "Referer": self.task_info.Episode.url,
            "User-Agent": config.get(config.user_agent)
        }

        self.session = httpx.Client(
            limits = limits,
            transport = transport,
            mounts = mounts,
            headers = headers,
            verify = ssl_context
        )

        cookies = get_cookies()

        for key, value in cookies.items():
            self.session.cookies.set(name = key, value = value, domain = ".bilibili.com", path = "/")

    def on_download_completed(self):
        # 防抖设定，避免队列完成以及进度到 100 时重复触发
        if getattr(self, "_completion_triggered", False):
            return
        
        self._completion_triggered = True
        
        self.task_info.Download.status = DownloadStatus.DOWNLOADING
        self.task_info.Download.speed = 0
        self.task_info.Download.progress = 100

        danmaku = self.task_info.Download.type & DownloadType.DANMAKU != 0
        subtitles = self.task_info.Download.type & DownloadType.SUBTITLE != 0
        cover = self.task_info.Download.type & DownloadType.COVER != 0
        metadata = self.task_info.Download.type & DownloadType.METADATA != 0
        chapter = ChapterParser.is_available(self.task_info)

        if any([danmaku, subtitles, cover, metadata, chapter]):
            self.task_info.Download.status = DownloadStatus.ADDITIONAL_PROCESSING

            # 附加内容解析同样跑在独立线程上，并且回调本对象，
            # 必须与 ParseWorker 一样纳入引用计数，否则销毁流程不会等它结束
            if not self._acquire_ref():
                return

            worker = AdditionalParseWorker(self.task_info)
            worker.success.connect(self.wait_merge)
            worker.error.connect(self.on_parse_error)
            worker.finished.connect(self._release_ref)

            try:
                AsyncTask.run(worker)

            except Exception:
                self._release_ref()

                raise
        else:
            self.wait_merge()

    def wait_merge(self):
        self.task_info.Download.status = DownloadStatus.FFMPEG_QUEUED

        self._stop_event.set()
        self._close_session()
        self.speed_timer.stop()

        task_manager.update_async(self.task_info)
        signal_bus.download.auto_manage_concurrent_downloads.emit()

    def on_chunk_start(self):
        with self.count_lock:
            self.active_workers += 1

    def on_chunk_end(self):
        with self.count_lock:
            self.active_workers -= 1

        self._queue_wait_callback_if_idle()

    def wait(self, on_end):
        self._stop_event.set()

        with self.start_worker_lock:
            self.download_generation += 1
            self.start_worker_requested = False

        with self.count_lock:
            self.wait_flag = True
            self.wait_callback = on_end

        self._finish_wait_if_idle()

    def _queue_wait_callback_if_idle(self):
        with self.count_lock:
            should_check = self.wait_flag and self.active_workers == 0

        if should_check:
            QMetaObject.invokeMethod(
                self,
                "_finish_wait_if_idle",
                Qt.ConnectionType.QueuedConnection
            )

    @Slot()
    def _finish_wait_if_idle(self):
        with self.start_worker_lock:
            if self.start_worker_pending:
                return

        with self.count_lock:
            if not self.wait_flag or self.active_workers != 0:
                return

            callback = self.wait_callback
            self.wait_flag = False
            self.wait_callback = None

        if callback:
            callback()

    def start_timer(self):
        if self.speed_timer.isActive():
            return

        self.last_sampled_size = self.task_info.Download.downloaded_size
        self.last_sampled_time = time.monotonic()
        self.speed_timer.start()

    def _calculate_speed(self):
        with self.update_lock:
            current_size = self.task_info.Download.downloaded_size

        # 按实际经过的时间折算。QTimer 只保证不早于 1s 触发，界面繁忙时
        # 间隔会明显拉长，直接拿差值当速度会把瞬时速度显示得偏高。
        now = time.monotonic()
        elapsed = now - self.last_sampled_time if self.last_sampled_time else 1.0
        self.last_sampled_time = now

        delta = current_size - self.last_sampled_size
        self.task_info.Download.speed = int(delta / elapsed) if elapsed > 0 and delta > 0 else 0

        total = getattr(self.task_info.Download, "total_size", 0)
        self.task_info.Download.progress = int(current_size / total * 100) if total > 0 else 100
        self.last_sampled_size = current_size

        self.update_item(self.task_info)

        # timer 的定期检查：如果队列为空且处于 DOWNLOADING 状态可以尝试转移到合并步骤
        if not self.task_info.Download.queue and self.task_info.Download.status == DownloadStatus.DOWNLOADING:
            self.on_download_completed()

    def shutdown(self):
        """
        进程退出前的快速收敛：让后台线程尽早停下来，但不销毁本对象

        与 on_delete 的区别是不走引用计数与销毁流程 —— 进程马上就要结束，
        对象由操作系统回收，这里只需保证没有线程还在读写文件和网络。
        """
        self._stop_event.set()

        with self.start_worker_lock:
            self.download_generation += 1
            self.start_worker_requested = False

        self.speed_timer.stop()

        pool = self.thread_pool

        if pool is not None:
            # 丢弃尚未开始的分片，已在运行的分片会因为会话关闭而立即出错退出
            pool.clear()

        # 关闭会话后阻塞在 socket 读上的分片会立刻返回，
        # 否则退出流程要一直等到读超时（5s）才能推进
        self._close_session()

        self._release_merger()

    def on_delete(self):
        # 在移出管理器之前先登记，保证销毁期间始终有一份来自 GUI 线程的引用
        _pending_delete.add(self)

        self._stop_event.set()

        # 提升代次，令仍在运行的分片线程尽快退出，并且不再回调本对象
        with self.start_worker_lock:
            self.download_generation += 1
            self.start_worker_requested = False

        self.speed_timer.stop()

        # 必须赶在 deleteLater 之前停掉 FFmpeg，否则销毁 parent 链时
        # 会析构仍在运行的 FFmpegRunner
        self._release_merger()

        with self._ref_lock:
            self._delete_pending = True

            # 线程池释放线程本身也算一个持有者，保证下面至少会触发一次归零检查。
            # 这里必须直接自增：_delete_pending 已经置位，_acquire_ref 会拒绝
            self._external_refs += 1

        # 关闭会话要等连接池释放，批量取消时逐个在 GUI 线程上关闭会让界面卡住数秒，
        # 因此与线程池的等待一并放到后台线程执行
        self._release_thread_pool()

    def _acquire_ref(self):
        """
        登记一个外部持有者，成功返回 True

        销毁流程一旦启动就必须拒绝：此时 _finalize_delete 可能已经排在 GUI 事件队列里，
        再放行新的后台任务，任务结束时回调的就是已经析构的 C++ 对象，
        跨线程的 invokeMethod 会落到已释放的内存上。
        """
        with self._ref_lock:
            if self._delete_pending or self._delete_finalized:
                return False

            self._external_refs += 1

            return True

    def _release_ref(self):
        with self._ref_lock:
            self._external_refs -= 1

            should_finalize = (
                self._delete_pending
                and self._external_refs <= 0
                and not self._delete_finalized
            )

            if should_finalize:
                self._delete_finalized = True

        if should_finalize:
            # 销毁必须回到对象所属的 GUI 线程执行
            QMetaObject.invokeMethod(
                self,
                "_finalize_delete",
                Qt.ConnectionType.QueuedConnection
            )

    @Slot()
    def _finalize_delete(self):
        # 本槽是排队执行的，从决定销毁到真正执行之间隔着一轮事件循环。
        # 期间若又有持有者登记进来，必须放弃本次销毁，改由最后一个持有者释放时重新触发，
        # 否则 C++ 对象会先于仍在运行的后台任务析构
        with self._ref_lock:
            if self._external_refs > 0:
                self._delete_finalized = False

                return

        self.task_info = None
        self.download_list = None

        # 线程池已经跑完，在本线程（GUI 线程）上释放
        self._releasing_pool = None

        self.deleteLater()

        # 放在最后：本槽运行在 GUI 线程上，此处释放最后一份引用，
        # 后续的 Python 回收就不会发生在工作线程里
        _pending_delete.discard(self)

    def _release_thread_pool(self):
        # QThreadPool 析构时会调用 waitForDone()。若在 GUI 线程上释放引用，
        # 界面会一直卡到所有分片线程退出为止（实测可达数秒），因此改到后台线程释放。
        pool = self.thread_pool
        self.thread_pool = None

        # QThreadPool 的 affinity 在 GUI 线程。若只由下面的闭包持有，闭包结束时
        # 它就会在那个裸线程里被回收，等于跨线程析构一个 QObject。
        # 这里替它保管一份引用，改由 _finalize_delete 在 GUI 线程上释放。
        self._releasing_pool = pool

        if pool is None:
            self._close_session()
            self._release_ref()

            return

        # 丢弃尚未开始的分片任务，只需等待已在运行的部分
        pool.clear()

        # 闭包只捕获这个容器，不直接持有线程池，以便在释放引用计数之前主动放手，
        # 原因见下方 release() 中的说明
        holder = [pool]

        def release():
            try:
                # 先断开连接，正在读取响应的分片会立即出错退出，无需等到读超时
                self._close_session()

                holder[0].waitForDone()

            except Exception:
                logger.exception("等待下载线程池退出时发生异常")

            finally:
                # 必须先放弃本线程对线程池的引用，再释放引用计数。
                #
                # _release_ref() 会把 _finalize_delete 排进 GUI 线程的事件队列，而本函数
                # 返回后 Thread.run() 会清掉 _target，连带释放闭包持有的这份引用。两者相差
                # 只有几微秒：若 GUI 线程抢先执行完 _finalize_delete（把 _releasing_pool 置空），
                # 最后一份引用就落在本线程手里，QThreadPool 会在这个裸线程里析构 ——
                # 它的 affinity 在 GUI 线程，跨线程析构会动到 removePostedEvents 和线程数据，
                # 正是 GUI 线程此刻在遍历的结构，表现为主线程在事件循环中访问违例，
                # 且 Python 栈上不留任何线索。
                #
                # 主窗口最小化时 GUI 线程几乎空闲，排队的槽会被立即处理，反而更容易撞上。
                holder[0] = None

                # 分片线程已全部退出，不会再有人回调本对象
                self._release_ref()

        thread = Thread(target = release, name = "downloader-pool-release", daemon = True)
        thread.start()

    def _close_session(self):
        session = self.session
        self.session = None

        if session is None:
            return

        try:
            session.close()

        except Exception:
            logger.exception("无法关闭 HTTP 会话，可能存在资源泄漏风险")
    
    def update_item(self, task_info: TaskInfo):
        signal_bus.download.update_downloading_item.emit(task_info)
        task_manager.update_async(self.task_info)

    def _check_disk_space(self, path: Path, file_size: int):
        if not Directory.has_enough_space(path.parent, file_size):
            error_message = Translator.ERROR_MESSAGES("INSUFFICIENT_SPACE")

            raise OSError(error_message)
            
        if not path.exists() and file_size > 0:
            # 预分配文件空间
            if config.get(config.preallocate_file_space):
                File.preallocate_file(path, file_size)

            else:
                # 关闭预分配时，仅创建空文件占位
                File.create_placeholder(path)
