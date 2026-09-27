"""
util/parse/additional/file/danmaku_xml.py —— 弹幕 XML 生成。

弹幕文本完全由服务端提供，且会被原样嵌进 XML。转义一旦失效，产出的就是
一个无法被任何播放器读取的非法文件 —— 而下载流程本身不会报错，用户只会发现
"弹幕没了"。因此这里用 xml.etree 真正解析一遍产物，而不是比对字符串。
"""

from util.parse.additional.file.danmaku_xml import DanmakuXML

from xml.etree import ElementTree
import pytest


def entry(**overrides):
    base = {
        "stime": 12340,
        "mode": 1,
        "size": 25,
        "color": 16777215,
        "date": 1700000000,
        "uhash": "abc",
        "dmid": "999",
        "text": "普通弹幕",
    }
    base.update(overrides)

    return base


def generate(entries):
    return DanmakuXML(entries, cid = 12345).generate()


class TestWellFormed:
    def test_output_is_parseable(self):
        root = ElementTree.fromstring(generate([entry()]))

        assert root.tag == "i"
        assert root.findtext("chatid") == "12345"

    def test_empty_list(self):
        root = ElementTree.fromstring(generate([]))

        assert root.findall("d") == []

    @pytest.mark.parametrize(
        "text",
        [
            "a<b>c",
            "a&b",
            'a"b',
            "a'b",
            "&lt;",                 # 已经像转义序列的文本不能被二次破坏
            "<![CDATA[x]]>",
            "</d><d p=\"0\">注入",   # 构造出的闭合标签不得改变文档结构
            "&amp;<>&",
        ],
    )
    def test_special_characters_keep_document_valid(self, text):
        root = ElementTree.fromstring(generate([entry(text = text)]))

        # 只能有一个 <d>，说明注入没有制造出额外节点
        assert len(root.findall("d")) == 1
        # 解析回来的文本必须与原文完全一致
        assert root.find("d").text == text

    def test_ampersand_escaped_first(self):
        # & 必须最先替换，否则 "<" → "&lt;" 之后的 & 会被二次转义成 "&amp;lt;"
        assert "&amp;lt;" not in generate([entry(text = "<")])

    @pytest.mark.parametrize("char", ["\x00", "\x01", "\x08", "\x1f", "\x7f"])
    def test_control_characters_removed(self, char):
        # 这些字符在 XML 1.0 中非法，保留会让整个文件无法解析
        root = ElementTree.fromstring(generate([entry(text = f"a{char}b")]))

        assert root.find("d").text == "ab"


class TestPAttribute:
    def test_has_exactly_eight_fields(self):
        # B 站弹幕的 p 属性是固定 8 字段：
        # 时间,模式,字号,颜色,发送时间,弹幕池,用户hash,弹幕ID
        root = ElementTree.fromstring(generate([entry()]))

        assert len(root.find("d").get("p").split(",")) == 8

    def test_field_order(self):
        root = ElementTree.fromstring(generate([entry()]))
        stime, mode, size, color, date, pool, uhash, dmid = root.find("d").get("p").split(",")

        assert stime == "12.34000"      # 毫秒转秒，保留 5 位小数
        assert mode == "1"
        assert size == "25"
        assert color == "16777215"
        assert date == "1700000000"
        assert pool == "0"
        assert uhash == "abc"
        assert dmid == "999"

    def test_weight_is_not_emitted(self):
        # weight 不属于 p 属性。它曾被当作 format 实参传入却无处可去，
        # 被 str.format 静默丢弃（ruff F522）。这里确保它不会在将来被误加进来
        root = ElementTree.fromstring(generate([entry(weight = 7)]))

        assert "7" not in root.find("d").get("p").split(",")

    def test_missing_fields_fall_back_to_defaults(self):
        # 服务端省略默认值字段（protobuf 的 MessageToDict 行为），取值必须有兜底
        root = ElementTree.fromstring(generate([{"stime": 1000, "text": "x"}]))

        assert root.find("d").get("p").split(",") == ["1.00000", "1", "25", "16777215", "0", "0", "0", "0"]
