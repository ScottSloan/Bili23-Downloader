"""
JSON 编解码的统一入口。

优先用 orjson —— 解析 B 站的大响应体时比标准库快得多；导入失败则回退标准库，
让没有预编译轮子的环境仍能跑起来。选哪条实现由**导入期**决定，两种情况下本模块
导出的都是同一组函数。

对外承诺的是**格式一致**，不是逐字节一致：同一份入参，两条实现产出的 JSON 结构
相同，缩进与分隔符的约定也相同（紧凑输出都不带空格，indent=2 都是两个空格）。
逐字节一致做不到，也不该假装做得到 —— 浮点数的字符串形式两边本来就不同
（orjson 写 1e-7，标准库写 1e-07），有些类型更是只有一边能序列化，见 dumps()。
凡是要把输出字节写进持久化结构（哈希、去重判定）的地方，一律用 dumps_stable()。
"""
import json as std_json
import logging

logger = logging.getLogger(__name__)

try:
    import orjson

except ImportError:
    orjson = None

    logger.warning("无法导入 orjson 模块，已回退到标准库的 json 模块")

# orjson.JSONDecodeError 是标准库这个类的**子类**，因此统一对外暴露标准库的类：
# 无论哪条实现抛出的解码错误，调用方的 `except JSONDecodeError` 都接得住，
# 调用方也不必知道 orjson 在不在
JSONDecodeError = std_json.JSONDecodeError

# 紧凑输出（indent=None）用的分隔符。orjson 恒为 (",", ":")，标准库默认是
# (", ", ": ")，不在回退分支里对齐的话，没装 orjson 的环境写出的 JSON
# 会凭空多出一堆空格
_COMPACT_SEPARATORS = (",", ":")

if orjson is not None:
    def _dumps(obj, indent) -> str:
        return orjson.dumps(obj, option = orjson.OPT_INDENT_2 if indent else None).decode("utf-8")

    def _dumps_bytes(obj, indent) -> bytes:
        # orjson 本来就返回 bytes，直接交出去，不经过 str 再 encode 一次
        return orjson.dumps(obj, option = orjson.OPT_INDENT_2 if indent else None)

    def _loads(s):
        return orjson.loads(s)

else:
    def _dumps(obj, indent) -> str:
        if indent:
            return std_json.dumps(obj, indent = indent, ensure_ascii = False)

        return std_json.dumps(obj, separators = _COMPACT_SEPARATORS, ensure_ascii = False)

    def _dumps_bytes(obj, indent) -> bytes:
        return _dumps(obj, indent).encode("utf-8")

    def _loads(s):
        return std_json.loads(s)


def _check_indent(indent):
    # orjson 只有 2 空格一档缩进，别的值没法在两条实现下得到相同结果。
    # 与其静默降级成 2（换个环境又变回传入的宽度），不如当场报错
    if indent not in (None, 2):
        raise ValueError(f"indent 只支持 None 或 2，收到 {indent!r}；需要其它缩进宽度请用 dumps_std()")

def dumps(obj, indent = None) -> str:
    """
    序列化为字符串，日常都用这个。indent 只支持 None（紧凑）与 2（两空格）

    两条实现之间还有几处**能力**差异，都是 orjson 自身的取舍。用之前确认入参里
    没有下面这些值，否则换个环境就会抛异常、或者写出不一样的东西：

    - datetime / date：orjson 直接写成 RFC3339 字符串，标准库抛 TypeError
    - 超过 64 位的整数、非字符串的 dict 键：orjson 抛 TypeError，标准库能处理
    - NaN / Infinity：orjson 写 null，标准库写 NaN —— 后者不是合法 JSON

    需要别的缩进宽度、或要求纯 ASCII 输出时，用 dumps_std()。
    """
    _check_indent(indent)

    return _dumps(obj, indent)

def dumps_bytes(obj, indent = None) -> bytes:
    """
    序列化为 UTF-8 字节，给写 socket、写管道这类地方用

    与 dumps() 的差别只是省掉一次 str ↔ bytes 往返，格式约定完全相同。
    """
    _check_indent(indent)

    return _dumps_bytes(obj, indent)

def loads(s):
    """
    反序列化，接受 str 与 bytes

    抛出的异常一律是 JSONDecodeError（标准库那个类），调用方不必关心当前是哪条实现
    """
    return _loads(s)

def dumps_std(obj, indent = None, ensure_ascii = False) -> str:
    """
    恒定走标准库的出口，用于**必须精确控制输出格式**的场景

    与 dumps() 的差别不是快慢，而是格式可不可控：orjson 只有 2 空格一档缩进、
    也转义不了非 ASCII，凡是要 4 空格缩进或纯 ASCII 输出的地方都只能走这里
    （配置文件落盘、stdio 桥接写给客户端）。代价是丢掉 orjson 的性能，
    因此只该用在低频路径上。
    """
    return std_json.dumps(obj, indent = indent, ensure_ascii = ensure_ascii)

def dumps_stable(obj) -> str:
    # 供计算持久化哈希使用，输出格式必须永远保持稳定。
    #
    # dumps 的结果取决于运行时有没有 orjson，也曾因为 indent 判断修改而变化过，
    # 一旦用它计算入库的哈希，换个环境或升级一次版本，历史记录就全部对不上了。
    # 因此这里固定走标准库，并显式锁定分隔符、键序与转义方式。
    return std_json.dumps(obj, sort_keys = True, separators = _COMPACT_SEPARATORS, ensure_ascii = True)
