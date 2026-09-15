"""
命名规则的结构模型 —— 可视化编辑器与 raw 规则串之间的双向桥。

可视化编辑器把一条规则看成两层结构：

    层级（目录，最后一层是文件名）
        └── 片段（一个变量，可带格式、前缀、后缀；或一段纯文字）

前缀与后缀会随变量一起消失，序列化出去就是 `<P{p:02d}->` 这样的可选段 ——
换句话说，`<>` 只是这个模型的存储形式，普通用户在界面上根本不必看见它。

**目录层不需要可选段**。FileNameFormatter.__normalize_path 本来就会丢掉空的
路径段，`<{parent_title}/>{leaf_title}` 与 `{parent_title}/{leaf_title}` 语义
完全等价。所以 to_rule() 永不生成跨 `/` 的可选段，parse_rule() 遇到这种写法
则把它规范化成普通目录层。

可视化能表达的是 raw 语法的**真子集**：嵌套可选段、一段里放多个变量这些写法
解析不回来。此时 parse_rule() 返回 UnsupportedRule 而不是抛异常、更不是悄悄
丢掉一部分 —— 界面据此禁用可视化区并提示用户改用高级模式。
"""

from .rule_template import compile_rule, RuleSyntaxError, TextNode, OptionalNode

from dataclasses import dataclass, field
import string

@dataclass
class Fragment:
    """
    层级里的一个片段

    variable 为 None 时是纯文字片段，内容在 text 里；否则是一个变量，
    prefix / suffix 是随它一起出现或消失的字面量。
    """
    variable: str = None
    spec: str = ""
    prefix: str = ""
    suffix: str = ""
    text: str = ""

    @property
    def is_text(self) -> bool:
        return self.variable is None

    @property
    def is_optional(self) -> bool:
        """带前后缀的变量才需要可选段语法把它们绑在一起"""
        return not self.is_text and bool(self.prefix or self.suffix)

@dataclass
class Level:
    """一个目录层级，或者（作为最后一层）文件名"""
    fragments: list = field(default_factory = list)

@dataclass
class RuleModel:
    levels: list = field(default_factory = list)

    def to_rule(self) -> str:
        return "/".join(
            "".join(_serialize_fragment(fragment) for fragment in level.fragments)
            for level in self.levels
        )

@dataclass
class UnsupportedRule:
    """规则含有可视化编辑器表达不了的结构，reason 用于告诉用户卡在哪里"""
    reason: str

def _escape(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")

def _serialize_fragment(fragment: Fragment) -> str:
    if fragment.is_text:
        return _escape(fragment.text)

    field_text = "{" + fragment.variable + (":" + fragment.spec if fragment.spec else "") + "}"

    if not fragment.is_optional:
        return field_text

    return "<" + _escape(fragment.prefix) + field_text + _escape(fragment.suffix) + ">"

def _iter_items(text: str):
    """
    把一段文本拆成字面量与字段

    string.Formatter().parse 已经处理了 {{ }} 的转义，返回的字面量是解转义后的
    """
    for literal_text, field_name, format_spec, conversion in string.Formatter().parse(text):
        if literal_text:
            yield ("text", literal_text)

        if field_name is None:
            continue

        if conversion is not None:
            raise _Unsupported("规则中使用了转换符（!r / !s），可视化编辑器无法表示")

        if format_spec and "{" in format_spec:
            raise _Unsupported("规则中使用了嵌套格式串，可视化编辑器无法表示")

        if not field_name or "." in field_name or "[" in field_name or field_name.isdigit():
            raise _Unsupported("规则中含有无法识别的变量写法")

        yield ("field", field_name, format_spec or "")

class _Unsupported(Exception):
    """内部使用：把解析过程中的「表达不了」一路抛到 parse_rule 转成返回值"""

    def __init__(self, reason: str):
        super().__init__(reason)

        self.reason = reason

def _flatten_optional(node: OptionalNode):
    """把一个可选段拍平成 (前缀, 变量名, 格式, 后缀)"""
    items = []

    for child in node.children:
        if isinstance(child, OptionalNode):
            raise _Unsupported("规则中含有嵌套的可选段，可视化编辑器无法表示")

        items.extend(_iter_items(child.text))

    fields = [item for item in items if item[0] == "field"]

    if len(fields) == 0:
        raise _Unsupported("规则中有不含变量的可选段")

    if len(fields) > 1:
        raise _Unsupported("规则中有一个可选段包含多个变量，可视化编辑器无法表示")

    index = items.index(fields[0])

    prefix = "".join(item[1] for item in items[:index])
    suffix = "".join(item[1] for item in items[index + 1:])

    return prefix, fields[0][1], fields[0][2], suffix

def _node_items(nodes):
    """把节点树拍平成统一的条目序列，可选段就地规范化"""
    items = []

    for node in nodes:
        if isinstance(node, TextNode):
            items.extend(_iter_items(node.text))
            continue

        prefix, name, spec, suffix = _flatten_optional(node)

        if not prefix and suffix == "/":
            # <{x}/> 等价于 {x}/ —— 空的目录层本来就会被路径规范化丢掉。
            # 统一成普通目录层，可视化编辑器才不必为它专门画一种形态
            items.append(("field", name, spec))
            items.append(("text", "/"))
            continue

        if "/" in prefix or "/" in suffix:
            raise _Unsupported("规则中有跨越目录层级的可选段，可视化编辑器无法表示")

        items.append(("optional", prefix, name, spec, suffix))

    return items

def _split_levels(items):
    levels = [[]]

    for item in items:
        if item[0] != "text":
            levels[-1].append(item)
            continue

        parts = item[1].split("/")

        for index, part in enumerate(parts):
            if index:
                levels.append([])

            if part:
                levels[-1].append(("text", part))

    return levels

def _build_level(items) -> Level:
    fragments = []

    for item in items:
        if item[0] == "text":
            # 相邻的文字合并成一个片段，否则往返一次就会多出几个空壳片段
            if fragments and fragments[-1].is_text:
                fragments[-1].text += item[1]
            else:
                fragments.append(Fragment(text = item[1]))

        elif item[0] == "field":
            fragments.append(Fragment(variable = item[1], spec = item[2]))

        else:
            fragments.append(Fragment(
                prefix = item[1], variable = item[2], spec = item[3], suffix = item[4]
            ))

    return Level(fragments = fragments)

def parse_rule(rule: str):
    """
    把 raw 规则串解析成结构模型

    成功返回 RuleModel，表达不了时返回 UnsupportedRule —— 绝不抛异常，
    也绝不静默丢掉解析不了的部分。
    """
    try:
        template = compile_rule(rule, True)

    except RuleSyntaxError as error:
        return UnsupportedRule(str(error))

    try:
        items = _node_items(template.nodes)

    except _Unsupported as error:
        return UnsupportedRule(error.reason)

    return RuleModel(levels = [_build_level(level) for level in _split_levels(items)])
