"""
WebUI 入口

由 `main.py --web-ui` 分流进来，**位置在导入 QtWidgets 与 qfluentwidgets 之前**
（参照 `--mcp-stdio` 的先例）。这条路径下不会加载任何界面代码。

按 D16，这个进程**可以**用 QtCore / QtGui 的值类型与字体度量（弹幕转 ASS 要 `QFontMetrics`），
但**绝不能依赖 Qt 事件循环** —— 它跑的是 uvicorn 的 asyncio 循环，
`QThread` / `QTimer` / 跨线程队列信号在这里会静默失效。守卫见 `test/core_async_ready.py`。

目前只有骨架：抢锁、查依赖、给出明确提示。真正的 FastAPI 服务在 S3-1 落地。
"""

from typing import List
import logging
import sys

logger = logging.getLogger(__name__)

# 后端依赖不进桌面发行版（D8）。从源码跑时用 requirements-web.txt 安装
REQUIRED_PACKAGES = ("fastapi", "uvicorn")

WEB_REQUIREMENTS_FILE = "requirements-web.txt"

def _missing_packages() -> List[str]:
    """检查后端依赖，返回缺失的包名"""
    from importlib.util import find_spec

    missing = []

    for name in REQUIRED_PACKAGES:
        try:
            if find_spec(name) is None:
                missing.append(name)

        except (ImportError, ValueError):
            missing.append(name)

    return missing

def run_web_ui(argv: List[str]) -> int:
    """返回进程退出码"""
    from util.common.logging_setup import setup_logging

    # 与桌面版分开写：TimedRotatingFileHandler 多进程轮转会打架。
    # 单实例锁保证两边不会同时跑，但同一天里先后跑过两边时轮转仍可能撞上
    setup_logging("webui.log")

    logger.info("以 WebUI 模式启动")

    # ---- 与桌面版抢同一把锁 ----
    #
    # 两边共用 config.json、task.db 与下载目录，同时跑会互相覆盖配置、并发写同一个库
    from util.common._config.paths import get_data_dir
    from util.common.single_instance import InstanceLock, INSTANCE_LOCK_NAME, MODE_WEBUI

    lock = InstanceLock(get_data_dir() / "locks" / INSTANCE_LOCK_NAME, MODE_WEBUI)

    if not lock.acquire():
        message = lock.describe_holder()

        logger.error("无法启动 WebUI：%s", message)

        print(f"无法启动 WebUI：{message}。", file = sys.stderr)
        print("桌面版与 WebUI 共用配置与任务数据，同一时间只能运行一个。", file = sys.stderr)

        return 1

    try:
        return _serve(argv)

    finally:
        lock.release()

def _serve(argv: List[str]) -> int:
    missing = _missing_packages()

    if missing:
        # 给出可执行的下一步，而不是让 ImportError 的堆栈糊用户一脸（D8 / PLAN S3-2）
        logger.error("缺少后端依赖：%s", ", ".join(missing))

        print(f"缺少 WebUI 所需的依赖：{', '.join(missing)}。", file = sys.stderr)
        print(f"请先安装：pip install -r {WEB_REQUIREMENTS_FILE}", file = sys.stderr)
        print("（打包好的桌面安装包不含这些依赖，WebUI 需从源码运行或使用 Docker 镜像）",
              file = sys.stderr)

        return 1

    # TODO(S3-1)：起 FastAPI + uvicorn。届时 host / port 也在这里解析
    logger.error("WebUI 后端尚未实现（S3-1）")

    print("WebUI 后端尚未实现，敬请期待。", file = sys.stderr)

    return 1
