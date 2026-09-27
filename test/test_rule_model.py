"""
util/format/rule_model.py —— 可视化编辑器与 raw 规则串之间的双向桥。

两条不变式：

1. **往返无损**：parse_rule(model.to_rule()) == model。可视化编辑器每改一次
   都会重新序列化再解析回来，这条一旦破了，用户的改动会在切换规则时丢失。
2. **表达不了要说出来**：可视化能表达的是 raw 语法的真子集，解析不回来时
   必须返回带原因的 UnsupportedRule，绝不抛异常，更不能悄悄丢掉一部分。
"""

from util.format.rule_model import parse_rule, RuleModel, Level, Fragment, UnsupportedRule
from util.format.rule_template import compile_rule
from util.common.config import DefaultValue

import pytest


class TestRoundTrip:
    @pytest.mark.parametrize("rule", [
        "{leaf_title}",
        "{parent_title}/P{p}-{leaf_title}",
        "{a}/<P{p:02d}->{b}",
        "{pub_time:%Y-%m}/{leaf_title}",
        "{uploader} - {leaf_title}",
        "【{a}】{b}",
        "{{{a}}}",
    ])
    def test_parse_serialize_parse(self, rule):
        model = parse_rule(rule)

        assert isinstance(model, RuleModel)
        assert model.to_rule() == rule
        assert parse_rule(model.to_rule()) == model

    @pytest.mark.parametrize("entry", DefaultValue.naming_rule_list, ids = lambda e: e["name"])
    def test_default_rules_are_all_representable(self, entry):
        # 内置规则必须全都能在可视化编辑器里打开，否则用户一进去就看到降级提示
        model = parse_rule(entry["rule"])

        assert isinstance(model, RuleModel), getattr(model, "reason", "")
        assert model.to_rule() == entry["rule"]

    def test_serialized_output_is_always_valid(self):
        model = RuleModel(levels = [
            Level([Fragment(variable = "a")]),
            Level([
                Fragment(prefix = "P", variable = "p", spec = "02d", suffix = "-"),
                Fragment(text = "【x】"),
                Fragment(variable = "b"),
            ]),
        ])

        # to_rule() 的输出必须恒能被严格模式接受
        compile_rule(model.to_rule(), True)


class TestNormalization:
    def test_optional_directory_level_is_flattened(self):
        # 空的目录层本来就会被 __normalize_path 丢掉，<{b}/> 与 {b}/ 等价。
        # 统一成普通目录层，可视化编辑器才不必为它专门画一种形态
        model = parse_rule("{a}/<{b}/>{c}")

        assert model.to_rule() == "{a}/{b}/{c}"
        assert len(model.levels) == 3

    def test_no_optional_segment_spans_a_separator(self):
        assert "/>" not in parse_rule("{a}/<{b}/>{c}").to_rule()


class TestStructure:
    def test_levels_split_on_separator(self):
        model = parse_rule("{a}/{b}/{c}")

        assert [len(level.fragments) for level in model.levels] == [1, 1, 1]

    def test_prefix_and_suffix_captured(self):
        fragment = parse_rule("<P{p:02d}->{t}").levels[0].fragments[0]

        assert (fragment.prefix, fragment.variable, fragment.spec, fragment.suffix) == ("P", "p", "02d", "-")
        assert fragment.is_optional

    def test_plain_field_is_not_optional(self):
        fragment = parse_rule("{t}").levels[0].fragments[0]

        assert not fragment.is_optional
        assert not fragment.is_text

    def test_adjacent_text_is_merged(self):
        # 不合并的话往返一次就会多出几个空壳片段，破坏不变式 1
        level = parse_rule("a{x}bc").levels[0]

        assert [fragment.text for fragment in level.fragments if fragment.is_text] == ["a", "bc"]


class TestUnsupported:
    @pytest.mark.parametrize("rule", [
        "<{a}-{b}>",        # 段内多个变量
        "<{a}<{b}>>",       # 嵌套可选段
        "<abc>",            # 不含变量的可选段
        "{a!r}",            # 转换符
        "{a:{w}}",          # 嵌套格式串
        "<x{a}/y>",         # 跨目录层级的可选段
        "<{a}",             # 语法错误
        "{a.b}",            # 属性穿透
    ])
    def test_returns_reason_instead_of_raising(self, rule):
        result = parse_rule(rule)

        assert isinstance(result, UnsupportedRule)
        assert result.reason
