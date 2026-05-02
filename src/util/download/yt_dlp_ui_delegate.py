"""
yt-dlp UI 解耦层
实现正确的架构：UI → TaskManager → Downloader
"""

from PySide6.QtCore import QObject, Signal
from typing import Optional, Dict, Any
import logging

from .task_manager import (
    TaskManager, 
    DownloadTask, 
    TaskStatus, 
    TaskPriority,
    get_global_task_manager
)

logger = logging.getLogger(__name__)


class YTDLPUIDelegate(QObject):
    """
    yt-dlp UI 代理
    作为 UI 和 TaskManager 之间的桥梁
    所有 UI 操作通过此类进行，不直接访问 downloader
    """
    
    # UI 信号
    task_added_signal = Signal(object)
    task_progress_signal = Signal(object, dict)
    task_finished_signal = Signal(object)
    task_failed_signal = Signal(object, str)
    task_cancelled_signal = Signal(object)
    task_retried_signal = Signal(object)
    queue_status_changed_signal = Signal(dict)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.task_manager = get_global_task_manager()
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """设置 TaskManager 回调"""
        self.task_manager.set_callbacks(
            progress=self._on_progress,
            finish=self._on_finish,
            error=self._on_error,
            task_added=self._on_task_added
        )
    
    def add_task(self, url: str, output_dir: str = "downloads",
                 title: str = "", cookie_file: Optional[str] = None,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 config: Optional[Dict[str, Any]] = None) -> str:
        """
        添加下载任务
        
        Args:
            url: 视频URL
            output_dir: 输出目录
            title: 视频标题
            cookie_file: Cookie文件路径
            priority: 任务优先级
            config: 额外配置
            
        Returns:
            str: 任务ID
        """
        task = DownloadTask(
            url=url,
            output_dir=output_dir,
            title=title,
            cookie_file=cookie_file,
            priority=priority,
            config=config or {}
        )
        
        task_id = self.task_manager.add_task(task)
        return task_id
    
    def start_download(self) -> bool:
        """开始下载队列中的下一个任务"""
        return self.task_manager.start_next()
    
    def stop_download(self) -> bool:
        """停止当前下载"""
        return self.task_manager.stop_current()
    
    def retry_task(self, task_id: str) -> bool:
        """重试指定任务"""
        return self.task_manager.retry_task(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        return self.task_manager.cancel_task(task_id)
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务信息"""
        return self.task_manager.get_task(task_id)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return self.task_manager.get_queue_status()
    
    def clear_finished(self):
        """清除已完成任务"""
        self.task_manager.clear_finished()
    
    def clear_failed(self):
        """清除失败任务"""
        self.task_manager.clear_failed()
    
    def retry_all_failed(self) -> int:
        """重试所有失败任务"""
        return self.task_manager.retry_all_failed()
    
    def _on_task_added(self, task: DownloadTask):
        """任务添加回调"""
        self.task_added_signal.emit(task)
        self.queue_status_changed_signal.emit(self.get_queue_status())
    
    def _on_progress(self, task: DownloadTask, data: Dict[str, Any]):
        """进度回调"""
        status = data.get("status", "")
        
        if status == "downloading":
            percent_str = data.get("percent", "0%")
            try:
                task.progress = float(percent_str.replace("%", "").strip())
            except ValueError:
                pass
            
            task.speed = data.get("speed", "")
            task.eta = data.get("eta", "")
        
        self.task_progress_signal.emit(task, data)
    
    def _on_finish(self, task: DownloadTask):
        """完成回调"""
        self.task_finished_signal.emit(task)
        self.queue_status_changed_signal.emit(self.get_queue_status())
    
    def _on_error(self, task: DownloadTask, error_msg: str):
        """错误回调"""
        self.task_failed_signal.emit(task, error_msg)
        self.queue_status_changed_signal.emit(self.get_queue_status())


class YTDLPUIDelegateFactory:
    """
    UI 代理工厂
    用于创建和管理多个 UI 代理实例
    """
    
    _instances = {}
    
    @classmethod
    def get_instance(cls, name: str = "default", parent: Optional[QObject] = None) -> YTDLPUIDelegate:
        """
        获取或创建 UI 代理实例
        
        Args:
            name: 实例名称
            parent: 父对象
            
        Returns:
            YTDLPUIDelegate: UI 代理实例
        """
        if name not in cls._instances:
            cls._instances[name] = YTDLPUIDelegate(parent)
        return cls._instances[name]
    
    @classmethod
    def remove_instance(cls, name: str = "default"):
        """移除实例"""
        if name in cls._instances:
            del cls._instances[name]
    
    @classmethod
    def clear_all(cls):
        """清除所有实例"""
        cls._instances.clear()