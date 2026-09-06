"""
全局配置单例

这个模块只做「组装」：真正的实现拆在 `_config/` 包里（包名带下划线是因为同名的模块与包
在 Python 里无法共存，而全仓库一百多处 `from util.common.config import config` 不能动）。

    _config/schema.py    配置项声明清单
    _config/item.py      配置项对象，形态与 qfluentwidgets 的 ConfigItem 对齐
    _config/coerce.py    取值纠正与序列化（纠正而非拒绝）
    _config/store.py     config.json 的读写，含未知字段透传
    _config/core.py      配置对象本体
    _config/migrate.py   结构版本迁移
    _config/runtime.py   不落盘的运行时状态
    _config/paths.py     用户数据目录

**本模块及其依赖不引入 Qt。** 桌面版所需的主题桥接在 `gui/config_bridge.py`，
由 main.py 显式安装；WebUI 进程不装它。
"""

from pathlib import Path
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

# 兼容旧写法：调用方普遍写成 `Path(appdata_path) / "Bili23 Downloader" / "task.db"`，
# 因此这里给的是**数据目录的上一层**。新代码请直接用 get_data_dir()
appdata_path = str(get_data_dir().parent)

config = Config(config_path)

if not config_path.exists():
    logger.warning("配置文件不存在，将创建新配置文件")

config.load()

# 判断是否需要修补配置文件
need_patch, config_version = check_need_patch(config.raw_data, APP_CONFIG_VERSION)

if need_patch:
    logger.info("检测到旧版本配置文件（结构版本 %d），正在进行修补", config_version)

    patch_config(config, config_version)

__all__ = ["config", "config_path", "appdata_path", "isWin11", "DefaultValue", "Config", "Item"]
