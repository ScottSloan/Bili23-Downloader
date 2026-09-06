"""
配置对象本体

对外形态与旧的 APPConfig 完全一致，调用方（一百多处）无需改动：

    config.get(config.download_path)        # 持久化项：按项取值
    config.set(config.download_path, path)  # 按项写值，默认立即落盘
    config.video_quality_id                 # 运行时状态：直接读写属性

与旧实现的三处关键差异：

1. **配置项是实例属性，不再是类属性。**
   旧实现把 ConfigItem 写在类体里，于是 `APPConfig()` 建出来的第二个实例与全局 config
   共享同一批 item 对象 —— 设置界面的「导出配置」正是这么用的，
   `temp_config.load()` 会把全局配置的取值一并改掉（导出一次，当前设置就被文件里的旧值覆盖）。
   改成实例属性后这个缺陷自然消失。

2. **写盘走 ConfigStore 的读改写**，磁盘上认不出来的键原样保留（D5）。

3. **不依赖 Qt。** 主题三项（themeMode / themeColor / fontFamilies）与几个 Qt 信号
   由桌面侧的桥接层注册进来，见 register_external()。WebUI 进程里它们不存在，
   而 WebUI 本来就不读写主题（D14）。
"""

from copy import deepcopy
from pathlib import Path
from typing import Any
import logging

from ..event import Event
from . import coerce
from .item import Item
from .paths import get_config_path
from .runtime import RuntimeState
from .schema import ITEMS, DynamicDefault
from .store import ConfigStore

logger = logging.getLogger(__name__)

def _resolve_dynamic_default(name: str):
    """求那些必须在运行时才能确定的默认值"""
    if name == "download_path":
        # 旧实现取自 QStandardPaths.DownloadLocation，即系统的「下载」目录
        import platformdirs

        return str(Path(platformdirs.user_downloads_dir()))

    raise KeyError(f"未知的动态默认值：{name}")

def _protect_config_version(merged: dict, on_disk: dict) -> None:
    """
    降级保护：磁盘上的结构版本更高时不要写小它

    否则新版本下次启动会误判需要重跑迁移。迁移虽然写的是幂等的，但不该依赖这一点兜底。
    未知字段本身由 ConfigStore 的读改写保住，这里补的是「字段认识、但语义会倒退」的那一格
    """
    disk_version = on_disk.get("Application", {}).get("config_version")
    new_version = merged.get("Application", {}).get("config_version")

    if isinstance(disk_version, int) and isinstance(new_version, int) and disk_version > new_version:
        merged["Application"]["config_version"] = disk_version

        logger.warning("磁盘上的配置结构版本（%d）高于本程序（%d），保留磁盘上的版本号",
                       disk_version, new_version)

