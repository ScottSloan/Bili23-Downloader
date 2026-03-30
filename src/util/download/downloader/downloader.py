from PySide6.QtCore import QRunnable, QThreadPool, QObject, QTimer, Slot, QMetaObject, Q_ARG
from PySide6.QtCore import Qt

from util.parse.additional.worker import AdditionalParseWorker
from util.download.downloader.parse_worker import ParseWorker
from util.common import signal_bus, config, Translator, File
from util.common.enum import DownloadStatus, DownloadType
from util.common.data import reversed_video_quality_map
from util.thread import GlobalThreadPoolTask, AsyncTask
from util.download.task.manager import task_manager
from util.download.downloader.merger import Merger
from util.network.request import get_cookies
from util.download.task.info import TaskInfo

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from threading import Event, Lock
from pathlib import Path
import requests
import json

class ChunkWorker(QRunnable):
    def __init__(self, session: requests.Session, chunk_index: int, chunk_range: tuple[int, int], file_name: str, file_path: Path, url: str, referer: str, task_info: TaskInfo, stop_event: Event, lock: Lock, parent = None, on_chunk_start = None, on_chunk_end = None):
        super().__init__()
    
        self.session = session
        self.chunk_index = chunk_index
        self.chunk_range = chunk_range
        self.chunk_size = chunk_range[1] - chunk_range[0]
        self.url = url
        self.referer = referer
        self.task_info = task_info
        self.file_name = file_name
        self.file_path = file_path
        self.stop_event = stop_event
        self.lock = lock

        self.parent = parent
        self.on_chunk_start = on_chunk_start
        self.on_chunk_end = on_chunk_end
        self.downloaded_chunk_size = 0
        self.finish_flag = False

    def run(self):
        if self.stop_event.is_set():
            return
        
        self.downloaded_chunk_size = 0

        if self.on_chunk_start:
            self.on_chunk_start()

        self.range_download()

        if not self.finish_flag and not self.stop_event.is_set():
            # 重新下载该区块
            self.run()
            return
        
        if self.on_chunk_end:
            self.on_chunk_end()

        if self.finish_flag:
            self.on_finished()

    def on_finished(self):
        QMetaObject.invokeMethod(
            self.parent,
            "on_chunk_finished",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, self.chunk_index)
        )

    def range_download(self):
        with open(self.file_path, "r+b") as f:
            f.seek(self.chunk_range[0])

            with self.session.get(self.url, headers = self.get_headers(), stream = True) as response:
                for chunk in response.iter_content(chunk_size = 8192):
                    if chunk:
                        f.write(chunk)

                        self.downloaded_chunk_size += len(chunk)

                        with self.lock:
                            self.task_info.Download.downloaded_size += len(chunk)

                        if self.stop_event.is_set():
                            break

        if self.downloaded_chunk_size >= self.chunk_size:
            # 如果区块没有下载完全，标志位就不会被设置
            self.finish_flag = True

    def get_headers(self):
        return {
            "Range": f"bytes={self.chunk_range[0]}-{self.chunk_range[1] - 1}"
        }

