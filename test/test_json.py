"""
util/common/_json.py 的契约测试。

这个模块有两条实现（orjson 与标准库），运行时走哪条取决于环境里有没有 orjson，
而 CI 上 orjson 永远装得上 —— 回退分支因此在测试里从来没有被执行过。
下面用「屏蔽 orjson 后把模块重新加载一份」的办法同时拿到两条实现，逐一比对。

这不是假想的风险。回退分支里曾经有过：紧凑输出用的是标准库默认的 (", ", ": ")
分隔符（orjson 是 (",", ":")，同一份数据两边写出的字节完全不同），以及一处
`case 4: return OPT_INDENT_2` 的复制粘贴错误 —— 两者都只在回退环境下才暴露。
"""
from pathlib import Path
import importlib.util
import json as std_json
import sys

MODULE_PATH = Path(__file__).resolve().parent.parent / "src" / "util" / "common" / "_json.py"

# 覆盖两条实现都要产出一致结果的数据形态：中文、嵌套、空容器、转义、顶层标量
PAYLOADS = [
    {"a": 1, "b": "中文"},
    {"nested": {"list": [1, 2, {"deep": None}], "flag": True}},
    {"empty_dict": {}, "empty_list": []},
    ["顶层数组", 1, 2.5, False, None],
    {"escape": "换行\n制表\t引号\"反斜杠\\", "emoji": "😀", "控制字符": "\x00\x1f"},
    {},
    [],
    "顶层字符串",
    42,
]


def _load(module_name, *, block_orjson):
    """把 _json.py 当普通文件加载一份，可选屏蔽 orjson 以强制走回退分支"""
    missing = object()
    saved = sys.modules.get("orjson", missing)

    if block_orjson:
        # sys.modules 里的 None 会让 `import orjson` 抛 ImportError，
        # 正是回退分支要触发的那条路径
        sys.modules["orjson"] = None

    try:
        spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)

        return module

    finally:
        if block_orjson:
            if saved is missing:
                del sys.modules["orjson"]

            else:
                sys.modules["orjson"] = saved


FAST = _load("_json_fast_path", block_orjson = False)
FALLBACK = _load("_json_fallback_path", block_orjson = True)


def test_orjson_is_installed_in_test_env():
    # requirements.txt 里 orjson 是硬依赖。缺了它，下面所有"两条实现一致"的比对
    # 会退化成同一个实现自己跟自己比 —— 仍然全绿，但什么都验证不到
    assert FAST.orjson is not None, "测试环境缺少 orjson，本文件的跨实现比对失去意义"


def test_both_implementations_export_the_same_api():
    for name in ("dumps", "dumps_bytes", "loads", "dumps_std", "dumps_stable", "JSONDecodeError"):
        assert hasattr(FAST, name), f"orjson 路径缺少 {name}"
        assert hasattr(FALLBACK, name), f"回退路径缺少 {name}"


def test_dumps_agrees_across_implementations():
    for payload in PAYLOADS:
        for indent in (None, 2):
            fast = FAST.dumps(payload, indent = indent)
            fallback = FALLBACK.dumps(payload, indent = indent)

            assert fast == fallback, (
                f"两条实现写出的字节不同（indent={indent}）：\n"
                f"  入参：    {payload!r}\n  orjson：  {fast!r}\n  标准库：  {fallback!r}"
            )


def test_compact_output_carries_no_padding_spaces():
    # 回退分支曾经漏掉这个对齐：标准库默认分隔符是 (", ", ": ")，
    # 于是没装 orjson 的环境写出的 JSON 处处多个空格
    for module in (FAST, FALLBACK):
        assert module.dumps({"a": 1, "b": [2, 3]}) == '{"a":1,"b":[2,3]}'


def test_indent_two_uses_two_spaces():
    for module in (FAST, FALLBACK):
        assert module.dumps({"a": {"b": 1}}, indent = 2) == '{\n  "a": {\n    "b": 1\n  }\n}'


def test_float_formatting_survives_round_trip():
    """
    浮点数的字符串形式两条实现本来就不同（orjson 写 1e-7，标准库写 1e-07），
    模块的承诺是"格式约定一致"而非"逐字节一致"，这里钉住承诺的下限：
    解析回来必须是同一个值。这条用例同时是 dumps_stable 存在理由的注脚 ——
    拿 dumps 的输出算哈希，换个环境就对不上了。
    """
    payload = [1e-7, 1e16, 0.1 + 0.2, 1 / 3, -0.0, 1.5]

    assert FAST.loads(FAST.dumps(payload)) == FALLBACK.loads(FALLBACK.dumps(payload)) == payload


def test_dumps_rejects_unsupported_indent():
    # orjson 只有 2 空格一档缩进，与其静默降级（换个环境又变回传入的宽度），
    # 不如当场报错。需要别的宽度请用 dumps_std()
    for module in (FAST, FALLBACK):
        try:
            module.dumps({"a": 1}, indent = 4)

        except ValueError as e:
            assert "dumps_std" in str(e), "错误信息应指向正确的替代方案"

        else:
            raise AssertionError("indent=4 应当被拒绝")


def test_dumps_std_honours_indent_and_ascii():
    for module in (FAST, FALLBACK):
        text = module.dumps_std({"中文": {"键": "值"}}, indent = 4)

        assert text == std_json.dumps({"中文": {"键": "值"}}, indent = 4, ensure_ascii = False)
        assert "\n    \"" in text, "indent=4 应当产生四空格缩进"

        # stdio 桥接依赖这一条：写出去的字节必须是纯 ASCII
        assert module.dumps_std({"中文": 1}, ensure_ascii = True).isascii()


def test_dumps_stable_is_byte_identical_across_implementations():
    # 计算持久化哈希的路径，格式必须与实现、与环境都无关
    first = {"b": 2, "a": "中文"}
    second = {"a": "中文", "b": 2}

    assert FAST.dumps_stable(first) == FALLBACK.dumps_stable(first)
    assert FAST.dumps_stable(first) == FAST.dumps_stable(second), "键序不应影响结果"
    assert FAST.dumps_stable(first).isascii()


def test_dumps_bytes_matches_dumps_encoded():
    for module in (FAST, FALLBACK):
        for indent in (None, 2):
            payload = {"中文": [1, {"a": None}]}

            assert module.dumps_bytes(payload, indent = indent) == module.dumps(payload, indent = indent).encode("utf-8")


def test_loads_accepts_str_and_bytes():
    for module in (FAST, FALLBACK):
        assert module.loads('{"中文": 1}') == {"中文": 1}
        assert module.loads('{"中文": 1}'.encode("utf-8")) == {"中文": 1}


def test_jsondecodeerror_catches_every_implementation():
    # 统一暴露标准库那个类：orjson.JSONDecodeError 是它的子类，
    # 所以调用方一句 `except JSONDecodeError` 就能覆盖两条实现，不必知道 orjson 在不在
    assert FAST.JSONDecodeError is std_json.JSONDecodeError
    assert FALLBACK.JSONDecodeError is std_json.JSONDecodeError

    for module in (FAST, FALLBACK):
        try:
            module.loads("{ 不是合法 JSON")

        except module.JSONDecodeError:
            pass

        else:
            raise AssertionError("非法 JSON 应当抛出 JSONDecodeError")

    if FAST.orjson is not None:
        assert issubclass(FAST.orjson.JSONDecodeError, std_json.JSONDecodeError)
