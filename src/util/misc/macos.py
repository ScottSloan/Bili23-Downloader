import sys
import logging

logger = logging.getLogger(__name__)

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
