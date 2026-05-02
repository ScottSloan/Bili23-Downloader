"""
yt-dlp GUI 集成示例
展示如何在现有 Bili23 GUI 中使用 yt-dlp 下载器
"""

from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QLabel, QPushButton, QLineEdit
from typing import Optional
import logging

from .yt_dlp_downloader import YTDLPDownloader

logger = logging.getLogger(__name__)


class YTDLPGUIHandler(QObject):
    """
    yt-dlp GUI 处理器
    与现有 Bili23 GUI 架构兼容
    """
    
    # 与现有 GUI 兼容的信号
    download_started = Signal(str)      # url
    download_progress = Signal(dict)    # progress_data
    download_finished = Signal(str)     # url
    download_error = Signal(str, str)   # url, error_msg

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.downloader = YTDLPDownloader()
        
        # 连接信号
        self.downloader.progress_signal.connect(self._handle_progress)
        self.downloader.finished_signal.connect(self._handle_finished)
        self.downloader.error_signal.connect(self._handle_error)

    def start_download(self, url: str, output_dir: str = "downloads", 
                      cookie_file: Optional[str] = None) -> bool:
        """
        开始下载并通知 GUI
        
        Args:
            url: 视频URL
            output_dir: 输出目录
            cookie_file: cookie文件路径
            
        Returns:
            bool: 是否成功启动
        """
        if self.downloader.is_downloading():
            logger.warning("Download already in progress")
            return False

        # 发射开始信号
        self.download_started.emit(url)
        
        # 启动下载
        return self.downloader.download(url, output_dir, cookie_file)

    def stop_download(self) -> bool:
        """停止下载"""
        return self.downloader.stop()

    def _handle_progress(self, progress_data: dict) -> None:
        """处理进度更新"""
        self.download_progress.emit(progress_data)

    def _handle_finished(self, url: str) -> None:
        """处理下载完成"""
        self.download_finished.emit(url)

    def _handle_error(self, error_msg: str) -> None:
        """处理下载错误"""
        # 需要从下载器获取当前 URL，这里简化处理
        self.download_error.emit("unknown", error_msg)


class SimpleDownloadWidget(QWidget):
    """
    简单的下载控件示例
    展示如何在现有 GUI 中使用 yt-dlp 下载器
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.download_handler = YTDLPGUIHandler(self)
        self.current_url = ""
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置 UI 控件"""
        layout = QVBoxLayout(self)
        
        # URL 输入
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入 Bilibili 视频 URL...")
        layout.addWidget(self.url_input)
        
        # 下载按钮
        self.download_btn = QPushButton("开始下载")
        layout.addWidget(self.download_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止下载")
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        layout.addWidget(self.status_label)
        
        # 速度标签
        self.speed_label = QLabel("")
        layout.addWidget(self.speed_label)

    def _connect_signals(self):
        """连接信号和槽"""
        self.download_btn.clicked.connect(self._start_download)
        self.stop_btn.clicked.connect(self._stop_download)
        
        # 连接下载处理器信号
        self.download_handler.download_started.connect(self._on_download_started)
        self.download_handler.download_progress.connect(self._on_download_progress)
        self.download_handler.download_finished.connect(self._on_download_finished)
        self.download_handler.download_error.connect(self._on_download_error)

    def _start_download(self):
        """开始下载"""
        url = self.url_input.text().strip()
        if not url:
            self.status_label.setText("请输入有效的 URL")
            return
        
        self.current_url = url
        
        # 启动下载
        success = self.download_handler.start_download(url)
        if success:
            self.status_label.setText("下载已启动...")
            self.download_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("下载启动失败")

    def _stop_download(self):
        """停止下载"""
        if self.download_handler.stop_download():
            self.status_label.setText("下载已停止")
            self.download_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _on_download_started(self, url: str):
        """下载开始回调"""
        self.status_label.setText(f"开始下载: {url}")
        self.progress_bar.setValue(0)

    def _on_download_progress(self, progress_data: dict):
        """下载进度回调"""
        status = progress_data.get("status", "")
        
        if status == "downloading":
            # 更新进度条
            percent_str = progress_data.get("percent", "0%")
            try:
                percent = float(percent_str.replace("%", "").strip())
                self.progress_bar.setValue(int(percent))
            except ValueError:
                pass
            
            # 更新状态信息
            speed = progress_data.get("speed", "")
            eta = progress_data.get("eta", "")
            self.speed_label.setText(f"{speed} - ETA: {eta}")
            
        elif status == "finished":
            self.status_label.setText("文件处理完成")

    def _on_download_finished(self, url: str):
        """下载完成回调"""
        self.status_label.setText("下载完成!")
        self.progress_bar.setValue(100)
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.speed_label.setText("")

    def _on_download_error(self, url: str, error_msg: str):
        """下载错误回调"""
        self.status_label.setText(f"下载错误: {error_msg}")
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)


# 与现有下载管理器集成的示例
class YTDLPIntegrationManager:
    """
    yt-dlp 与现有下载管理器集成示例
    """
    
    @staticmethod
    def create_yt_dlp_downloader() -> YTDLPDownloader:
        """创建 yt-dlp 下载器实例"""
        return YTDLPDownloader()
    
    @staticmethod
    def integrate_with_gui(parent_widget: QWidget) -> YTDLPGUIHandler:
        """
        将 yt-dlp 下载器集成到 GUI
        
        Args:
            parent_widget: 父控件
            
        Returns:
            YTDLPGUIHandler: GUI 处理器实例
        """
        handler = YTDLPGUIHandler(parent_widget)
        
        # 这里可以添加与现有 GUI 组件的连接
        # 例如连接到主窗口的下载列表、进度显示等
        
        return handler
    
    @staticmethod
    def replace_existing_downloader() -> bool:
        """
        替换现有下载器为 yt-dlp 下载器
        
        Returns:
            bool: 替换是否成功
        """
        try:
            # 这里可以实现替换现有下载器的逻辑
            # 需要根据实际的下载管理器结构进行调整
            
            logger.info("YT-DLP downloader integrated as replacement")
            return True
        except Exception as e:
            logger.error(f"Failed to replace existing downloader: {e}")
            return False


# 演示使用示例
def demo_usage():
    """演示如何使用 yt-dlp 下载器"""
    
    # 1. 基本使用
    downloader = YTDLPDownloader()
    
    def on_progress(data):
        print(f"进度: {data}")
    
    def on_finished(url):
        print(f"完成: {url}")
    
    def on_error(msg):
        print(f"错误: {msg}")
    
    downloader.progress_signal.connect(on_progress)
    downloader.finished_signal.connect(on_finished)
    downloader.error_signal.connect(on_error)
    
    # 开始下载
    # downloader.download("https://www.bilibili.com/video/BV1GJ411x7h7")
    
    # 2. GUI 集成使用
    app = QApplication([])
    
    widget = SimpleDownloadWidget()
    widget.show()
    
    app.exec()


if __name__ == "__main__":
    demo_usage()