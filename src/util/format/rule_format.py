"""
命名规则里格式串的预设。

界面上不让用户直接手写 `%Y-%m-%d` 或 `02d`，而是给一组预设；只有预设覆盖不到
时才落到自定义输入框。放在 util 层是为了让预设与它的示例效果能被单独测试 ——
一个渲染不出来的预设会让整条规则失败，而用户完全看不出问题在哪。
"""

from ..common.enum import VariableType

from .time import Time

# 与 VariableListFactory 的样本时间戳保持一致，预设的示例效果才对得上预览
SAMPLE_TIMESTAMP = 1772841600

# 日期时间的格式预设。键是 strftime 格式串，空串表示沿用变量自身的默认写法
DATETIME_PRESETS = (
    "%Y-%m-%d",
    "%Y-%m",
    "%Y",
    "%Y-%m-%d_%H-%M-%S",
    "%Y年%m月%d日",
)

# 数字的格式预设。补零是为了避免 1, 10, 2 这样的排序混乱
NUMBER_PRESETS = (
    "",
    "02d",
    "03d",
    "04d",
)

def presets_for(variable_type) -> tuple:
    match variable_type:
        case VariableType.DATETIME:
            return DATETIME_PRESETS

        case VariableType.NUMBER:
            return NUMBER_PRESETS

        case _:
            return ()

def preview_spec(variable_type, spec: str) -> str:
    """
    把一个格式串渲染成示例效果，供下拉项旁边标注

    渲染失败时返回空串 —— 调用方据此不显示示例，而不是把异常抛到界面上
    """
    try:
        match variable_type:
            case VariableType.DATETIME:
                value = Time.from_timestamp(SAMPLE_TIMESTAMP)

            case VariableType.NUMBER:
                value = 1

            case _:
                return ""

        return format(value, spec) if spec else str(value)

    except (ValueError, TypeError):
        return ""
