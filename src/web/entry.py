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

    import uvicorn

    from util.common.config import config

    from .app import create_app, ensure_password_configured

    host, port = _resolve_bind(argv)

    # 首次启动生成随机口令。**必须在服务起来之前**打印，否则用户看不到
    password = ensure_password_configured()

    if password:
        print("")
        print("=" * 60)
        print("  首次启动，已生成登录口令。这行只显示一次，请立即保存：")
        print("")
        print(f"    用户名：{config.get(config.webui_username)}")
        print(f"    密码：  {password}")
        print("")
        print("  忘记了可以删除 config.json 里的 webui_password_hash 重新生成。")
        print("=" * 60)
        print("")

    logger.info("WebUI 监听 http://%s:%d", host, port)

    if host == "0.0.0.0":
        logger.warning("正在监听所有网卡，请确认该端口不会被暴露到公网")

    uvicorn.run(
        create_app(),
        host = host,
        port = port,
        # 日志已由 setup_logging 统一配置，让 uvicorn 沿用而不是自己再装一套
        log_config = None,
        access_log = False,
    )

    return 0

def _resolve_bind(argv: List[str]):
    """
    解析监听地址。命令行 > 配置文件

    命令行参数是给 Docker 用的：镜像里必须绑 0.0.0.0（否则端口映射不通），
    而配置文件默认只听环回地址，从源码跑时不该无声无息地暴露到局域网
    """
    from util.common.config import config

    host = config.get(config.webui_host)
    port = config.get(config.webui_port)

    for index, arg in enumerate(argv):
        if arg == "--host" and index + 1 < len(argv):
            host = argv[index + 1]

        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]

        elif arg == "--port" and index + 1 < len(argv):
            port = argv[index + 1]

        elif arg.startswith("--port="):
            port = arg.split("=", 1)[1]

    try:
        port = int(port)

    except (TypeError, ValueError):
        logger.warning("端口 %r 无法解析，回落到配置值", port)

        port = config.get(config.webui_port)

    return host, port
