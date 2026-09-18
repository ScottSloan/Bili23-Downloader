"""
util/format/file_name.py —— 命名规则渲染与路径净化。

这是全项目唯一把**服务端返回的字符串**变成**本地文件路径**的地方，
视频标题、UP 主名、收藏夹名全都由 B 站接口提供，内容不受本程序控制。
因此这里的净化逻辑是安全边界：一旦失效，一个精心构造的标题就能让下载
写到下载目录之外。

format() 内部吞掉了所有异常并返回 None，所以这些用例同时兼有
"不崩" 与 "不逃逸" 两重含义。
"""

from util.format.file_name import FileNameFormatter

from pathlib import Path
import pytest


def render(rule: str, data: dict):
    formatter = FileNameFormatter()
    formatter.set_rule(rule)
    formatter.variable_data = data

    return formatter.format()


class TestSanitize:
    def test_plain_title_untouched(self):
        assert render("{title}", {"title": "正常标题"}) == "正常标题"

    @pytest.mark.parametrize("char", list(r'<>:"/\|?*'))
    def test_windows_reserved_chars_replaced(self, char):
        # 这几个字符在 Windows 上不合法，在 POSIX 上 "/" 还会凭空多出一级目录
        assert render("{title}", {"title": f"a{char}b"}) == "a_b"

    @pytest.mark.parametrize("char", ["\x00", "\x1f", "\n", "\t"])
    def test_control_chars_replaced(self, char):
        assert render("{title}", {"title": f"a{char}b"}) == "a_b"

    def test_non_string_values_pass_through(self):
        # 序号、aid 等是整数，不应被净化逻辑破坏
        assert render("{n}", {"n": 42}) == "42"


class TestPathTraversal:
    """以下每条都是"接口返回的标题不得逃出下载目录"的具体形式"""

    def test_dotdot_inside_variable(self):
        # 变量里的分隔符会被替换成下划线，".." 因此无法独立成段
        result = render("{title}", {"title": "../../etc/passwd"})

        assert ".." not in Path(result).parts
        assert result == "_.._etc_passwd"

    def test_dotdot_as_rule_segment(self):
        # 规则模板里写死的 ".." 段由 strip(" .") 清掉
        result = render("{a}/{b}", {"a": "..", "b": "evil"})

        assert ".." not in Path(result).parts
        assert result == "evil"

    def test_leading_slash_does_not_produce_absolute_path(self):
        # 否则拼接下载目录时前导斜杠会让结果变成绝对路径，直接写到盘根
        assert not Path(render("/{title}", {"title": "x"})).is_absolute()

    def test_trailing_dots_and_spaces_stripped(self):
        # Windows 上以点或空格结尾的目录名无法正常创建与删除
        assert render("{a}/{b}", {"a": "dir. ", "b": "file ."}) == str(Path("dir", "file"))

    def test_empty_render_falls_back(self):
        # 渲染结果为空时不能返回空串：Path("") 是 "."，
        # File.name 会变空、folder 会变 "."，任务建得出来却没有文件名
        assert render("{a}", {"a": ""}) == "_"

    def test_everything_stripped_falls_back(self):
        # 全部字符都被清掉时必须给出一个占位名，不能返回空串让 open() 拿去当路径
        assert render("{a}", {"a": "..."}) == "_"


class TestFailureHandling:
    def test_missing_variable_returns_none(self):
        # 规则里引用了不存在的变量（用户自定义规则写错字）时返回 None，
        # 由调用方回退，而不是让异常冒到下载线程
        assert render("{missing}", {"title": "x"}) is None

    def test_empty_rule_without_type_id_returns_none(self):
        # 既没有显式规则也没有 type_id，get_rule_from_config 返回 None，
        # 于是回退到 FALLBACK_RULE，而它引用的 leaf_title 在空数据里同样不存在
        assert FileNameFormatter().format() is None


class TestTypeMapping:
    def test_attribute_maps_to_convention_type(self):
        from util.parse.episode.tree import Attribute
        from util.common.enum import ConventionType

        formatter = FileNameFormatter()

        assert formatter.get_type_id_from_attribute(Attribute.FAVLIST_BIT) == ConventionType.FAVORITE
        assert formatter.get_type_id_from_attribute(Attribute.SPACE_BIT) == ConventionType.SPACE
        assert formatter.get_type_id_from_attribute(Attribute.BANGUMI_BIT) == ConventionType.BANGUMI

        # 会员购商城课程并入课程，属性位还在但命名类型跟着并了过去
        assert formatter.get_type_id_from_attribute(Attribute.LESSON_BIT) == ConventionType.CHEESE

        # 没有结构形态位也没有来源位的纯投稿视频按单个视频处理；
        # 兜底项排在 type_map 末尾，不会抢走 PART 的判定
        assert formatter.get_type_id_from_attribute(Attribute.VIDEO_BIT) == ConventionType.NORMAL
        assert formatter.get_type_id_from_attribute(
            Attribute.VIDEO_BIT | Attribute.PART_BIT
        ) == ConventionType.PART

    def test_unknown_attribute_returns_none(self):
        assert FileNameFormatter().get_type_id_from_attribute(0) is None


class TestOptionalSegmentSafety:
    """
    可选段不得绕开净化链

    求值顺序是 __sanitize_component（逐值）→ 模板渲染 → __normalize_path（整串）。
    可选段只是在**已净化的值**之间做拼接，拼接结果整体再过一次路径规范化，
    所以上面 TestSanitize / TestPathTraversal 的全部不变式在这里依然成立。
    """

    def test_traversal_inside_an_optional_segment(self):
        result = render("<{title}>", {"title": "../../etc/passwd"})

        assert ".." not in Path(result).parts
        assert result == "_.._etc_passwd"

    def test_separator_inside_an_optional_segment(self):
        # 变量值里的斜杠照样被换成下划线，可选段不能凭空多出一级目录
        assert render("<{a}/>{b}", {"a": "x/y", "b": "n"}) == str(Path("x_y", "n"))

    def test_literal_dotdot_in_an_optional_segment_stripped(self):
        assert render("<{a}/../>{b}", {"a": "dir", "b": "n"}) == str(Path("dir", "n"))

    def test_everything_dropped_falls_back(self):
        # 所有段都被丢弃时结果是占位名，绝不是空串
        assert render("<{a}><{b}>", {"a": "", "b": 0}) == "_"

    def test_unknown_variable_in_a_dropped_segment_still_fails(self):
        # 错误优先于丢弃
        assert render("<{parent_title}{typo}>{title}", {"parent_title": "", "title": "x"}) is None


class TestIssue461EndToEnd:
    """经过 __normalize_path 之后的最终落盘路径"""

    RULE = "{space_owner}/{parent_title}/<P{p:02d}->{leaf_title}"

    def test_single_part(self):
        result = render(self.RULE, {
            "space_owner": "UP主", "parent_title": "", "p": 0, "leaf_title": "单P标题"
        })

        assert result == str(Path("UP主", "单P标题"))

    def test_multi_part(self):
        result = render(self.RULE, {
            "space_owner": "UP主", "parent_title": "分P稿件", "p": 1, "leaf_title": "第一段"
        })

        assert result == str(Path("UP主", "分P稿件", "P01-第一段"))
