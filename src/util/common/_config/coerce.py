"""
取值纠正与序列化

**语义是「纠正」而不是「拒绝」**，这一条是从 qfluentwidgets 沿用下来的，不是随手定的：
用户的 config.json 可能被手工改过、可能是旧版本写的、也可能被另一个进程写进了越界值。
在这些情况下让程序照常起来、把值拉回合法区间，比抛异常拒绝启动更符合一个下载器的定位。
pydantic 默认是拒绝并抛 ValidationError，所以这一层不能直接交给它。

与旧实现的一处**有意差异**：qfluentwidgets 的 OptionsValidator.correct() 在取值非法时返回
`options[0]`（第一个可选值），而不是该项的默认值。例如 when_close_window 的默认值是
ALWAYS_ASK，但 options[0] 是 EXIT —— 配置一旦损坏，关闭窗口的行为会变成直接退出。
这里一律回落到**该项声明的默认值**，这也是 schema 里写明的语义。
只有配置损坏或被手工改坏时才会走到这条分支，正常取值不受影响。
"""

from copy import deepcopy
from enum import Enum
from typing import Any
import logging

from .schema import ItemSpec, ValueType

logger = logging.getLogger(__name__)

def correct(spec: ItemSpec, value: Any, default: Any = None) -> Any:
    """
    把 value 纠正成该配置项可接受的取值

    default 用于覆盖 spec.default（下载目录那类运行时才能求得的默认值）
    """
    fallback = spec.default if default is None else default

    def bad(reason):
        logger.warning("配置项 %s.%s 的取值 %r %s，回落默认值", spec.group, spec.key, value, reason)

        return deepcopy(fallback)

    t = spec.type

    if t == ValueType.BOOL:
        return value if isinstance(value, bool) else bad("不是布尔值")

    if t in (ValueType.INT, ValueType.FLOAT):
        # bool 是 int 的子类，但布尔值出现在数值项上一定是配置坏了，不要静默当成 0 / 1
        if isinstance(value, bool):
            return bad("不是数值")

        if isinstance(value, str):
            # 旧实现里数值项大多没挂校验器，字符串会被原样收下。
            # 手工改过的配置、或早期版本写进去的字符串数字都属于这一类，能转就转
            try:
                value = float(value)

            except ValueError:
                return bad("不是数值")

        elif not isinstance(value, (int, float)):
            return bad("不是数值")

        value = int(value) if t == ValueType.INT else float(value)

        if spec.range:
            low, high = spec.range

            # 越界时 clamp 到边界而不是回落默认值：用户填 99999 端口，
            # 意图明显是「尽量大」，拉到 65535 比悄悄变回 23330 更贴近意图
            clamped = min(max(low, value), high)

            if clamped != value:
                logger.warning("配置项 %s.%s 的取值 %r 超出范围 %s，已收敛到 %r",
                               spec.group, spec.key, value, spec.range, clamped)

            return clamped

        return value

    if t == ValueType.STR:
        # 数值转成字符串而不是丢弃。cookie 里的 b_nut 就是这样：默认值是空字符串，
        # 但 cookie.py 写进去的是时间戳整数，旧实现没挂校验器所以一直原样收着。
        # 这类取值扔掉会直接影响风控参数，转换则不丢任何信息
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(value)

        if not isinstance(value, str):
            return bad("不是字符串")

        # 字符串型的可选值（排序字段名一类），不认识就回落
        if spec.options and value not in spec.options:
            return bad("不在可选值内")

        return value

    if t == ValueType.LIST:
        return deepcopy(value) if isinstance(value, list) else bad("不是列表")

    if t == ValueType.DICT:
        return deepcopy(value) if isinstance(value, dict) else bad("不是字典")

    if t == ValueType.ENUM:
        enum_class = spec.options

        if isinstance(value, enum_class):
            return value

        # 允许直接给字面量（从 config.json 反序列化时就是字面量）
        try:
            return enum_class(value)

        except ValueError:
            return bad("不是合法的枚举值")

    # COLOR 只出现在 QFluentWidgets 组，由桌面侧的桥接层自行处理，core 不解释
    return value

def serialize(spec: ItemSpec, value: Any) -> Any:
    """把内存中的取值转成可写进 config.json 的形态"""
    if spec.type == ValueType.ENUM and isinstance(value, Enum):
        return value.value

    return value

def deserialize(spec: ItemSpec, value: Any, default: Any = None) -> Any:
    """从 config.json 读出的字面量还原成内存取值，顺带纠正"""
    return correct(spec, value, default)
