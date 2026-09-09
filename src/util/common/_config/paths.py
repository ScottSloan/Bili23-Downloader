from pathlib import Path
import logging
import os

import platformdirs

logger = logging.getLogger(__name__)

APP_NAME = "Bili23 Downloader"

DATA_DIR_ENV = "BILI23_DATA_DIR"

def get_data_dir() -> Path:
    """用户数据目录，config.json / task.db / thumbnail.db / history.db / logs / locks 都在这里"""
    override = os.environ.get(DATA_DIR_ENV)

    if override:
        # 只做展开，不校验可写性 —— 目录可能还不存在，由各个使用方按需创建。
        # 真写不进去时让它在写入点上报错，比在这里提前判断更准确
        return Path(os.path.expanduser(os.path.expandvars(override)))

    # appauthor = False：Windows 上不要多插一层厂商名，旧实现没有那一层
    # roaming = True：对应 QStandardPaths 的 AppDataLocation（Roaming 而非 Local）
    return Path(platformdirs.user_data_dir(APP_NAME, appauthor = False, roaming = True))

def get_config_path() -> Path:
    return get_data_dir() / "config.json"
