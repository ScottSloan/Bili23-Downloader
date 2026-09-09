import logging
import sys

from ._config.core import Config
from ._config.item import Item
from ._config.migrate import check_need_patch, patch_config
from ._config.paths import get_config_path, get_data_dir
from ._config.runtime import APP_CONFIG_VERSION
from ._config.schema import DefaultValue

logger = logging.getLogger(__name__)

def isWin11():
    return sys.platform == "win32" and sys.getwindowsversion().build >= 22000

config_path = get_config_path()

data_dir = get_data_dir()

config = Config(config_path)

if not config_path.exists():
    logger.warning("配置文件不存在，将创建新配置文件")

config.load()

# 判断是否需要修补配置文件
need_patch, config_version = check_need_patch(config.raw_data, APP_CONFIG_VERSION)

if need_patch:
    logger.info("检测到旧版本配置文件（结构版本 %d），正在进行修补", config_version)

    patch_config(config, config_version)

__all__ = ["config", "config_path", "data_dir", "isWin11", "DefaultValue", "Config", "Item"]
