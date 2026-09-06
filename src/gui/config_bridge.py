"""
桌面侧的配置桥接层

S2-2 把配置系统从 qfluentwidgets 的 QConfig 上摘了下来（WebUI 进程里没有 Qt），
但**桌面版仍然需要那座桥**：qfluentwidgets 的全局单例 qconfig 是它内部读取主题、
强调色、字体的唯一入口，本项目也有三处直接依赖它 ——

    util/common/icon.py:43        qconfig.theme      决定图标取 light 还是 dark 资源
    util/common/style_sheet.py:12 qconfig.theme      决定样式表取哪一套
    gui/component/view_model/delegate_base.py:25     qconfig.fontFamilies

旧实现靠 `qconfig.load(config_path, config)` 把 qconfig 与本项目的 config 变成同一个对象
（QConfig.load 内部会 `self._cfg = config`）。这座桥一旦断掉，图标、样式表、委托字体会
全部退回 qfluentwidgets 的默认值 —— **不报错，只是「看起来不太对」**。

这里的做法是让 QConfig 只保留它自己那三项（themeMode / themeColor / fontFamilies，
它们落在 config.json 的 "QFluentWidgets" 段），业务配置全部归 core 管，两边通过
register_external() 相互可见，于是 `config.themeMode`、`config.themeChanged`、
`config.appRestartSig` 这些界面侧的写法一个字都不用改。

主题不与 WebUI 联动（D14）：这一段由桌面版独占，WebUI 只负责原样透传，不解释其取值。
"""

from pathlib import Path
import logging

from qfluentwidgets import QConfig, Theme, qconfig

from util.common.config import config

logger = logging.getLogger(__name__)

class ConfigBridge(QConfig):
    """
    只持有 QConfig 自带的主题三项，不再声明任何业务配置项

    save() 转交给 core，让主题与业务配置在同一次写盘里落地，
    也就顺带继承了 core 那边的原子替换、写盘串行化与未知字段透传
    """

    def save(self):
        config.save()

_bridge: ConfigBridge = None

def install() -> ConfigBridge:
    """
    安装桥接层。**必须在任何界面代码读取主题之前调用**，由 main.py 在导入 config 之后立即执行

    WebUI 进程不调用它，那边 config.themeMode 一类属性直接不存在（core 会给出明确的
    AttributeError 而不是静默返回默认值）
    """
    global _bridge

    if _bridge is not None:
        return _bridge

    _bridge = ConfigBridge()

    # 首次启动跟随系统主题。QConfig 里 themeMode 声明的默认值是 Light，
    # 直接改 item 的取值而不是走 set()，避免在加载配置前就触发一次写盘
    _bridge.themeMode.value = Theme.AUTO

    # 读取 config.json 里的 "QFluentWidgets" 段，并把 qconfig._cfg 指向本桥。
    # 这一步之后 qconfig.theme / qconfig.get(qconfig.fontFamilies) 才是用户的配置
    qconfig.load(Path(config.file), _bridge)

    # qconfig.set() 内部调的是 qconfig 自己的 save()，它会用 json.dump 直接覆写整个文件 ——
    # 而 qconfig 只认识主题三项，业务配置会在那一瞬间全部消失。
    # 设置界面的 38 个绑定点走的正是 qconfig.set()，所以这里必须把写盘接管过来。
    # （旧实现没有这个问题，因为那时 _cfg 就是持有全部配置项的 APPConfig）
    qconfig.save = _bridge.save

    for name in ("themeMode", "themeColor", "fontFamilies"):
        config.register_external(name, getattr(_bridge, name))

    for name in ("themeChanged", "themeChangedFinished", "themeColorChanged", "appRestartSig"):
        config.register_external(name, getattr(_bridge, name))

    # core 不认识 Qt 信号，需要重启的配置项被改动时它只发纯 Python 事件，这里转成 Qt 信号。
    # 用 DIRECT 就地执行：发射方本来就在 GUI 线程（改设置只可能来自界面操作），
    # 多绕一次事件循环会让「需要重启」的提示延迟到下一帧才出现
    from util.thread.dispatch import DIRECT

    config.restart_required.connect(_bridge.appRestartSig.emit, dispatcher = DIRECT)

    logger.debug("配置桥接层已安装，主题：%s", qconfig.theme)

    return _bridge
