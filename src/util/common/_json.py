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
    
def json_loads(s):
    if _orjson_available:
        return json.loads(s)
    else:
        return json.loads(s)
