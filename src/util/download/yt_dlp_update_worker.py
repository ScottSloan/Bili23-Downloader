from PySide6.QtCore import QObject, Signal, Slot

from util.thread import AsyncTask
from util.common import signal_bus, Translator
from util.common.enum import ToastNotificationCategory

import subprocess
import sys
import logging

logger = logging.getLogger(__name__)


class YtDlpUpdateWorker(QObject):
    """yt-dlp 更新工作线程"""
    
    success = Signal(str)   # 成功消息
    error = Signal(str)     # 错误消息
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot()
    def run(self):
        """执行 yt-dlp 更新"""
        try:
            logger.info("开始更新 yt-dlp...")
            
            # 获取当前版本
            current_version = self._get_current_version()
            
            # 执行更新命令
            result = self._upgrade_yt_dlp()
            
            if result:
                new_version = self._get_current_version()
                msg = Translator.TIP_MESSAGES("YTDLP_UPDATE_SUCCESS").format(
                    old_version=current_version,
                    new_version=new_version
                )
                self.success.emit(msg)
            else:
                self.error.emit(Translator.ERROR_MESSAGES("YTDLP_UPDATE_FAILED"))
                
        except Exception as e:
            logger.error(f"yt-dlp 更新失败: {e}")
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _get_current_version(self) -> str:
        """获取当前 yt-dlp 版本"""
        try:
            import yt_dlp
            return yt_dlp.version.__version__
        except Exception:
            return "unknown"

    def _upgrade_yt_dlp(self) -> bool:
        """执行 yt-dlp 升级命令"""
        try:
            # 使用 pip 升级 yt-dlp
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2分钟超时
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            if result.returncode == 0:
                logger.info("yt-dlp 更新成功")
                return True
            else:
                logger.error(f"yt-dlp 更新失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp 更新超时")
            return False
        except Exception as e:
            logger.error(f"yt-dlp 更新异常: {e}")
            return False
