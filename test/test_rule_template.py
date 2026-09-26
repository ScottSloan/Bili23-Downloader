"""
util/format/rule_template.py —— 命名规则模板的解析与渲染。

这里守着三件事：

1. **`<` `>` 只在可选段的位置才是定界符**。它们同时是 str.format 的对齐符
   （`{t:>8}`）和 strftime 指令的一部分，扫描器必须绕开 {} 内部。
2. **判空看原始值**。单P视频的 part_number 是 0，`{p:02d}` 会渲染成 "00"，
   按文本判空根本发现不了 —— issue #461 里那截 `P0-单P标题` 就是这么来的。
3. **未知变量 ≠ 空变量**。变量名拼错必须让整条规则失败，哪怕它所在的段
   最终会被丢弃；而已知变量取空值是可选段的正常触发条件，不是错误。
"""

from util.format.rule_template import compile_rule, is_blank, RuleSyntaxError

from datetime import datetime
import pytest


def render(rule: str, data: dict):
    return compile_rule(rule).render(data)


class TestDelimiterScanning:
    """`<` `>` 在 {} 内部不是定界符"""

    def test_alignment_spec_is_not_a_segment(self):
        assert render("{t:>6}", {"t": "ab"}) == "    ab"
        assert render("{t:<6}", {"t": "ab"}) == "ab    "

    def test_strftime_spec_untouched(self):
        assert render("{d:%Y-%m-%d}", {"d": datetime(2026, 3, 7)}) == "2026-03-07"

    def test_nested_format_spec(self):
        assert render("{t:{w}}", {"t": "ab", "w": ">6"}) == "    ab"

    def test_doubled_braces_are_literal(self):
        assert render("{{{t}}}", {"t": "x"}) == "{x}"


class TestSyntaxErrors:
    """严格模式给编辑器精确报错，宽松模式让运行期活下去"""

    @pytest.mark.parametrize(("rule", "position"), [
        ("<{a}", 0),
        ("{a}>", 3),
        ("<{a}>>", 5),
    ])
    def test_strict_reports_position(self, rule, position):
        with pytest.raises(RuleSyntaxError) as error:
            compile_rule(rule, True)

        assert error.value.position == position

    @pytest.mark.parametrize("rule", ["<{a}", "{a}>"])
    def test_lenient_mode_survives(self, rule):
        # 手改过配置文件的用户不该因为一个游离尖括号就让所有任务取不到文件名。
        # 游离的定界符一律丢弃，保留下来会生成 Windows 上打不开的文件名
        assert render(rule, {"a": "X"}) == "X"

    def test_depth_limit(self):
        with pytest.raises(RuleSyntaxError):
            compile_rule("<" * 9 + "{a}" + ">" * 9, True)


class TestIsBlank:
    @pytest.mark.parametrize("value", [None, "", "   ", "...", " . ", 0, 0.0])
    def test_blank(self, value):
        assert is_blank(value)

    @pytest.mark.parametrize("value", ["0", False, True, 1, -1, 0.5, datetime(2026, 3, 7)])
    def test_not_blank(self, value):
        # False 是 int 的子类但它是一个正经取值；"0" 是有内容的字符串
        assert not is_blank(value)


class TestOptionalSegment:
    def test_part_number_zero_drops_the_whole_segment(self):
        # 本模块的头号回归用例：单P视频的 p 是 0，整段必须消失，
        # 而不是渲染成 P00-
        assert render("<P{p:02d}->{leaf_title}", {"p": 0, "leaf_title": "标题"}) == "标题"

    def test_part_number_present_keeps_the_segment(self):
        assert render("<P{p:02d}->{leaf_title}", {"p": 1, "leaf_title": "标题"}) == "P01-标题"

    def test_any_semantics(self):
        # 取「任一为空即丢弃」而非「全部为空」，否则缺集号时会产出 S01E
        assert render("<S{a:02d}E{b:02d}>", {"a": 1, "b": 0}) == ""
        assert render("<S{a:02d}E{b:02d}>", {"a": 1, "b": 8}) == "S01E08"

    def test_literal_prefix_and_suffix_go_with_it(self):
        assert render("【<{a}>】", {"a": ""}) == "【】"
        assert render("<【{a}】>", {"a": ""}) == ""

    def test_nested_segments(self):
        assert render("<{a}/<{b}/>>", {"a": "A", "b": "B"}) == "A/B/"
        assert render("<{a}/<{b}/>>", {"a": "A", "b": ""}) == "A/"
        assert render("<{a}/<{b}/>>", {"a": "", "b": "B"}) == ""

    def test_literal_only_outer_segment_collapses(self):
        # 外层自己没有变量，嵌套子段又全被丢弃，只剩字面量，没有存在意义
        assert render("x<-<{b}>>y", {"b": ""}) == "xy"
        assert render("x<-<{b}>>y", {"b": "B"}) == "x-By"


class TestFailureContract:
    def test_unknown_variable_raises(self):
        with pytest.raises(KeyError):
            render("{titel}", {"title": "x"})

    def test_unknown_variable_inside_a_dropped_segment_still_raises(self):
        # 错误优先于丢弃：段内写错的变量名即使所在段会被丢弃也必须报错，
        # 否则编辑器里校验通过的规则，到了运行期才悄悄少一截
        with pytest.raises(KeyError):
            render("<{parent_title}{typo}>", {"parent_title": ""})

    @pytest.mark.parametrize("rule", ["{a.__class__}", "{a[0]}", "{}", "{0}"])
    def test_field_injection_rejected(self, rule):
        # 规则串来自用户配置，属性穿透与位置参数一律按未知变量处理
        with pytest.raises(KeyError):
            render(rule, {"a": "x"})


class TestIntrospection:
    """供编辑器复用，不触发渲染"""

    def test_field_names(self):
        template = compile_rule("{a}/<P{b:02d}-{c}>")

        assert template.field_names() == frozenset({"a", "b", "c"})

    def test_field_names_include_nested_spec(self):
        assert compile_rule("{t:{w}}").field_names() == frozenset({"t", "w"})

    def test_literal_texts_exclude_delimiters(self):
        # 定界符已被解析器吃掉，剩下的 < > 就确实是用户写的非法字符
        assert compile_rule("【{a}】/<P{b}->").literal_texts() == ["【", "】/", "P", "-"]

    def test_empty_optional_segment_detected(self):
        assert compile_rule("<abc>{a}").has_empty_optional_segment()
        assert not compile_rule("<P{b}>").has_empty_optional_segment()

    def test_empty_optional_segment_detected_when_nested(self):
        assert compile_rule("<{a}<abc>>").has_empty_optional_segment()


class TestIssue461:
    """一条规则同时适配单P与多P —— 这是整个特性存在的理由"""

    RULE = "{space_owner}/{parent_title}/<P{p:02d}->{leaf_title}"

    def test_single_part(self):
        result = render(self.RULE, {
            "space_owner": "UP主", "parent_title": "", "p": 0, "leaf_title": "单P标题"
        })

        # 空的目录层留下一个空路径段，由 FileNameFormatter.__normalize_path 收敛
        assert result == "UP主//单P标题"

    def test_multi_part(self):
        result = render(self.RULE, {
            "space_owner": "UP主", "parent_title": "分P稿件", "p": 1, "leaf_title": "第一段"
        })

        assert result == "UP主/分P稿件/P01-第一段"
