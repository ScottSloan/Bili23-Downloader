"""
yt-dlp 适配器 - 与现有 Bili23 下载管理器兼容
"""

from PySide6.QtCore import QObject, Signal
from typing import Optional, Dict, Any
from pathlib import Path
import logging

# 导入现有项目中的相关模块
try:
    from util.common import config, Translator
    from util.common.enum import DownloadStatus, DownloadType
    from util.download.task.info import TaskInfo
    from util.download.task.manager import task_manager
except ImportError:
    # 备用导入，用于独立测试
    DownloadStatus = type('DownloadStatus', (), {
        'PARSING': 'parsing',
        'DOWNLOADING': 'downloading', 
        'FINISHED': 'finished',
        'FAILED': 'failed'
    })
    DownloadType = type('DownloadType', (), {
        'VIDEO': 1,
        'AUDIO': 2
    })

from .yt_dlp_downloader import YTDLPDownloader

logger = logging.getLogger(__name__)


class YTDLPTaskAdapter(QObject):
    """
    yt-dlp 任务适配器
    将 yt-dlp 下载器与现有 TaskInfo 系统集成
    """
    
    # 与现有下载器兼容的信号
    task_progress_signal = Signal(object, dict)  # task_info, progress_data
    task_finished_signal = Signal(object)        # task_info
    task_error_signal = Signal(object, str)      # task_info, error_msg

    def __init__(self):
        super().__init__()
        self.downloader = YTDLPDownloader()
        self.current_task: Optional[TaskInfo] = None
        
        # 连接信号
        self.downloader.progress_signal.connect(self._on_progress)
        self.downloader.finished_signal.connect(self._on_finished)
        self.downloader.error_signal.connect(self._on_error)

    def start_download(self, task_info: TaskInfo) -> bool:
        """
        开始下载任务
        
        Args:
            task_info: 任务信息对象
            
        Returns:
            bool: 是否成功启动
        """
        if self.current_task:
            logger.warning("Download already in progress")
            return False

        self.current_task = task_info
        
        # 更新任务状态
        task_info.Download.status = DownloadStatus.DOWNLOADING
        
        # 获取下载参数
        url = self._get_url_from_task(task_info)
        output_dir = self._get_output_dir(task_info)
        cookie_file = self._get_cookie_file()

        if not url:
            logger.error("No valid URL found in task")
            return False

        # 启动下载
        return self.downloader.download(url, output_dir, cookie_file)

    def stop_download(self) -> bool:
        """停止当前下载任务"""
        if self.current_task:
            self.current_task.Download.status = DownloadStatus.FAILED
            self.current_task = None
        
        return self.downloader.stop()

    def is_downloading(self) -> bool:
        """检查是否正在下载"""
        return self.downloader.is_downloading()

    def _on_progress(self, progress_data: Dict[str, Any]) -> None:
        """处理进度更新"""
        if not self.current_task:
            return

        # 更新任务进度信息
        if progress_data.get("status") == "downloading":
            # 解析进度百分比
            percent_str = progress_data.get("percent", "")
            if "%" in percent_str:
                try:
                    percent = float(percent_str.replace("%", "").strip())
                    self.current_task.Download.progress = percent
                except ValueError:
                    pass

            # 更新下载速度等信息
            self.current_task.Download.info_label = f"{progress_data.get('speed', '')} - {progress_data.get('eta', '')}"

        # 发射进度信号
        self.task_progress_signal.emit(self.current_task, progress_data)

    def _on_finished(self, url: str) -> None:
        """处理下载完成"""
        if not self.current_task:
            return

        # 更新任务状态
        self.current_task.Download.status = DownloadStatus.FINISHED
        self.current_task.Download.progress = 100
        self.current_task.Download.info_label = Translator.TIP_MESSAGES("DOWNLOAD_COMPLETED")

        # 发射完成信号
        self.task_finished_signal.emit(self.current_task)
        self.current_task = None

    def _on_error(self, error_msg: str) -> None:
        """处理下载错误"""
        if not self.current_task:
            return

        # 更新任务状态
        self.current_task.Download.status = DownloadStatus.FAILED
        self.current_task.Download.info_label = f"Error: {error_msg}"

        # 发射错误信号
        self.task_error_signal.emit(self.current_task, error_msg)
        self.current_task = None

    def _get_url_from_task(self, task_info: TaskInfo) -> Optional[str]:
        """从任务信息中提取 URL"""
        # 这里需要根据实际的 TaskInfo 结构来提取 URL
        # 假设 task_info 有 url 属性或可以从其他属性推导
        try:
            # 尝试从不同属性获取 URL
            if hasattr(task_info, 'url') and task_info.url:
                return task_info.url
            elif hasattr(task_info, 'Download') and hasattr(task_info.Download, 'url'):
                return task_info.Download.url
            elif hasattr(task_info, 'video_info') and hasattr(task_info.video_info, 'url'):
                return task_info.video_info.url
        except Exception as e:
            logger.error(f"Failed to get URL from task: {e}")
        
        return None

    def _get_output_dir(self, task_info: TaskInfo) -> str:
        """获取输出目录"""
        # 使用配置中的下载目录
        try:
            download_dir = config.get(config.download_dir)
            if download_dir:
                return download_dir
        except:
            pass
        
        # 默认目录
        return "downloads"

    def _get_cookie_file(self) -> Optional[str]:
        """获取 cookie 文件路径"""
        # 从配置中获取 cookie 文件路径
        try:
            cookie_file = config.get(config.cookie_file)
            if cookie_file and Path(cookie_file).exists():
                return cookie_file
        except:
            pass
        
        return None

    # 配置管理方法
    def update_config(self, **kwargs) -> None:
        """更新下载配置"""
        # 这里可以添加配置更新逻辑
        pass


# 全局适配器实例
_global_adapter: Optional[YTDLPTaskAdapter] = None


def get_global_adapter() -> YTDLPTaskAdapter:
    """获取全局适配器实例"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = YTDLPTaskAdapter()
    return _global_adapter


def integrate_with_existing_manager() -> bool:
    """
    将 yt-dlp 适配器集成到现有下载管理器
    
    Returns:
        bool: 集成是否成功
    """
    try:
        # 这里可以添加与现有下载管理器的集成逻辑
        # 例如替换默认下载器或添加为备用下载器
        
        logger.info("YT-DLP adapter integrated with existing download manager")
        return True
    except Exception as e:
        logger.error(f"Failed to integrate YT-DLP adapter: {e}")
        return False