class Config(RuntimeState):
    def __init__(self, file: Path = None):
        self._file = Path(file) if file is not None else get_config_path()

        self._store = ConfigStore(self._file)

        # 磁盘上读到的原始 JSON。迁移逻辑需要看已经不再声明的旧字段（proxy_enabled 等），
        # 那些字段没有对应的 Item，只能从这里取
        self.raw_data: dict = {}

        # 由桌面侧桥接层注册的属性：主题三项与几个 Qt 信号。见 register_external()
        self._external: dict[str, Any] = {}

        # 配置项按 attr 建索引，同时挂成实例属性，让 config.download_path 直接可用。
        #
        # 挂成实例属性会覆盖同名的类成员，因此先挡一道：schema 里新增一项叫 save / file / get
        # 之类的名字，会把方法悄悄换成配置项对象，而报错点会出现在离现场很远的地方
        reserved = {name for name in dir(type(self)) if not name.startswith("__")}

        self._items: dict[str, Item] = {}

        for spec in ITEMS:
            if spec.attr in reserved:
                raise RuntimeError(
                    f"配置项 {spec.attr!r} 与 Config 上已有的成员同名，会把它覆盖掉。"
                    f"请在 schema.py 里换一个 attr（key 可以保持不变，两者互不影响）"
                )

            default = None

            if isinstance(spec.default, DynamicDefault):
                default = _resolve_dynamic_default(spec.default.name)

            item = Item(spec, default = default)

            self._items[spec.attr] = item

            setattr(self, spec.attr, item)

        # 需要重启才能生效的项被改动时触发。桌面侧把它接到 appRestartSig 上，
        # core 不认识 Qt 信号，所以这里只发纯 Python 事件
        self.restart_required = Event("config.restart_required")

    # ---- 桌面侧注入 ----

    def register_external(self, name: str, obj) -> None:
        """
        注册一个由桌面侧提供的属性

        主题三项是 qfluentwidgets 的 ConfigItem（图标、样式表、委托字体都从全局 qconfig 读它们），
        themeChanged / themeColorChanged / appRestartSig 是 QConfig 上的 Qt 信号。
        它们必须仍以 config.xxx 的形式可见，否则界面侧十几处调用都要改。
        core 不解释这些对象，只做转发。
        """
        self._external[name] = obj

    def __getattr__(self, name: str):
        # __getattr__ 只在常规查找失败后才会被调用，因此不会影响任何已存在的属性
        external = self.__dict__.get("_external")

        if external and name in external:
            return external[name]

        raise AttributeError(
            f"{type(self).__name__} 没有属性 {name!r}"
            + ("（主题相关属性只在桌面版可用，见 gui/config_bridge.py）"
               if name in ("themeMode", "themeColor", "fontFamilies",
                           "themeChanged", "themeColorChanged", "appRestartSig") else "")
        )

    # ---- 配置文件路径 ----

    @property
    def file(self) -> Path:
        return self._file

    @file.setter
    def file(self, value) -> None:
        """
        改路径必须连带换掉 ConfigStore，否则后续写入还是落到旧文件上。
        设置界面的「导入配置」就是先改 file 再 save() 的，两者不同步会把导入的文件反写一遍
        """
        self._file = Path(value)

        self._store = ConfigStore(self._file)

    # ---- 取值 ----

    def get(self, item: Item):
        return item.value

    def set(self, item: Item, value, save: bool = True, copy: bool = True) -> None:
        """
        写入配置项。参数与 qfluentwidgets 的 QConfig.set 对齐，行为也保持一致：
        取值没变就直接返回（避免无谓写盘），需要重启的项额外发出提示
        """
        if item.value == value:
            return

        try:
            item.value = deepcopy(value) if copy else value

        except Exception:
            # 有些取值（含 Qt 对象的容器等）拷不动，与旧实现一样退化成直接赋值
            item.value = value

        if save:
            self.save()

        if item.restart:
            self.restart_required.emit()

    # ---- 读写文件 ----

    def load(self, file: Path = None) -> None:
        """
        从磁盘载入。file 省略时用当前的 self.file

        任何一项读失败都只影响该项（回落默认值并记日志），不会中断整个加载 ——
        配置读不出来不该拦住程序启动。
        """
        if file is not None:
            self.file = file

        self.raw_data = self._store.load()

        for item in self._items.values():
            section = self.raw_data.get(item.group)

            if not isinstance(section, dict) or item.name not in section:
                continue

            try:
                item.deserializeFrom(section[item.name])

            except Exception:
                logger.exception("配置项 %s 读取失败，使用默认值", item.key)

    def save(self) -> bool:
        known: dict[str, dict[str, Any]] = {}

        for item in self._items.values():
            known.setdefault(item.group, {})[item.name] = item.serialize()

        # 主题三项由桌面侧持有。桌面版运行时把它们一并写回，
        # 否则 qfluentwidgets 自己那套写盘路径与这里会互相覆盖
        for name in ("themeMode", "themeColor", "fontFamilies"):
            external = self._external.get(name)

            if external is None:
                continue

            try:
                known.setdefault(external.group, {})[external.name] = external.serialize()

            except Exception:
                logger.exception("主题配置项 %s 序列化失败，本次跳过（磁盘上的原值会被保留）", name)

        return self._store.save(known, adjust = _protect_config_version)

    def reset(self) -> None:
        """把所有配置项恢复默认值（不写盘）"""
        for item in self._items.values():
            item.reset()

    # ---- 供 WebUI / 导出使用 ----

    def to_dict(self) -> dict:
        """导出为可写进 JSON 的字典，含主题三项（桌面版才有）"""
        data: dict[str, dict[str, Any]] = {}

        for item in self._items.values():
            data.setdefault(item.group, {})[item.name] = item.serialize()

        for name in ("themeMode", "themeColor", "fontFamilies"):
            external = self._external.get(name)

            if external is None:
                continue

            try:
                data.setdefault(external.group, {})[external.name] = external.serialize()

            except Exception:
                logger.exception("主题配置项 %s 序列化失败，导出内容中将不含该项", name)

        return data

    def export_to(self, path) -> bool:
        """
        导出当前配置到指定文件

        这里刻意**不**走 ConfigStore 的读改写：导出的目标由用户在保存对话框里挑选并已确认覆盖，
        把目标文件里的旧内容合并进来只会得到一份谁也没要过的混合配置。

        旧实现是 `temp_config = APPConfig(); temp_config.load(config.file)`，
        而 ConfigItem 全是类属性、两个实例共享同一批对象，那句 load 会把**全局配置**的取值
        一并改成文件里的旧值 —— 导出一次，用户当前的设置就被悄悄改掉了。
        改成实例属性后本可以照旧写，但既然不需要第二个实例，就直接写出去
        """
        return ConfigStore(Path(path)).write(self.to_dict())

    def import_from(self, path) -> None:
        """从指定文件导入配置，随后写回自己原本的配置文件"""
        original = self.file

        try:
            self.load(path)

        finally:
            # 无论导入是否顺利都要把路径拨回来，否则后续任何一次 set() 都会写到导入源文件上
            self.file = original

        self.save()

    def item(self, attr: str) -> Item:
        return self._items[attr]

    @property
    def items(self) -> dict[str, Item]:
        return self._items
