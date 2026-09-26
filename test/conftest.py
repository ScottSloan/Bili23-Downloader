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


# --------------------------------------------------------------------------
# DefaultValue 完整性检查
# --------------------------------------------------------------------------

# qfluentwidgets 的 ConfigItem 直接持有默认值对象，config.get() 返回的就是
# DefaultValue 上那个 list / dict 本身而非副本。任何一处「取到后就地修改」
# 都会永久污染进程内的默认值，且没有任何报错。
#
# 这个检查必须在**整场测试结束时**执行：放进普通用例只能覆盖到它自己之前
# 发生的修改，而污染往往来自后面某个用例走过的业务代码路径。

_defaults_snapshot = {}


def pytest_sessionstart(session):
    import copy

    from util.common.config import DefaultValue

    for name, value in vars(DefaultValue).items():
        if not name.startswith("_"):
            _defaults_snapshot[name] = copy.deepcopy(value)


def pytest_sessionfinish(session, exitstatus):
    from util.common.config import DefaultValue

    polluted = [
        name for name, pristine in _defaults_snapshot.items()
        if getattr(DefaultValue, name) != pristine
    ]

    if polluted:
        raise AssertionError(
            f"config.DefaultValue 中以下默认值在测试过程中被就地修改：{polluted}\n"
            "config.get() 返回的是默认值对象本身而非副本，改动它会污染整个进程。\n"
            "修改前请先 copy.deepcopy()（嵌套结构用 .copy() 浅拷贝挡不住）。"
        )
