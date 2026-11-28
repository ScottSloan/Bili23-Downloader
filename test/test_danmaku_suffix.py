"""
util/parse/additional/danmaku.py —— 弹幕文件后缀词。
"""

from util.common.enum import DanmakuSuffixMode
from util.common.translator import Translator
from util.parse.additional.danmaku import DanmakuParser

import pytest


def test_default_mode():
    result = DanmakuParser.resolve_qualifier(DanmakuSuffixMode.DEFAULT, "abcd")

    assert result == [Translator.ADDITIONAL_FILES_QUALIFIER("DANMAKU")]

def test_none_mode():
    result = DanmakuParser.resolve_qualifier(DanmakuSuffixMode.NONE, "abcd")

    assert result == []

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("dm", ["dm"]),
        (".dm.", ["dm"]),
        (" .dm. ", ["dm"]),
        ("a..b", ["a.b"]),
        ("a...b", ["a.b"]),
        ("my dm", ["my dm"]),
        ("dm/1:2", ["dm_1_2"]),
        ('<>:"/\\|?*', ["_" * 9]),
        ("", []),
        ("   ", []),
        ("...", []),
        (None, []),
    ],
)
def test_custom_mode(raw, expected):
    assert DanmakuParser.resolve_qualifier(DanmakuSuffixMode.CUSTOM, raw) == expected