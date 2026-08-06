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
from ...thread.pool import GlobalThreadPoolTask
from ...network.request import get_cookies, get_mounts, get_ssl_context
from ...network.proxy import Proxy
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

    def _download_chunk(self):
        chunk_start, chunk_end = self.chunk_range

        # 本分片已确认落盘的字节数。重试时从这里断点续传，而不是整片重下：
        # 原先一次网络抖动就会让最多 4MB 已下载的数据作废，界面上直接表现为进度回退。
        written = 0
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

            downloaded = 0
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

                                with self.lock:
                                    self.task_info.Download.downloaded_size += chunk_len

                finally:
                    # 无论正常结束还是中途抛错，都要先关闭文件（隐含 flush）。
                    # 这一步必须在外层 except 之前完成：关闭成功即代表本轮写入的字节
                    # 确实落盘，可以计入断点，重试时从这里续传而不是整片重下。
                    try:
                        f.close()

                        written += downloaded
                        flushed = True

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

                if not flushed:
                    # 文件没能正常关闭，无法确认这批数据是否真的落盘，
                    # 回退计数并从上一个确认过的断点重来
                    with self.lock:
                        self.task_info.Download.downloaded_size = max(self.task_info.Download.downloaded_size - downloaded, 0)

                attempt += 1
                retryable = self._is_retryable_exception(exc)

                if not retryable or attempt >= self.max_retries:
                    self._report_download_failure(exc, attempt, retryable)
                    break

                self._interruptible_sleep(min(2 ** (attempt - 1), 8))

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

        self.speed_timer = QTimer()
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

                parse_worker = ParseWorker(self.task_info, self, on_finished = self._release_ref)

                self._acquire_ref()

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
            self._acquire_ref()

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
        current_size = path.stat().st_size if path.exists() else 0
        required_space = max(file_size - current_size, 0)

        # 检查磁盘空间并预分配文件
        self._check_disk_space(path, required_space)

        info["file_path"] = path
        chunk_list = self.calc_chunk_list(file_key, file_size, self.chunk_size)
        self.calc_downloaded_size()

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

    def start_merge(self):
        self.task_info.Download.status = DownloadStatus.MERGING
        merge_worker = Merger(self.task_info, parent=self)
        merge_worker.start()

    def pause(self):
        with self.start_worker_lock:
            self.download_generation += 1
            self.start_worker_requested = False

        self.task_info.Download.status = DownloadStatus.PAUSED
        self._stop_event.set()

        self._close_session()
        self.speed_timer.stop()

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
        if chunk_list := file_info.get("chunks_list"):
            return chunk_list
        
        total_chunks = (total_size + chunk_size - 1) // chunk_size if total_size > 0 else 0
        if total_chunks == 0:
            total_chunks = 1
            
        chunk_list = list(range(total_chunks))
        file_info["total_chunks"] = total_chunks
        file_info["chunks_list"] = chunk_list.copy()
        return chunk_list

    def calc_chunk_range(self, chunk_index: int, chunk_size: int, total_size: int):
        start = chunk_index * chunk_size
        end = min(start + chunk_size, total_size) if total_size > 0 else 0
        return start, end

    def calc_downloaded_size(self):
        downloaded_size = 0
        
        for file_info in self.task_info.Download.files.values():
            total_chunks = file_info.get("total_chunks", 0)
            file_size = file_info.get("file_size", 0)
            chunks_list = file_info.get("chunks_list", [])

            if total_chunks > 0:
                # 只累加确实已经完全下载完成的区块的实际大小
                for i in range(total_chunks):
                    if i not in chunks_list:
                        start = i * self.chunk_size
                        end = min(start + self.chunk_size, file_size) if file_size > 0 else 0
                        downloaded_size += (end - start)

        with self.update_lock:
            self.task_info.Download.downloaded_size = downloaded_size
    
    @Slot(str, int)
    def on_chunk_finished(self, file_key: str, chunk_index: int):
        with self.update_lock:
            file_info = self.task_info.Download.files.get(file_key, {})
            if chunk_index in file_info.get("chunks_list", []):
                file_info["finished_chunks"] += 1
                file_info["chunks_list"].remove(chunk_index)

            total = file_info.get("total_chunks", 1)
            current_progress = int((file_info.get("finished_chunks", 0) / total) * 100) if total > 0 else 100

        task_manager.update_async(self.task_info)

        if current_progress >= 100:
            if file_key in self.task_info.Download.queue:
                self.task_info.Download.queue.remove(file_key)

            if self.task_info.Download.queue and not self._stop_event.is_set():
                self.start_download()
                return

        # 若队列全空，且任务没被暂停/取消，意味着所有文件下载完成
        if not self.task_info.Download.queue and self.task_info.Download.status == DownloadStatus.DOWNLOADING:
            self.on_download_completed()

    def update_info(self, download_info: dict):
        if not self.task_info.Download.files:
            self.task_info.Download.files = {
                file_key: {
                    "chunks_list": [],
                    "total_chunks": 0,
                    "finished_chunks": 0,
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
        mounts = get_mounts(Proxy().get_proxies())

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

        if any([danmaku, subtitles, cover, metadata]):
            self.task_info.Download.status = DownloadStatus.ADDITIONAL_PROCESSING
            
            worker = AdditionalParseWorker(self.task_info)
            worker.success.connect(self.wait_merge)
            worker.error.connect(self.on_parse_error)
            AsyncTask.run(worker)
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

    def on_delete(self):
        self._stop_event.set()

        # 提升代次，令仍在运行的分片线程尽快退出，并且不再回调本对象
        with self.start_worker_lock:
            self.download_generation += 1
            self.start_worker_requested = False

        self._close_session()
        self.speed_timer.stop()

        with self._ref_lock:
            self._delete_pending = True

        # 线程池释放线程本身也算一个持有者，保证下面至少会触发一次归零检查
        self._acquire_ref()
        self._release_thread_pool()

    def _acquire_ref(self):
        with self._ref_lock:
            self._external_refs += 1

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
        self.task_info = None
        self.download_list = None

        self.deleteLater()

    def _release_thread_pool(self):
        # QThreadPool 析构时会调用 waitForDone()。若在 GUI 线程上释放引用，
        # 界面会一直卡到所有分片线程退出为止（实测可达数秒），因此改到后台线程释放。
        pool = self.thread_pool
        self.thread_pool = None

        if pool is None:
            self._release_ref()

            return

        # 丢弃尚未开始的分片任务，只需等待已在运行的部分
        pool.clear()

        def release():
            try:
                pool.waitForDone()

            except Exception:
                logger.exception("等待下载线程池退出时发生异常")

            finally:
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
