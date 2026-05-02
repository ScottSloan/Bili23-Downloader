"""
基于 yt-dlp 的下载模块
与现有 Bili23 项目架构兼容的 yt-dlp 下载器
"""

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from yt_dlp import YoutubeDL
import os
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)


class YTDLPDownloadWorker(QRunnable):
    """
    yt-dlp 下载工作线程，与 Qt 线程池兼容
    """
    
    def __init__(self, url: str, output_dir: str, cookie_file: Optional[str] = None,
                 progress_callback: Optional[Callable] = None,
                 finish_callback: Optional[Callable] = None,
                 error_callback: Optional[Callable] = None):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.cookie_file = cookie_file
        self.progress_callback = progress_callback
        self.finish_callback = finish_callback
        self.error_callback = error_callback
        self._stop_requested = False

    def _hook(self, d: Dict[str, Any]) -> None:
        """
        yt-dlp 进度回调
        """
        if self._stop_requested:
            raise Exception("Download stopped by user")
            
        if d.get("status") == "downloading":
            if self.progress_callback:
                self.progress_callback({
                    "status": "downloading",
                    "filename": d.get("filename", ""),
                    "percent": d.get("_percent_str", "").strip(),
                    "speed": d.get("_speed_str", "").strip(),
                    "eta": d.get("_eta_str", "").strip(),
                    "downloaded_bytes": d.get("downloaded_bytes", 0),
                    "total_bytes": d.get("total_bytes", 0),
                })
        elif d.get("status") == "finished":
            if self.progress_callback:
                self.progress_callback({
                    "status": "finished",
                    "filename": d.get("filename", ""),
                })

    def stop(self) -> None:
        """停止下载"""
        self._stop_requested = True

    def run(self) -> None:
        """执行下载任务"""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            ydl_opts = {
                # 视频+音频合并
                "format": "bv+ba/b",
                
                # 自动合并 mp4
                "merge_output_format": "mp4",
                
                # 输出路径
                "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
                
                # 进度回调
                "progress_hooks": [self._hook],
                
                # 基础优化
                "noplaylist": False,
                "retries": 3,
                "fragment_retries": 3,
                "concurrent_fragment_downloads": 4,
                
                # 减少日志干扰
                "quiet": True,
                "no_warnings": True,
                
                # 更好的错误处理
                "ignoreerrors": False,
                "skip_unavailable_fragments": True,
            }

            # cookie 支持
            if self.cookie_file and os.path.exists(self.cookie_file):
                ydl_opts["cookiefile"] = self.cookie_file

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            if self.finish_callback and not self._stop_requested:
                self.finish_callback(self.url)

        except Exception as e:
            if self.error_callback:
                self.error_callback(str(e))
            else:
                logger.error(f"Download error: {e}")


class YTDLPDownloader(QObject):
    """
    与 Bili23 项目兼容的 yt-dlp 下载器
    继承自 QObject 以支持 Qt 信号机制
    """
    
    # 信号定义 - 与现有项目兼容
    progress_signal = Signal(dict)  # 进度信号
    finished_signal = Signal(str)   # 完成信号
    error_signal = Signal(str)      # 错误信号

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(1)  # 单任务下载
        self.current_worker: Optional[YTDLPDownloadWorker] = None

    def download(self, url: str, output_dir: str = "downloads", 
                 cookie_file: Optional[str] = None) -> bool:
        """
        开始下载任务
        
        Args:
            url: 视频URL
            output_dir: 输出目录
            cookie_file: cookie文件路径
            
        Returns:
            bool: 是否成功启动下载
        """
        if self.current_worker:
            logger.warning("Download already in progress")
            return False

        def progress_callback(data: Dict[str, Any]) -> None:
            self.progress_signal.emit(data)

        def finish_callback(url: str) -> None:
            self.finished_signal.emit(url)
            self.current_worker = None

        def error_callback(error_msg: str) -> None:
            self.error_signal.emit(error_msg)
            self.current_worker = None

        self.current_worker = YTDLPDownloadWorker(
            url=url,
            output_dir=output_dir,
            cookie_file=cookie_file,
            progress_callback=progress_callback,
            finish_callback=finish_callback,
            error_callback=error_callback
        )

        self.thread_pool.start(self.current_worker)
        return True

    def stop(self) -> bool:
        """停止当前下载任务"""
        if self.current_worker:
            self.current_worker.stop()
            self.current_worker = None
            return True
        return False

    def is_downloading(self) -> bool:
        """检查是否正在下载"""
        return self.current_worker is not None

    # 扩展配置方法
    def set_max_threads(self, count: int) -> None:
        """设置最大线程数"""
        self.thread_pool.setMaxThreadCount(count)

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "format": "bv+ba/b",
            "merge_output_format": "mp4",
            "retries": 3,
            "concurrent_fragment_downloads": 4,
            "quiet": True,
            "no_warnings": True,
        }

    @staticmethod
    def create_custom_config(**kwargs) -> Dict[str, Any]:
        """创建自定义配置"""
        base_config = YTDLPDownloader.get_default_config()
        base_config.update(kwargs)
        return base_config


# 便捷的单例模式
_global_downloader: Optional[YTDLPDownloader] = None


def get_global_downloader() -> YTDLPDownloader:
    """获取全局下载器实例"""
    global _global_downloader
    if _global_downloader is None:
        _global_downloader = YTDLPDownloader()
    return _global_downloader


# CLI 测试版本
if __name__ == "__main__":
    def progress_callback(data):
        print(f"[PROGRESS] {data}")

    def finish_callback(url):
        print(f"[DONE] {url}")

    def error_callback(msg):
        print(f"[ERROR] {msg}")

    # 测试下载
    downloader = YTDLPDownloader()
    downloader.progress_signal.connect(progress_callback)
    downloader.finished_signal.connect(finish_callback)
    downloader.error_signal.connect(error_callback)

    # 替换为实际的 Bilibili 视频 URL
    test_url = "https://www.bilibili.com/video/BV1GJ411x7h7"
    downloader.download(test_url, output_dir="./test_downloads")
    
    # 等待下载完成
    import time
    while downloader.is_downloading():
        time.sleep(1)