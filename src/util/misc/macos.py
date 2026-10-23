import sys
import logging

logger = logging.getLogger(__name__)

_accessibility_fix = None


def install_accessibility_ownership_fix():
    """Backport QTBUG-149612 after QApplication loads the Cocoa plugin.

    Keep the callback implementations in native code, including dealloc, so
    Qt teardown never calls back into a finalizing Python interpreter.
    """
    global _accessibility_fix
    if sys.platform != "darwin":
        return False
    if _accessibility_fix is not None:
        return True

    from PySide6.QtCore import qVersion
    # These are the bundled macOS runtime and the current source dependency.
    # Remove/extend this allowlist only after running the native regression.
    if qVersion() not in ("6.9.3", "6.10.3"):
        logger.warning("Qt %s 未启用已验证的 Cocoa 所有权修复，请重新验证 QTBUG-149612", qVersion())
        return False

    import ctypes
    from pathlib import Path
    path = Path(__file__).with_name("qt_cocoa_ownership.dylib")
    try:
        library = ctypes.CDLL(str(path))
        install = library.bili23_install_qt_cocoa_ownership_fix
        install.argtypes = []
        install.restype = ctypes.c_int
        result = install()
        if result not in (0, 1):
            logger.error("Cocoa 所有权修复未安装，原生布局检查返回 %d", result)
            return False
    except (OSError, AttributeError):
        logger.warning("未找到或无法加载 Cocoa 所有权修复。源码运行前请执行 "
                       "python scripts/build_macos_compat.py", exc_info = True)
        return False

    _accessibility_fix = library
    logger.info("已启用 Qt %s Cocoa 辅助功能所有权修复 (QTBUG-149612)", qVersion())
    return True


def activate_app():
    """
    在 macOS 上把本进程提到前台

    macOS 26 起，系统为了阻止应用互相抢焦点改用了合作式激活（cooperative activation）：
    只有当前前台应用（responsible process）让出激活权，目标进程才会真正变成 active。
    旧的 -[NSApplication activateIgnoringOtherApps:] 在 macOS 14 已标记废弃，
    到 macOS 26 上基本被系统忽略。

    Qt 的 cocoa 插件在启动时会把没有 bundle 的进程转成前台应用（TransformProcessType），
    紧接着调用的正是那个废弃接口。于是从终端直接运行 main.py 时，Dock 上有图标、窗口也画了
    出来，进程却始终不是 active：窗口拿不到键盘焦点，点击窗口也没有反应，必须先点一次 Dock
    图标才能恢复正常。macOS 14 及更早的系统走的是旧激活模型，不受影响。

    -[NSApplication activate]（macOS 14 引入）走新的合作式激活流程。从终端运行时 Terminal
    是前台应用，由它让出激活权，本进程才能顺利拿到焦点。
    """
    if sys.platform != "darwin":
        return

    try:
        # pyobjc 是 qframelesswindow 在 macOS 上的既有依赖（mac 分支直接 import Cocoa），
        # 这里不引入新的第三方依赖
        from AppKit import NSApplication, NSApplicationActivationPolicyRegular

        app = NSApplication.sharedApplication()

        # 没有 bundle 的进程默认按后台进程对待，这一步保证它出现在 Dock 与 Cmd-Tab 中。
        # Qt 通常已经做过，重复设置没有副作用
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

        if hasattr(app, "activate"):
            app.activate()
        else:
            # macOS 13 及更早没有新接口，回退到旧的激活方式
            app.activateIgnoringOtherApps_(True)

    except Exception:
        # 抢不到焦点只是体验问题，不能影响程序启动
        logger.exception("激活应用窗口失败")
