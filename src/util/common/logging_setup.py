"""
日志配置

桌面版与 WebUI 两个入口共用同一套格式，写到同一个 `logs/` 目录下的不同文件。
分开文件是因为 `TimedRotatingFileHandler` 在多进程下轮转会打架 —— 虽然单实例锁
保证两边不会同时跑，但同一天里先后跑过两边时，轮转仍可能撞上。

**不依赖 Qt。** WebUI 的分流发生在导入任何 Qt 之前（PLAN 的 S2-8），那时候得先有日志。
"""

from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import logging
import sys

from ._config.paths import get_data_dir

class CompactLogFormatter(logging.Formatter):
    def format(self, record):
        record.callsite = f"{record.filename}:{record.lineno} in {record.funcName}"

        return super().format(record)

    def formatTime(self, record, datefmt = None):
        dt = datetime.fromtimestamp(record.created)

        if datefmt:
            return dt.strftime(datefmt)

        return dt.isoformat(sep = " ", timespec = "microseconds")

def create_formatter() -> CompactLogFormatter:
    return CompactLogFormatter(
        "[%(asctime)s] - %(name)s - %(levelname)s - at %(callsite)s: %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S.%f",
    )

def setup_logging(filename: str = "app.log", level: int = logging.INFO) -> Path:
    """配置根 logger，返回日志文件路径"""
    log_path = get_data_dir() / "logs" / filename

    log_path.parent.mkdir(parents = True, exist_ok = True)

    formatter = create_formatter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    file_handler = TimedRotatingFileHandler(
        log_path, when = "midnight", interval = 1, backupCount = 15, encoding = "utf-8")
    file_handler.setFormatter(formatter)

    logging.basicConfig(level = level, handlers = [stream_handler, file_handler])

    return log_path
