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

    _bridge.themeMode.value = Theme.AUTO

    qconfig.load(Path(config.file), _bridge)

    qconfig.save = _bridge.save

    for name in ("themeMode", "themeColor", "fontFamilies"):
        config.register_external(name, getattr(_bridge, name))

    for name in ("themeChanged", "themeChangedFinished", "themeColorChanged", "appRestartSig"):
        config.register_external(name, getattr(_bridge, name))

    from util.thread.dispatch import DIRECT

    config.restart_required.connect(_bridge.appRestartSig.emit, dispatcher = DIRECT)

    logger.debug("配置桥接层已安装，主题：%s", qconfig.theme)

    return _bridge
