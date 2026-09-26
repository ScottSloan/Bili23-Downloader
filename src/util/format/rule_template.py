"""
命名规则模板的解析与渲染。

在 str.format 的基础上加了一种语法：`<...>` 可选段 —— 段内任一变量取空值时，
整段（连同段内的字面量前后缀）一并丢弃。它存在的理由只有一个：让同一条规则
同时适配单P与多P。以个人空间为例，`<P{p:02d}->{leaf_title}` 对多P条目渲染成
`P01-第一段`，对单P条目（part_number 为 0）渲染成 `第一段`，而不是留下
`P00-` 这样一截没有意义的前缀。

**求值顺序不可协商**，它是安全边界的一部分：

    FileNameFormatter.__sanitize_component（逐值净化）
        → 本模块解析模板、代入变量值
            → FileNameFormatter.__normalize_path（整串，最后一步）

模板**先解析后代入**，因此变量值里的 `<` `>` 无法注入语法；而可选段只是在
已净化的值之间做拼接，拼接结果整体再过一次路径规范化。任何人不得在
__normalize_path 之后再拼接字符串 —— 那会绕过这条链上的全部防护。

`<` `>` 不提供转义写法。这两个字符在 Windows 文件名里非法，净化逻辑会把
变量值里的它们换成下划线，编辑器的校验器也一直在拒绝字面量里的它们 ——
本项目的输出里从来不可能出现 `<` 或 `>`，转义机制没有正当用途。
"""

from functools import lru_cache
from dataclasses import dataclass
from typing import Mapping
import string
import logging

logger = logging.getLogger(__name__)

# 可选段的嵌套深度上限。正常规则一层足矣，设上限只是为了让畸形输入
# （手改配置文件、或是从别处粘来的串）不至于把解析器递归到爆栈
MAX_DEPTH = 8

class RuleSyntaxError(ValueError):
    """规则模板语法错误，携带出错位置供编辑器把光标定过去"""

    def __init__(self, message: str, position: int):
        super().__init__(message)

        self.position = position

@dataclass(frozen = True)
class TextNode:
    """一段普通文本，内部仍可能含有 {变量} 字段，交给 str.format 处理"""

    text: str

@dataclass(frozen = True)
class OptionalNode:
    """一个 `<...>` 可选段"""

    children: tuple

def is_blank(value) -> bool:
    """
    判断变量「没有取到值」

    EpisodeInfo 里所有字段的 dataclass 默认值就是「未取到」的哨兵：字符串是
    空串，数字是 0。所以判空等价于「等于该类型的默认值」。

    必须看**原始值**而不是渲染结果：单P视频的 part_number 就是 0，`{p:02d}`
    会把它渲染成 "00"，按文本判空根本发现不了 —— 这正是 issue #461 里那截
    `P0-单P标题` 垃圾前缀的来源。

    字符串额外做 strip(" .")：只由空格和点构成的标题在落地时会被
    __normalize_path 清空，提前判空才不会留下孤零零的字面量前后缀。
    """
    if value is None:
        return True

    if isinstance(value, bool):
        # bool 是 int 的子类，但 False 是一个正经取值，不能当成空
        return False

    if isinstance(value, str):
        return not value.strip(" .")

    if isinstance(value, (int, float)):
        return value == 0

    # datetime 等一律视为有值
    return False

class _BlankTrackingFormatter(string.Formatter):
    """
    渲染文本节点，同时记录本段里是否出现过取空值的变量

    一个实例服务于**一个层级**：该层的所有文本节点共用它，于是
    blank_hit / field_count 反映的就是这一段自身（不含嵌套子段）的情况。
    """

    def __init__(self):
        super().__init__()

        self.blank_hit = False
        self.field_count = 0

    def get_field(self, field_name, args, kwargs):
        if "." in field_name or "[" in field_name:
            # {x.__class__} 这类属性穿透在命名规则里没有任何正当用途。
            # 规则串来自用户配置，顺手把这条格式串注入的路径关掉
            raise KeyError(field_name)

        return super().get_field(field_name, args, kwargs)

    def get_value(self, key, args, kwargs):
        if not isinstance(key, str):
            # {} 与 {0} 这类位置参数会绕过变量名校验，一律按未知变量处理
            raise KeyError(key)

        # 未知变量照旧抛 KeyError —— 这是既有的失败契约：变量名拼错必须让
        # 整条规则失败，而不是被可选段悄悄吃掉，变成一个少了一截的文件名
        value = kwargs[key]

        self.field_count += 1

        if is_blank(value):
            self.blank_hit = True

        return value

