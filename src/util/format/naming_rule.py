"""
命名规则的变量表、校验与预览

原先这三件事写在 `gui/dialog/setting/edit_rule.py` 里 —— 那是个 Qt 对话框，
WebUI 用不了。规则的语义（哪些变量可用、什么样的规则算合法、套上示例数据长什么样）
**不该有第二份实现**：两边判断不一致的表现是「桌面版存得下的规则，WebUI 说非法」，
反过来更糟 —— WebUI 存下一条桌面版会崩的规则。

所以逻辑收在这里，两端共用；对话框只留交互外壳。这一层不依赖 Qt。

## 校验的三条

1. 不能为空
2. 不能以 `/` 或 `.` 开头 / 结尾（`..` 同理）—— 那样拼出来的路径会跳出下载目录，
   或产生隐藏文件
3. 路径的每一段都不能含 `<>:\\"|?*` 与控制字符 —— Windows 上这些字符非法，
   而下载目录常常是跨平台共享的

第 3 条要分两次查：一次查规则模板里的字面量（用户直接打进去的），
一次查套上示例数据之后的结果（变量的值里也可能带非法字符）。
只查后者的话，`{title}<` 这种在示例数据恰好规避了的写法会漏过去。
"""

from pathlib import Path
from typing import List, Optional, Tuple
import os
import re
import string

from ..common.data import VariableListFactory
from ..common.enum import ConventionType
from ..common.translator import Translator

from .file_name import FileNameFormatter

# Windows 上文件名里的非法字符，外加控制字符
ILLEGAL_PATTERN = re.compile(r'[<>:\\"|?*\x00-\x1f]')

def variables_for(convention_type) -> List[dict]:
    """
    某个规则类型可用的变量

    返回的 `description` 已经翻译过。原始表里存的是翻译键，认不出来的原样返回 ——
    与桌面版 `init_variable_list()` 的处理一致
    """
    factory = VariableListFactory()

    try:
        type_enum = convention_type if isinstance(convention_type, ConventionType) \
            else ConventionType(int(convention_type))

    except (TypeError, ValueError):
        return []

    entries = factory.build(type_enum) or []

    descriptions = Translator.VARIABLE_DESCRIPTION()

    result = []

    for entry in entries:
        description = entry.get("description")

        result.append({
            "variable": entry.get("variable"),
            "description": descriptions.get(description, description),
            "example": str(entry.get("example")),
        })

    return result

def validate_rule(rule: str) -> Tuple[bool, Optional[str]]:
    """规则本身合不合法。返回 (是否通过, 出错说明)"""
    if not rule:
        return False, Translator.ERROR_MESSAGES("NAMING_RULE_EMPTY")

    if rule.startswith(("/", ".", "..")) or rule.endswith(("/", ".")):
        return False, Translator.ERROR_MESSAGES("NAMING_RULE_BAD_EDGE")

    try:
        for literal_text, _, _, _ in string.Formatter().parse(rule):
            if literal_text and ILLEGAL_PATTERN.search(literal_text):
                return False, Translator.ERROR_MESSAGES("NAMING_RULE_ILLEGAL_CHARS")

    except (ValueError, KeyError):
        # 花括号没配对之类。string.Formatter 是下游真正会用的解析器，
        # 拿它来判「能不能解析」比自己写一套括号匹配可靠
        return False, Translator.ERROR_MESSAGES("NAMING_RULE_INVALID")

    return True, None

def preview_rule(convention_type, rule: str) -> Tuple[bool, Optional[str], Optional[Path]]:
    """
    套上示例数据看看结果。返回 (是否通过, 出错说明, 结果路径)

    结果路径的 `parent` 是相对下载目录的子目录，`stem` 是文件名（不含扩展名）——
    与桌面版预览对话框显示的两行一致
    """
    ok, message = validate_rule(rule)

    if not ok:
        return False, message, None

    variables = VariableListFactory()

    try:
        type_enum = convention_type if isinstance(convention_type, ConventionType) \
            else ConventionType(int(convention_type))

    except (TypeError, ValueError):
        return False, Translator.ERROR_MESSAGES("NAMING_RULE_INVALID"), None

    formatter = FileNameFormatter()
    formatter.set_variable_data(variables.build(type_enum) or [])
    formatter.set_rule(rule)

    try:
        result = formatter.format()

    except Exception:
        return False, Translator.ERROR_MESSAGES("NAMING_RULE_INVALID"), None

    if not result:
        return False, Translator.ERROR_MESSAGES("NAMING_RULE_INVALID"), None

    # 变量的值里也可能带非法字符，套完之后再查一遍每一段
    for part in str(result).split(os.sep):
        if ILLEGAL_PATTERN.search(part):
            return False, Translator.ERROR_MESSAGES("NAMING_RULE_ILLEGAL_CHARS"), None

    return True, None, Path(result)
