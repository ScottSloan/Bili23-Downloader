"""
pytest 全局配置。

本文件的两件事都必须发生在任何 `util.*` / `gui.*` 导入之前，因此全部写在模块层：

1. 把 src 加入 sys.path —— 项目以 src 为包根运行（main.py 所在目录），
   而不是可安装的发行包，测试必须复现同样的导入路径。

2. 开启 Qt 的测试模式 —— util/common/config.py 在**导入期**就会
   `qconfig.load(config_path, config)` 并执行版本迁移 `patch_config()`，
   路径取自 QStandardPaths.AppDataLocation。不隔离的话，跑一次测试就可能
   改写用户真实的 config.json。测试模式把 AppDataLocation 重定向到
   `<AppData>/qttest`，真实配置从此不可达。

   注意：Windows 上 Qt 走 SHGetKnownFolderPath，改写 APPDATA 环境变量无效，
   setTestModeEnabled 是唯一可靠的手段。
"""

from PySide6.QtCore import QStandardPaths

from pathlib import Path
import shutil
import sys

_SRC = Path(__file__).resolve().parent.parent / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

QStandardPaths.setTestModeEnabled(True)

_TEST_APPDATA = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))

# 断言隔离确实生效。这行是整个测试套件的安全前提，宁可测试起不来，
# 也不能在未隔离的情况下跑下去
assert "qttest" in _TEST_APPDATA.as_posix(), (
    f"Qt 测试模式未生效，AppDataLocation 仍指向 {_TEST_APPDATA}，"
    "继续执行会污染用户的真实配置文件"
)

# 每轮测试从干净状态开始：上一轮遗留的配置会让「首次启动」「版本迁移」这类
# 用例的结果取决于执行顺序
shutil.rmtree(_TEST_APPDATA / "Bili23 Downloader", ignore_errors = True)