def _scan_field(rule: str, start: int, strict: bool) -> int:
    """
    从 rule[start] 处的 '{' 扫到配对的 '}'，返回其后一位

    整个字段会被原样拷进文本缓冲，这样 `{title:<20}`、`{pub_time:%Y-%m-%d}`
    里的 `<` `>` 就不会被误当成可选段定界符 —— 它们是对齐符和 strftime 指令。
    嵌套的格式串 `{x:{w}}` 靠深度计数处理。
    """
    if rule.startswith("{{", start):
        return start + 2

    depth = 0
    index = start

    while index < len(rule):
        if rule[index] == "{":
            depth += 1

        elif rule[index] == "}":
            depth -= 1

            if depth == 0:
                return index + 1

        index += 1

    if strict:
        raise RuleSyntaxError("'{' 没有配对的 '}'", start)

    # 宽松模式：当成普通字面量，后续交给 str.format 自己去报错
    return start + 1

def _parse_nodes(rule: str, pos: int, depth: int, strict: bool):
    """
    解析一层节点，返回 (节点元组, 结束位置)

    遇到属于本层的 '>' 或字符串结束时返回。strict 与宽松两种模式的区别只在
    畸形输入上：编辑器要精确报错和位置，运行期则不能因为一个游离尖括号就让
    用户的所有任务都取不到文件名。
    """
    nodes = []
    buffer = []

    def flush():
        if buffer:
            nodes.append(TextNode("".join(buffer)))
            buffer.clear()

    index = pos

    while index < len(rule):
        char = rule[index]

        if char == "{":
            end = _scan_field(rule, index, strict)
            buffer.append(rule[index:end])
            index = end

        elif char == "<":
            if depth + 1 > MAX_DEPTH:
                if strict:
                    raise RuleSyntaxError("可选段嵌套层数过多", index)

                logger.warning("命名规则的可选段嵌套过深，已忽略多余的定界符：%s", rule)

                index += 1
                continue

            flush()

            children, end = _parse_nodes(rule, index + 1, depth + 1, strict)

            if end >= len(rule) or rule[end] != ">":
                if strict:
                    raise RuleSyntaxError("'<' 没有配对的 '>'", index)

                logger.warning("命名规则中的 '<' 没有配对的 '>'，已按普通文本处理：%s", rule)

                nodes.extend(children)
                index = end
                continue

            nodes.append(OptionalNode(tuple(children)))
            index = end + 1

        elif char == ">":
            if depth == 0:
                if strict:
                    raise RuleSyntaxError("'>' 没有配对的 '<'", index)

                # 游离的 '>' 只能丢弃，不能当字面量保留 —— 保留下来会生成
                # 一个在 Windows 上根本打不开的文件名
                logger.warning("命名规则中的 '>' 没有配对的 '<'，已忽略：%s", rule)

                index += 1
                continue

            flush()

            return tuple(nodes), index

        else:
            buffer.append(char)
            index += 1

    flush()

    return tuple(nodes), index

def _iter_text_nodes(nodes):
    for node in nodes:
        if isinstance(node, TextNode):
            yield node
        else:
            yield from _iter_text_nodes(node.children)

