"""
yt-dlp 任务管理器模块
包含任务状态机、任务管理器和受控下载器
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import uuid
import os
import threading

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    WAITING = "waiting"
    DOWNLOADING = "downloading"
    FINISHED = "finished"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class DownloadTask:
    """下载任务数据类"""
    url: str
    output_dir: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    cookie_file: Optional[str] = None
    status: TaskStatus = TaskStatus.WAITING
    priority: TaskPriority = TaskPriority.NORMAL
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    file_size: int = 0
    downloaded_size: int = 0
    filename: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """增加重试计数"""
        self.retry_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "url": self.url,
            "title": self.title,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "filename": self.filename,
        }


class ControlledDownloader:
    """
    受控下载器
    支持 start/stop/retry 操作
    """
    
    def __init__(self, task: DownloadTask):
        self.task = task
        self._stop_event = threading.Event()
        self._ydl = None
        self._is_running = False
    
    def start(self, progress_callback: Optional[Callable] = None,
              finish_callback: Optional[Callable] = None,
              error_callback: Optional[Callable] = None) -> bool:
        """
        开始下载
        
        Args:
            progress_callback: 进度回调
            finish_callback: 完成回调
            error_callback: 错误回调
            
        Returns:
            bool: 是否成功启动
        """
        if self._is_running:
            logger.warning(f"Task {self.task.task_id} already running")
            return False
        
        self._stop_event.clear()
        self._is_running = True
        self.task.status = TaskStatus.DOWNLOADING
        self.task.started_at = datetime.now()
        
        try:
            from yt_dlp import YoutubeDL
            
            ydl_opts = {
                "format": self.task.config.get("format", "bv+ba/b"),
                "merge_output_format": self.task.config.get("merge_output_format", "mp4"),
                "outtmpl": os.path.join(self.task.output_dir, "%(title)s.%(ext)s"),
                "progress_hooks": [lambda d: self._hook(d, progress_callback)],
                "quiet": True,
                "no_warnings": True,
                "retries": 3,
                "fragment_retries": 3,
                "no_write_cookies": True,
            }
            
            if self.task.cookie_file and os.path.exists(self.task.cookie_file):
                ydl_opts["cookiefile"] = self.task.cookie_file
            
            self._ydl = YoutubeDL(ydl_opts)
            
            with self._ydl:
                self._ydl.download([self.task.url])
            
            self.task.status = TaskStatus.FINISHED
            self.task.progress = 100.0
            self.task.finished_at = datetime.now()
            
            if finish_callback:
                finish_callback(self.task)
            
            return True
            
        except Exception as e:
            if self._stop_event.is_set():
                self.task.status = TaskStatus.CANCELLED
                logger.info(f"Task {self.task.task_id} cancelled")
            else:
                self.task.status = TaskStatus.FAILED
                self.task.error_message = str(e)
                logger.error(f"Task {self.task.task_id} failed: {e}")
                
                if error_callback:
                    error_callback(self.task, str(e))
            
            self._is_running = False
            return False
    
    def stop(self) -> bool:
        """停止下载"""
        if not self._is_running:
            return False
        
        self._stop_event.set()
        self._is_running = False
        self.task.status = TaskStatus.CANCELLED
        logger.info(f"Task {self.task.task_id} stopped")
        return True
    
    def retry(self, progress_callback: Optional[Callable] = None,
              finish_callback: Optional[Callable] = None,
              error_callback: Optional[Callable] = None) -> bool:
        """
        重试下载
        
        Args:
            progress_callback: 进度回调
            finish_callback: 完成回调
            error_callback: 错误回调
            
        Returns:
            bool: 是否成功启动重试
        """
        if not self.task.can_retry():
            logger.warning(f"Task {self.task.task_id} max retries reached")
            return False
        
        self.task.increment_retry()
        self.task.status = TaskStatus.RETRYING
        self.task.error_message = ""
        self.task.progress = 0.0
        
        logger.info(f"Task {self.task.task_id} retrying ({self.task.retry_count}/{self.task.max_retries})")
        
        return self.start(progress_callback, finish_callback, error_callback)
    
    def _hook(self, d: Dict[str, Any], callback: Optional[Callable]) -> None:
        """进度回调钩子"""
        if self._stop_event.is_set():
            raise Exception("Download stopped by user")
        
        if callback:
            if d.get("status") == "downloading":
                callback({
                    "status": "downloading",
                    "task_id": self.task.task_id,
                    "filename": d.get("filename", ""),
                    "percent": d.get("_percent_str", "").strip(),
                    "speed": d.get("_speed_str", "").strip(),
                    "eta": d.get("_eta_str", "").strip(),
                })
            elif d.get("status") == "finished":
                callback({
                    "status": "finished",
                    "task_id": self.task.task_id,
                    "filename": d.get("filename", ""),
                })
    
    @property
    def is_running(self) -> bool:
        return self._is_running


class TaskManager:
    """
    任务管理器
    管理下载任务队列，控制任务执行顺序
    """
    
    def __init__(self, max_concurrent: int = 1):
        self.queue: List[DownloadTask] = []
        self.current: Optional[DownloadTask] = None
        self.current_downloader: Optional[ControlledDownloader] = None
        self.finished_tasks: List[DownloadTask] = []
        self.failed_tasks: List[DownloadTask] = []
        self.max_concurrent = max_concurrent
        self._lock = threading.Lock()
        
        self._progress_callback: Optional[Callable] = None
        self._finish_callback: Optional[Callable] = None
        self._error_callback: Optional[Callable] = None
        self._task_added_callback: Optional[Callable] = None
    
    def set_callbacks(self, progress: Optional[Callable] = None,
                      finish: Optional[Callable] = None,
                      error: Optional[Callable] = None,
                      task_added: Optional[Callable] = None):
        """设置回调函数"""
        self._progress_callback = progress
        self._finish_callback = finish
        self._error_callback = error
        self._task_added_callback = task_added
    
    def add_task(self, task: DownloadTask) -> str:
        """
        添加任务到队列
        
        Args:
            task: 下载任务
            
        Returns:
            str: 任务ID
        """
        with self._lock:
            self.queue.append(task)
            
            if self._task_added_callback:
                self._task_added_callback(task)
            
            logger.info(f"Task {task.task_id} added to queue")
            return task.task_id
    
    def start_next(self) -> bool:
        """
        开始下一个任务
        
        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if not self.queue:
                logger.info("No tasks in queue")
                return False
            
            if self.current and self.current.status == TaskStatus.DOWNLOADING:
                logger.warning("A task is already running")
                return False
            
            self.current = self.queue.pop(0)
        
        return self._execute_task(self.current)
    
    def _execute_task(self, task: DownloadTask) -> bool:
        """执行任务"""
        downloader = ControlledDownloader(task)
        self.current_downloader = downloader
        
        def on_progress(data):
            if self._progress_callback:
                self._progress_callback(task, data)
        
        def on_finish(finished_task):
            with self._lock:
                self.finished_tasks.append(finished_task)
                self.current = None
                self.current_downloader = None
            
            if self._finish_callback:
                self._finish_callback(finished_task)
            
            self.start_next()
        
        def on_error(failed_task, error_msg):
            with self._lock:
                self.failed_tasks.append(failed_task)
                self.current = None
                self.current_downloader = None
            
            if self._error_callback:
                self._error_callback(failed_task, error_msg)
        
        import threading
        thread = threading.Thread(
            target=downloader.start,
            args=(on_progress, on_finish, on_error),
            daemon=True
        )
        thread.start()
        
        return True
    
    def stop_current(self) -> bool:
        """停止当前任务"""
        if self.current_downloader:
            return self.current_downloader.stop()
        return False
    
    def retry_task(self, task_id: str) -> bool:
        """
        重试指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功启动重试
        """
        task = self._find_task(task_id)
        if not task:
            return False
        
        if task == self.current and self.current_downloader:
            return self.current_downloader.retry(
                progress_callback=lambda d: self._progress_callback(task, d) if self._progress_callback else None,
                finish_callback=lambda t: self._finish_callback(t) if self._finish_callback else None,
                error_callback=lambda t, e: self._error_callback(t, e) if self._error_callback else None
            )
        
        return False
    
    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        with self._lock:
            for i, task in enumerate(self.queue):
                if task.task_id == task_id:
                    self.queue.pop(i)
                    task.status = TaskStatus.CANCELLED
                    logger.info(f"Task {task_id} cancelled")
                    return True
        
        if self.current and self.current.task_id == task_id:
            return self.stop_current()
        
        return False
    
    def remove_task(self, task_id: str) -> bool:
        """移除指定任务"""
        return self.cancel_task(task_id)
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务"""
        return self._find_task(task_id)
    
    def _find_task(self, task_id: str) -> Optional[DownloadTask]:
        """查找任务"""
        if self.current and self.current.task_id == task_id:
            return self.current
        
        for task in self.queue:
            if task.task_id == task_id:
                return task
        
        for task in self.finished_tasks:
            if task.task_id == task_id:
                return task
        
        for task in self.failed_tasks:
            if task.task_id == task_id:
                return task
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "queue_length": len(self.queue),
            "current_task": self.current.to_dict() if self.current else None,
            "finished_count": len(self.finished_tasks),
            "failed_count": len(self.failed_tasks),
        }
    
    def clear_finished(self):
        """清除已完成的任务"""
        with self._lock:
            self.finished_tasks.clear()
    
    def clear_failed(self):
        """清除已失败的任务"""
        with self._lock:
            self.failed_tasks.clear()
    
    def retry_all_failed(self) -> int:
        """重试所有失败的任务"""
        count = 0
        with self._lock:
            for task in self.failed_tasks:
                if task.can_retry():
                    task.status = TaskStatus.WAITING
                    self.queue.append(task)
                    count += 1
            self.failed_tasks.clear()
        
        if count > 0 and not self.current:
            self.start_next()
        
        return count


_global_task_manager: Optional[TaskManager] = None


def get_global_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    global _global_task_manager
    if _global_task_manager is None:
        _global_task_manager = TaskManager()
    return _global_task_manager