class Downloader(QObject):
    def __init__(self, task_info: TaskInfo):
        super().__init__()

        self.task_info = task_info

        self.init_session()

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(config.get(config.download_thread))

        self.chunk_size = 4 * 1024 * 1024
        self.download_list = {}

        self._stop_event = Event()
        self.update_lock = Lock()
        self.count_lock = Lock()

        self.active_workers = 0
        self.last_sampled_size = 0
        self.wait_flag = False
        self.wait_callback = None

        self.speed_timer = QTimer()
        self.speed_timer.setInterval(1000)
        self.speed_timer.timeout.connect(self._calculate_speed)

    def start(self):
        # 如果下载已经完成，就直接进入合并阶段
        if self.task_info.Download.progress >= 100:
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
                # 如果不需要下载视频和音频，就直接进入进入合并阶段
                self.task_info.Download.info_label = "附加文件"

                self.update_item(self.task_info)

                self.on_download_completed()

    @Slot(str)
    def on_parse_finished(self, download_info_json: str):
        # 只有解析下载链接后才真正开始下载
        
        if self._stop_event.is_set():
            # 如果在解析过程中任务被取消了，就不继续执行了
            return
        
        download_info = json.loads(download_info_json)

        self.download_list = download_info["download_list"]
        self.task_info.Download.status = DownloadStatus.DOWNLOADING

        self.task_info.Download.total_size = download_info["total_size"]
        self.task_info.Download.queue = download_info["download_queue"]

        self.update_info(download_info)

        self.start_worker()

        self.start_timer()

    @Slot(str)
    def on_parse_error(self, error_message: str):
        self.task_info.Download.status = DownloadStatus.FAILED

        self.update_item(self.task_info)

        signal_bus.download.start_next_task.emit()

        signal_bus.toast.show_long_message.emit(
            Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
            error_message
        )

    def start_worker(self):
        info = self.get_download_info()

        file_total_size = info["file_size"]

        chunk_list = self.calc_chunk_list(file_total_size, self.chunk_size)

        self.calc_downloaded_size()

        for chunk_index in chunk_list:
            chunk_range = self.calc_chunk_range(chunk_index, self.chunk_size, file_total_size)

            worker_data = {
                "session": self.session,
                "file_name": info["file_name"],
                "file_path": info["file_path"],
                "url": info["url"],
                "referer": self.task_info.Episode.url,
                "chunk_index": chunk_index,
                "chunk_range": chunk_range,
                "task_info": self.task_info,
                "parent": self,
                "on_chunk_start": self.on_chunk_start,
                "on_chunk_end": self.on_chunk_end,
                "stop_event": self._stop_event,
                "lock": self.update_lock
            }

            worker = ChunkWorker(**worker_data)
            self.thread_pool.start(worker)

        task_manager.update(self.task_info)

    def start_merge(self):
        self.task_info.Download.status = DownloadStatus.MERGING

        merge_worker = Merger(self.task_info, parent = self)
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

    def calc_chunk_list(self, total_size: int, chunk_size: int):
        if chunk_list := self.task_info.Download.files[self.current_queue_key]["chunks_list"]:
            return chunk_list
        
        else:
            total_chunks = (total_size + chunk_size - 1) // chunk_size
            chunk_list = list(range(total_chunks))

            self.task_info.Download.files[self.current_queue_key]["total_chunks"] = total_chunks
            self.task_info.Download.files[self.current_queue_key]["chunks_list"] = chunk_list.copy()

            return chunk_list

    def calc_chunk_range(self, chunk_index: int, chunk_size: int, total_size: int):
        start = chunk_index * chunk_size
        end = min(start + chunk_size, total_size)

        return start, end
    
    def calc_downloaded_size(self):
        downloaded_size = 0

        for file_info in self.task_info.Download.files.values():
            finished_chunks = file_info["finished_chunks"]
            total_chunks = file_info["total_chunks"]

            if total_chunks > 0:
                if finished_chunks == total_chunks:
                    downloaded_size += file_info["file_size"]

                else:
                    downloaded_size += finished_chunks * self.chunk_size

        with self.update_lock:
            self.task_info.Download.downloaded_size = downloaded_size
    
    @Slot(int)
    def on_chunk_finished(self, chunk_index: int):
        with self.update_lock:
            # 检查该区块是否已经被标记为完成，避免重复更新进度
            if chunk_index in self.task_info.Download.files[self.current_queue_key]["chunks_list"]:
                self.task_info.Download.files[self.current_queue_key]["finished_chunks"] += 1

                current_progress = int(self.task_info.Download.files[self.current_queue_key]["finished_chunks"] / self.task_info.Download.files[self.current_queue_key]["total_chunks"] * 100)

                self.task_info.Download.files[self.current_queue_key]["chunks_list"].remove(chunk_index)

        task_manager.update(self.task_info)

        if current_progress >= 100:
            self.task_info.Download.queue.remove(self.current_queue_key)

            if self.task_info.Download.queue and not self._stop_event.is_set():
                self.start_worker()
                return

        if self.task_info.Download.progress >= 100:
            self.on_download_completed()

    def get_download_info(self):
        # 从队列选取一个 key
        self.current_queue_key = self.task_info.Download.queue.copy().pop(0)

        info = self.download_list.get(self.current_queue_key, {})

        path = Path(self.task_info.File.download_path, self.task_info.File.folder, info["file_name"])
        path.parent.mkdir(parents = True, exist_ok = True)

        if not Path(path).exists():
            File.preallocate_file(path, info.get("file_size", 0))

        info["file_path"] = path

        return info

    def update_info(self, download_info: dict):
        if not self.task_info.Download.files:
            self.task_info.Download.files = {
                file_key: {
                    "chunks_list": [],
                    "total_chunks": 0,
                    "finished_chunks": 0,
                    "file_size": download_info["download_list"][file_key]["file_size"]
                } for file_key in download_info["download_queue"]
            }

            has_video = self.task_info.Download.type & DownloadType.VIDEO != 0
            has_audio = self.task_info.Download.type & DownloadType.AUDIO != 0

            if has_video and has_audio:
                self.task_info.Download.info_label = Translator.VIDEO_QUALITY(reversed_video_quality_map.get(self.task_info.Download.video_quality_id, ""))

            elif has_video and not has_audio:
                self.task_info.Download.info_label = "MP4"

            elif not has_video and has_audio:
                self.task_info.Download.info_label = self.tr("Audio")

    def init_session(self):
        self.session = requests.Session()

        retry_strategy = Retry(
            total = 5,
            backoff_factor = 1,
            status_forcelist = [429, 500, 502, 503, 504]
        )

        adapter = HTTPAdapter(
            pool_connections = 5,
            pool_maxsize = 10,
            max_retries = retry_strategy
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        cookies = get_cookies()

        for key, value in cookies.items():
            self.session.cookies.set(
                name = key,
                value = value,
                domain = ".bilibili.com",
                path = "/"
            )

        headers = {
            "Referer": self.task_info.Episode.url,
            "User-Agent": config.get(config.user_agent)
        }

        self.session.headers.update(headers)

    def on_download_completed(self):
        self.task_info.Download.status = DownloadStatus.DOWNLOADING

        # 判断是否需要下载附加文件，如果需要就先下载附加文件，下载完成后再进入合并阶段
        danmaku = self.task_info.Download.type & DownloadType.DANMAKU != 0
        subtitles = self.task_info.Download.type & DownloadType.SUBTITLE != 0
        cover = self.task_info.Download.type & DownloadType.COVER != 0
        metadata = self.task_info.Download.type & DownloadType.METADATA != 0

        if any([danmaku, subtitles, cover, metadata]):
            worker = AdditionalParseWorker(self.task_info)
            worker.success.connect(self.wait_merge)
            worker.error.connect(self.on_parse_error)
            
            AsyncTask.run(worker)

        else:
            self.wait_merge()

    def wait_merge(self):
        # 等待合并
        self.task_info.Download.status = DownloadStatus.FFMPEG_QUEUED
        self.task_info.Download.speed = 0
        self.task_info.Download.progress = 100

        self._stop_event.set()

        self.session.close()

        self.speed_timer.stop()

        task_manager.update(self.task_info)

        # 通知 model 开始下一个下载任务
        signal_bus.download.start_next_task.emit()

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

        self.task_info.Download.speed = current_size - self.last_sampled_size
        self.task_info.Download.progress = int(self.task_info.Download.downloaded_size / self.task_info.Download.total_size * 100)
        self.last_sampled_size = current_size

        # emit 信号通知视图更新下载速度显示
        self.update_item(self.task_info)

        # 如果前面 on_chunk_finished 没有及时更新进度导致下载完成后没有进入合并阶段，这里再检查一次
        if self.task_info.Download.progress >= 100 and self.task_info.Download.status == DownloadStatus.DOWNLOADING:
            self.on_download_completed()

    def on_delete(self):
        # 销毁下载器实例前，清除引用
        self.session = None
        self.thread_pool = None

        self.task_info = None
        self.download_list = None

        self.deleteLater()
    
    def update_item(self, task_info: TaskInfo):
        signal_bus.download.update_downloading_item.emit(task_info)

        task_manager.update(self.task_info)