def _iter_field_names(text: str):
    """取出一段文本里的全部变量名，连同格式串里嵌套的那些"""
    for _, field_name, format_spec, _ in string.Formatter().parse(text):
        if field_name:
            # {a.b} / {a[0]} 取根名即可，它们本来就会在渲染时被拒绝
            yield field_name.split(".")[0].split("[")[0]

        if format_spec:
            yield from _iter_field_names(format_spec)

def _has_field(nodes) -> bool:
    return any(
        any(True for _ in _iter_field_names(node.text))
        for node in _iter_text_nodes(nodes)
    )

class RuleTemplate:
    """一条编译好的命名规则，可反复渲染"""

    __slots__ = ("rule", "nodes")

    def __init__(self, rule: str, nodes: tuple):
        self.rule = rule
        self.nodes = nodes

    def render(self, data: Mapping) -> str:
        text, _, _, _, _ = self._render_nodes(self.nodes, data)

        return text

    def _render_nodes(self, nodes, data: Mapping):
        """
        渲染一层节点

        返回 (文本, 本层是否命中空变量, 本层变量个数, 嵌套段总数, 嵌套段保留数)。

        文本节点一律**先渲染再判断是否丢弃**：段内写错的变量名即使所在段最终
        会被丢弃，也必须抛出 KeyError，否则编辑器里校验通过的规则到了运行期
        才悄悄少一截。
        """
        formatter = _BlankTrackingFormatter()

        pieces = []
        nested_total = 0
        nested_kept = 0

        for node in nodes:
            if isinstance(node, TextNode):
                pieces.append(formatter.vformat(node.text, (), data))

            else:
                nested_total += 1

                rendered = self._render_optional(node, data)

                if rendered:
                    nested_kept += 1

                pieces.append(rendered)

        return "".join(pieces), formatter.blank_hit, formatter.field_count, nested_total, nested_kept

    def _render_optional(self, node: OptionalNode, data: Mapping) -> str:
        text, blank_hit, field_count, nested_total, nested_kept = self._render_nodes(node.children, data)

        if blank_hit:
            # 段内任一变量为空 → 整段（含字面量前后缀）丢弃。
            # 取「任一」而非「全部」，否则 <S{season_number}E{episode_number}>
            # 在缺集号时会产出 S01E 这样的残缺结果
            return ""

        if field_count == 0 and nested_total and not nested_kept:
            # 自身没有变量、嵌套子段又全被丢弃，只剩下字面量，没有存在意义
            return ""

        return text

    def field_names(self) -> frozenset:
        """规则里用到的全部变量名，供编辑器做未知变量检查，不触发渲染"""
        names = set()

        for node in _iter_text_nodes(self.nodes):
            names.update(_iter_field_names(node.text))

        return frozenset(names)

    def literal_texts(self):
        """
        规则里的全部字面量（即 {} 之外的部分）

        定界符已经被解析器吃掉，所以这些文本里再出现 `<` `>` 就确实是
        用户写下的非法字符，而不是可选段语法
        """
        texts = []

        for node in _iter_text_nodes(self.nodes):
            for literal_text, _, _, _ in string.Formatter().parse(node.text):
                if literal_text:
                    texts.append(literal_text)

        return texts

    def has_empty_optional_segment(self) -> bool:
        """是否存在不含任何变量的可选段 —— 那样的段永远不会被丢弃，写了没用"""
        return self._find_empty_optional(self.nodes)

    def _find_empty_optional(self, nodes) -> bool:
        for node in nodes:
            if isinstance(node, OptionalNode):
                if not _has_field(node.children):
                    return True

                if self._find_empty_optional(node.children):
                    return True

        return False

@lru_cache(maxsize = 256)
def compile_rule(rule: str, strict: bool = False) -> RuleTemplate:
    """
    编译规则模板

    带缓存：一批下载动辄几百个条目，每个条目都要用同一条规则渲染一次。
    刻意写成模块级函数而不是方法，免得把 self 挂进缓存里跟着一起长寿。
    """
    nodes, _ = _parse_nodes(rule, 0, 0, strict)

    return RuleTemplate(rule, nodes)
