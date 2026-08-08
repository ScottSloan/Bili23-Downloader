import json as std_json
import logging

logger = logging.getLogger(__name__)

# 尝试导入 orjson，如果导入失败，则回退到标准库的 json 模块
_orjson_available = False

try:
    import orjson as json

    _orjson_available = True

except ImportError:
    import json

    _orjson_available = False

    logger.warning("无法导入 orjson 模块，已回退到标准库的 json 模块")

def json_dumps(obj, indent = None):
    if _orjson_available:
        # orjson 仅支持 2 空格缩进；未指定 indent 时输出紧凑格式，避免入库数据额外膨胀一倍
        return json.dumps(obj, option = json.OPT_INDENT_2 if indent else None).decode("utf-8")
    else:
        return json.dumps(obj, indent = indent)
    
def json_dumps_stable(obj):
    # 供计算持久化哈希使用，输出格式必须永远保持稳定。
    #
    # json_dumps 的结果取决于运行时有没有 orjson，也曾因为 indent 判断修改而变化过，
    # 一旦用它计算入库的哈希，换个环境或升级一次版本，历史记录就全部对不上了。
    # 因此这里固定走标准库，并显式锁定分隔符、键序与转义方式。
    return std_json.dumps(obj, sort_keys = True, separators = (",", ":"), ensure_ascii = True)

def json_loads(s):
    if _orjson_available:
        return json.loads(s)
    else:
        return json.loads(s)
