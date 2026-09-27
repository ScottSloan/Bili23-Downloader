"""
util/parse/worker.py —— 解析类型与 wbi 签名的对应关系。

签名密钥没就绪时，解析界面会先等密钥到位再发起解析，而这份分类决定了「哪些解析需要等」。
分错了不会报任何错，只会在弱网下表现成两种坏结果之一：

* 该等的没等 —— 用户看到「解析失败」，以为程序坏了，正是这份分类要消除的观感；
* 不该等的等了 —— 番剧、课程这些打非签名接口、本可能成功的解析被一起停摆 65 秒。

所以这里直接对着解析器源码核对，而不是把常量复述一遍：将来新增解析器、
或者某个解析器改用 / 停用 wbi 签名，这里都会红。
"""

from pathlib import Path

import pytest

from util.parse.worker import NO_WBI_PARSER_TYPES, WBI_PARSER_TYPES, needs_wbi_signature


PARSER_DIR = Path(__file__).resolve().parent.parent / "src" / "util" / "parse" / "parser"

CLASSIFIED = sorted(WBI_PARSER_TYPES | NO_WBI_PARSER_TYPES)

# 不走解析界面这道闸门的解析器，每个都写明原因：
#   b23 / festival —— 短链，真实的解析类型要请求一次才知道，拦下来可能误伤番剧链接
#   favorite       —— 只由「我的收藏」浮出控件直接调用，不经过 ParseWorker
#   dynamic        —— 由自动解析驱动，而自动解析的前置条件本来就是一次已成功的解析
UNCLASSIFIED_PARSERS = {"b23", "festival", "favorite", "dynamic"}

# parser/ 下的非解析器模块
NOT_A_PARSER = {"base", "__init__"}


def test_the_two_sets_do_not_overlap():
    assert not (WBI_PARSER_TYPES & NO_WBI_PARSER_TYPES)


def test_every_parser_module_is_accounted_for():
    """
    新增解析器时必须在分类里明确表态一次，不能默认漏到「不需要签名」那一侧。

    漏了不会有任何运行期表现，直到弱网下用户点解析、弹出一条「解析失败」。
    """
    present = {path.stem for path in PARSER_DIR.glob("*.py")} - NOT_A_PARSER
    accounted = set(CLASSIFIED) | UNCLASSIFIED_PARSERS

    assert present == accounted, (
        "以下解析器模块没有被归入任何一类，请在上面的集合里补上并说明理由：\n"
        f"  仅在磁盘上：{sorted(present - accounted)}\n"
        f"  仅在分类里：{sorted(accounted - present)}"
    )


@pytest.mark.parametrize("parser_type", CLASSIFIED)
def test_classification_matches_the_parser_source(parser_type):
    source = (PARSER_DIR / f"{parser_type}.py").read_text(encoding = "utf-8")
    uses_wbi = "enc_wbi" in source

    assert uses_wbi == (parser_type in WBI_PARSER_TYPES), (
        f"{parser_type}.py {'用到了' if uses_wbi else '没有用到'} enc_wbi，"
        "与 WBI_PARSER_TYPES 的分类不符"
    )


@pytest.mark.parametrize("parser_type", sorted(UNCLASSIFIED_PARSERS))
def test_unclassified_parsers_are_not_gated(parser_type):
    assert not needs_wbi_signature(parser_type), (
        f"{parser_type} 的真实类型要请求一次才知道，拦下来可能误伤本可成功的解析"
    )


def test_needs_wbi_signature_covers_exactly_the_wbi_set():
    for parser_type in CLASSIFIED:
        assert needs_wbi_signature(parser_type) == (parser_type in WBI_PARSER_TYPES)

    # 闸门只认已知类型；将来新增类型在表态之前，一律不拦
    assert not needs_wbi_signature("某种还没表态的类型")
