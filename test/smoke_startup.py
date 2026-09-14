"""
启动路径的冒烟测试。

src/main.py 的 Application.start_mcp_server() 注释里写着：

    # 默认关闭，未启用时连模块都不导入 —— http.server 与整条解析、下载链路
    # 都不应该出现在启动路径上（test/smoke_startup.py 对此有断言）。

本文件就是那份断言。在此之前该文件并不存在，注释描述的是一份不存在的保障。

为什么值得测：程序的首屏时间直接取决于启动路径上加载了多少模块。
仅仅是在某个启动期模块顶部多写一行 `from util.parse.parser.video import ...`，
就会把整条解析链路（连同 httpx、ssl、CA 证书加载）拖进启动路径，
而这在功能上毫无表现 —— 一切正常，只是启动慢了几百毫秒，且不会有人注意到
是哪次提交引入的。

必须在子进程中执行：pytest 自身的进程早已因为其他用例导入了 util.parse.*，
在同一进程里检查 sys.modules 没有任何意义。
"""

from pathlib import Path
import subprocess
import textwrap
import sys
import json

ROOT = Path(__file__).resolve().parent.parent

# 这些模块都不该出现在启动路径上。每一项后面是它被误引入时的实际代价
FORBIDDEN_AT_STARTUP = {
    "http.server": "MCP 的 HTTP 服务端，默认关闭时不应加载",
    "util.mcp": "MCP 包本身，默认关闭时不应加载",
    "util.mcp.server": "MCP 服务端实现",
    "httpx": "网络栈，main.py 明确将其预热放到后台线程（约 0.3 秒）",
    "ssl": "首次构建 SSL 上下文需加载完整 CA 列表（约 0.5 秒）",
    "sqlite3": "下载任务数据库，应延迟到真正需要时再加载",
    "util.download.downloader.downloader": "下载链路",
    "util.parse.worker": "解析链路",
    "util.parse.parser.video": "解析链路",
    "gui.interface.main_window": "主窗口应由 _main() 显式导入，而非模块导入期",
}


