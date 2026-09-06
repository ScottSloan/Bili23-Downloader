"""
用户数据目录

**必须与旧实现算出完全一样的路径**，否则升级后用户的配置、任务、登录态全都「消失」。

旧实现（config.py 模块顶层）：

    appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    config_path = Path(appdata_path) / "Bili23 Downloader" / "config.json"

这里藏着一个隐式时序依赖：`AppDataLocation` 在**没有 QApplication 实例时**返回的是裸目录
（Windows 上是 `.../AppData/Roaming`），有实例时会自动拼上 `applicationName`。
config.py 恰好在 QApplication 构造之前被导入，所以拿到裸目录、再手动拼一次应用名，结果正确。
一旦有人调整导入顺序，路径会变成 `.../Roaming/Bili23 Downloader/Bili23 Downloader/`，
而且不会报错，只表现为「配置全丢了」。这个仓库的无头脚本已经踩过一次同类问题。

platformdirs 不依赖任何全局状态，正好根除这个脆弱性。三个平台的取值与旧实现一致：

| 平台 | 旧实现（QStandardPaths 裸值 + 应用名） | platformdirs |
|---|---|---|
| Windows | `%APPDATA%\\Bili23 Downloader` | 同（roaming = True） |
| macOS | `~/Library/Application Support/Bili23 Downloader` | 同 |
| Linux | `~/.local/share/Bili23 Downloader` | 同 |

Windows 上已实测一致；macOS 与 Linux 在对应平台首次运行时需要复核。
"""

from pathlib import Path

import platformdirs

APP_NAME = "Bili23 Downloader"

def get_data_dir() -> Path:
    """用户数据目录，config.json / task.db / thumbnail.db / history.db / logs / locks 都在这里"""
    # appauthor = False：Windows 上不要多插一层厂商名，旧实现没有那一层
    # roaming = True：对应 QStandardPaths 的 AppDataLocation（Roaming 而非 Local）
    return Path(platformdirs.user_data_dir(APP_NAME, appauthor = False, roaming = True))

def get_config_path() -> Path:
    return get_data_dir() / "config.json"
