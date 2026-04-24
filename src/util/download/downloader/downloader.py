from PySide6.QtCore import QRunnable, QThreadPool, QObject, QTimer, Slot, QMetaObject, Q_ARG
from PySide6.QtCore import Qt

from util.common.enum import DownloadStatus, DownloadType, MediaType
from util.parse.additional.worker import AdditionalParseWorker
from util.common import signal_bus, config, Translator, File
from util.thread import GlobalThreadPoolTask, AsyncTask
from util.common.data import reversed_video_quality_map
from util.network import get_cookies

from ..task.info import TaskInfo
from ..task.manager import task_manager
from .parse_worker import ParseWorker
from .merger import Merger

from threading import Event, Lock
from pathlib import Path
import httpx
import json
import time

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
    def __init__(self, session: httpx.Client, file_key: str, chunk_index: int, chunk_range: tuple[int, int], file_path: Path, url: str, referer: str, task_info: TaskInfo, stop_event: Event, lock: Lock, token_bucket: TokenBucket, parent=None, on_chunk_start=None, on_chunk_end=None):
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
        self.parent = parent
        self.on_chunk_start = on_chunk_start
        self.on_chunk_end = on_chunk_end

    def run(self):
        if self.stop_event.is_set():
            return
        
        if self.on_chunk_start:
            self.on_chunk_start()
            
        headers = {
            "Range": f"bytes={self.chunk_range[0]}-{self.chunk_range[1] - 1}"
        }

        while not self.stop_event.is_set():
            downloaded = 0
            try:
                with open(self.file_path, "r+b") as f:
                    f.seek(self.chunk_range[0])

                    with self.session.stream("GET", self.url, headers = headers, follow_redirects = True, timeout = 10) as response:
                        response.raise_for_status()

                        # 获取服务端实际承诺下发的体量。若是最后一个切片且 CDN 数据缩水，它将以实际值为准
                        expected_size = int(response.headers.get("Content-Length", self.chunk_size))
                        
                        for chunk in response.iter_bytes(chunk_size = 8192):
                            if self.stop_event.is_set():
                                break
                            
                            if chunk:
                                chunk_len = len(chunk)
                                if self.token_bucket:
                                    self.token_bucket.consume(chunk_len, self.stop_event)

                                f.write(chunk)
                                downloaded += chunk_len
                                
                                with self.lock:
                                    self.task_info.Download.downloaded_size += chunk_len
                                    
                # 如果中途被停止，跳出循环退出
                if self.stop_event.is_set():
                    break
                    
                # 检查区块是否真下载到了服务端承诺的大小（原为严格检测 self.chunk_size）
                if downloaded >= expected_size:
                    QMetaObject.invokeMethod(
                        self.parent, "on_chunk_finished",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, self.file_key),
                        Q_ARG(int, self.chunk_index)
                    )
                    break
                else:
                    # 提前结束但没有报错，说明连接意外断开，触发重试
                    raise StopIteration(f"Chunk mismatch (Expected: {expected_size}, Got: {downloaded}), triggering retry.")

            except Exception:
                if self.stop_event.is_set():
                    break
                
                # 发生异常（断网、超时等），清空本轮的下载计数并等待后重试（区块从头下）
                with self.lock:
                    self.task_info.Download.downloaded_size -= downloaded

                time.sleep(1)

        if self.on_chunk_end:
            self.on_chunk_end()

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
        
        self._completion_triggered = False

        self.speed_timer = QTimer()
        self.speed_timer.setInterval(1000)
        self.speed_timer.timeout.connect(self._calculate_speed)

    def start(self):
        self._completion_triggered = False

        # 如果队列空了则说明下载完成（进度 100）
        if self.task_info.Download.progress >= 100 or (not self.task_info.Download.queue and self.task_info.Download.total_size > 0 and self.task_info.Download.status != DownloadStatus.FAILED):
            self.on_download_completed()
        else:
            download_video = self.task_info.Download.type & DownloadType.VIDEO != 0
            download_audio = self.task_info.Download.type & DownloadType.AUDIO != 0

            if download_video or download_audio:
                self.task_info.Download.status = DownloadStatus.PARSING
                self._stop_event.clear()

                parse_worker = ParseWorker(self.task_info, self)
                GlobalThreadPoolTask.run(parse_worker)
            else:
                self.task_info.Download.info_label = Translator.TIP_MESSAGES("ADDITIONAL_FILES")
                self.update_item(self.task_info)
                self.on_download_completed()

    @Slot(str)
    def on_parse_finished(self, download_info_json: str):
        if self._stop_event.is_set():
            return
        
        download_info = json.loads(download_info_json)
        self.download_list = download_info["download_list"]
        self.task_info.Download.status = DownloadStatus.DOWNLOADING
        self.task_info.Download.total_size = download_info["total_size"]

        # 只有在 files 信息为空时才设置下载队列（说明是第一次物理解析而非断点复拉）
        # 彻底弃用 progress == 0 的判断，防止大文件前 1% 下载途中暂停造成的队列误重置
        if not self.task_info.Download.files:
            self.task_info.Download.queue = download_info["download_queue"]

        self.update_info(download_info)
        self.start_worker()
        self.start_timer()

    @Slot(str)
    def on_parse_error(self, error_message: str):
        self.task_info.Download.status = DownloadStatus.FAILED
        self.update_item(self.task_info)
        signal_bus.download.auto_manage_concurrent_downloads.emit()
        signal_bus.toast.show_long_message.emit(
            Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
            error_message
        )

    def start_worker(self):
        if not self.task_info.Download.queue:
            return
            
        file_key = self.task_info.Download.queue[0]
        info = self.download_list.get(file_key, {})

        path = Path(self.task_info.File.download_path, self.task_info.File.folder, info.get("file_name", ""))
        path.parent.mkdir(parents = True, exist_ok = True)

        file_size = info.get("file_size", 0)
        if not path.exists() and file_size > 0:
            File.preallocate_file(path, file_size)

        info["file_path"] = path
        chunk_list = self.calc_chunk_list(file_key, file_size, self.chunk_size)
        self.calc_downloaded_size()

        for chunk_index in chunk_list:
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
                parent = self,
                on_chunk_start = self.on_chunk_start,
                on_chunk_end = self.on_chunk_end
            )
            self.thread_pool.start(worker)

        task_manager.update(self.task_info)

    def start_merge(self):
        self.task_info.Download.status = DownloadStatus.MERGING
        merge_worker = Merger(self.task_info, parent=self)
        merge_worker.start()

    def pause(self):
        self.task_info.Download.status = DownloadStatus.PAUSED
        self._stop_event.set()
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

        task_manager.update(self.task_info)

        if current_progress >= 100:
            if file_key in self.task_info.Download.queue:
                self.task_info.Download.queue.remove(file_key)

            if self.task_info.Download.queue and not self._stop_event.is_set():
                self.start_worker()
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
        limits = httpx.Limits(max_keepalive_connections = config.get(config.download_thread), max_connections = config.get(config.download_thread))
        transport = httpx.HTTPTransport(retries = 5)

        headers = {
            "Referer": self.task_info.Episode.url,
            "User-Agent": config.get(config.user_agent)
        }

        self.session = httpx.Client(
            limits = limits,
            transport = transport,
            headers = headers
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
        self.session.close()
        self.speed_timer.stop()

        task_manager.update(self.task_info)
        signal_bus.download.auto_manage_concurrent_downloads.emit()

    def on_chunk_start(self):
        with self.count_lock:
            self.active_workers += 1

    def on_chunk_end(self):
        with self.count_lock:
            self.active_workers -= 1

        if self.active_workers == 0 and self.wait_flag and self._stop_event.is_set():
            self.wait_callback()

    def wait(self, on_end):
        self.wait_flag = True
        self.wait_callback = on_end
        self._stop_event.set()

        if self.active_workers == 0:
            on_end()

    def start_timer(self):
        self.last_sampled_size = self.task_info.Download.downloaded_size
        self.speed_timer.start()

    def _calculate_speed(self):
        with self.update_lock:
            current_size = self.task_info.Download.downloaded_size

        speed = current_size - self.last_sampled_size
        self.task_info.Download.speed = speed if speed > 0 else 0
        total = getattr(self.task_info.Download, "total_size", 0)
        self.task_info.Download.progress = int(current_size / total * 100) if total > 0 else 100
        self.last_sampled_size = current_size

        self.update_item(self.task_info)

        # timer 的定期检查：如果队列为空且处于 DOWNLOADING 状态可以尝试转移到合并步骤
        if not self.task_info.Download.queue and self.task_info.Download.status == DownloadStatus.DOWNLOADING:
            self.on_download_completed()

    def on_delete(self):
        self.session = None
        self.thread_pool = None
        self.task_info = None
        self.download_list = None
        self.deleteLater()
    
    def update_item(self, task_info: TaskInfo):
        signal_bus.download.update_downloading_item.emit(task_info)
        task_manager.update(self.task_info)