from copy import deepcopy
from typing import Any

from ..event import Event
from . import coerce
from .schema import ItemSpec

class Item:
    __slots__ = ("spec", "valueChanged", "_value", "_default")

    def __init__(self, spec: ItemSpec, default: Any = None):
        """default 用于覆盖 spec.default，供 DynamicDefault 那类运行时才能求得的默认值使用"""
        self.spec = spec

        self.valueChanged = Event(f"config.{spec.group}.{spec.key}", weak = True)

        self._default = coerce.correct(spec, spec.default if default is None else default,
                                       default = spec.default if default is None else default)
        self._value = deepcopy(self._default)

    # ---- 与 ConfigItem 对齐的只读属性 ----

    @property
    def group(self) -> str:
        return self.spec.group

    @property
    def name(self) -> str:
        # ConfigItem 里的 name 指的是 config.json 中的二级键
        return self.spec.key

    @property
    def key(self) -> str:
        return f"{self.spec.group}.{self.spec.key}"

    @property
    def restart(self) -> bool:
        return self.spec.restart

    @property
    def options(self):
        """
        OptionsConfigItem 的接口。枚举项返回成员列表（与 OptionsValidator 一致），
        字面量项原样返回。非可选项返回 None —— 界面只会对声明了 options 的项取用
        """
        options = self.spec.options

        if options is None:
            return None

        if isinstance(options, type):
            return list(options)

        return list(options)

    @property
    def range(self):
        """RangeConfigItem 的接口"""
        return self.spec.range

    @property
    def defaultValue(self):
        return deepcopy(self._default)

    # ---- 取值 ----

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        v = coerce.correct(self.spec, v, default = self._default)

        old = self._value
        self._value = v

        # 与 ConfigItem 一致：只有真正变了才通知，避免界面无谓重绘
        if old != v:
            self.valueChanged.emit(v)

    # ---- 序列化 ----

    def serialize(self):
        return coerce.serialize(self.spec, self._value)

    def deserializeFrom(self, value):
        self.value = coerce.deserialize(self.spec, value, default = self._default)

    def reset(self):
        self.value = deepcopy(self._default)

    def __str__(self):
        return f"Item[{self.key}={self._value!r}]"

    __repr__ = __str__