def _run_in_subprocess(code: str):
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd = ROOT,
        capture_output = True,
        text = True,
        encoding = "utf-8",
        errors = "replace",
        timeout = 180,
    )

    assert result.returncode == 0, (
        f"子进程退出码 {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )

    # qfluentwidgets 会在导入时打印推广横幅，取最后一行 JSON
    payload = result.stdout.strip().splitlines()[-1]

    return json.loads(payload)


def test_startup_does_not_import_heavy_modules():
    loaded = _run_in_subprocess(f"""
        import sys, json
        sys.path.insert(0, "test")
        import conftest      # sys.path 与 Qt 测试模式隔离

        import main          # 只导入，不执行 _main()（受 __name__ 守卫保护）

        forbidden = {list(FORBIDDEN_AT_STARTUP)!r}

        print(json.dumps([m for m in forbidden if m in sys.modules]))
    """)

    assert loaded == [], "以下模块被错误地拖入了启动路径：\n" + "\n".join(
        f"  - {name}：{FORBIDDEN_AT_STARTUP[name]}" for name in loaded
    )


def test_mcp_disabled_by_default():
    # 上一条断言成立的前提。MCP 会在本地环回地址上开放 HTTP 端点，
    # 必须由用户显式启用 —— 默认值一旦被改成 True，是个安全问题而不只是性能问题
    from util.common.config import config

    assert config.get(config.mcp_enabled) is False


def test_main_module_imports_without_qapplication():
    # main.py 在模块导入期就做了日志、faulthandler、Qt 消息处理器的安装。
    # 这些都不得依赖 QApplication 已经存在，否则 --mcp-stdio 桥接模式
    # （不创建 GUI）会在启动时直接崩掉
    _run_in_subprocess("""
        import sys, json
        sys.path.insert(0, "test")
        import conftest

        import main
        from PySide6.QtWidgets import QApplication

        assert QApplication.instance() is None, "导入 main 不应创建 QApplication"

        print(json.dumps("ok"))
    """)


def test_qt_resources_are_registered():
    """
    main.py 的 `import res.resources_rc` 是纯副作用导入 —— 没有任何符号被引用，
    ruff 会将其报为 F401。删掉它程序不会报错，只是图标、样式表、翻译文件
    全部静默消失。这里用实际存在的资源路径把它钉住。
    """
    from PySide6.QtCore import QDir

    import main     # noqa: F401  导入即注册资源

    entries = set(QDir(":/bili23").entryList())

    assert {"icon", "image", "qss", "i18n"} <= entries, (
        f":/bili23 下缺少资源目录，实际为 {sorted(entries)}；"
        "很可能是 res.resources_rc 的导入被当作未使用而删除"
    )


def test_importing_auth_server_creates_manager():
    """
    util/auth/server.py 在模块导入期就创建 server_manager，其 __init__ 连接了
    start_server 信号。captcha.py 里那句"未使用"的 `from .server import ServerManager`
    依赖的正是这个副作用。
    """
    import util.auth.server as server_module

    assert isinstance(getattr(server_module, "server_manager", None), server_module.ServerManager), (
        "util.auth.server 不再于导入期创建 server_manager，"
        "captcha.py 中依赖该副作用的延迟导入已失去意义"
    )


def test_captcha_still_imports_server_before_emitting():
    """
    源码级断言，守住一个删了也不会报错的东西。

    captcha.py 中 `from .server import ServerManager` 没有任何符号被使用，
    ruff 报 F401、IDE 也会提示"未使用"。但它必须先于 start_server.emit() 执行，
    否则信号发出时没有接收者 —— 验证码服务器不会启动，登录流程静默中断。

    运行时无法安全验证（真的 emit 会拉起一个 HTTP 服务器），因此改为断言
    这两行在同一个函数体内、且导入在 emit 之前。
    """
    source = (ROOT / "src" / "util" / "auth" / "captcha.py").read_text(encoding = "utf-8")

    import_index = source.find("from .server import ServerManager")
    emit_index = source.find("signal_bus.login.start_server.emit()")

    assert import_index != -1, (
        "captcha.py 不再导入 util.auth.server。若这是有意改动，"
        "请确认 start_server 信号在 emit 前已有接收者，并同步删除本用例"
    )
    assert emit_index != -1, "captcha.py 不再发出 start_server 信号，本用例需要同步更新"
    assert import_index < emit_index, "导入必须在 emit 之前，否则信号发出时还没有接收者"


# 首屏构造阶段（QApplication + MainWindow）之后仍不该出现的模块。
#
# 与 FORBIDDEN_AT_STARTUP 的区别：那一组只覆盖 `import main`，而界面模块是在
# MainWindow 构造时才被拉进来的 —— 本项目就曾因此漏掉一处：封面查询模块在顶层
# import httpx，经「收藏夹浮出控件 → 条目列表」的链路被界面间接引入，使得 main.py
# 特意放到后台线程的网络栈预热失去意义（零延时定时器按注册顺序触发，
# MainWindow.init_utils 先于 bootstrap_startup_tasks 执行）。
FORBIDDEN_AFTER_WINDOW = {
    "httpx": "网络栈，main.py 明确将其预热放在后台线程（导入约 64ms）",
    "http.server": "MCP 服务端，默认关闭时不应加载",
    "util.mcp.server": "MCP 服务端实现",
    "util.download.downloader.downloader": "下载链路，应延迟到真正开始下载时",
}


def test_window_construction_does_not_import_network_stack():
    loaded = _run_in_subprocess(f"""
        import sys, json
        sys.path.insert(0, "test")
        import conftest

        import main

        app = main.Application([])
        app.setup_app()

        from gui.interface.main_window import MainWindow

        MainWindow()

        forbidden = {list(FORBIDDEN_AFTER_WINDOW)!r}

        print(json.dumps([m for m in forbidden if m in sys.modules]))

        import os
        sys.stdout.flush()
        os._exit(0)     # 主题监听等线程会让事件循环无法正常收敛
    """)

    assert loaded == [], "主窗口构造阶段拖入了以下模块：\n" + "\n".join(
        f"  - {name}：{FORBIDDEN_AFTER_WINDOW[name]}" for name in loaded
    )
