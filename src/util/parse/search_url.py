from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from ..common.data import url_patterns

# B 站部分接口本身就支持按关键词搜索，但承载关键词的查询参数名并不统一
# 键为 url_patterns 中的解析类型标识，只有登记在此的类型才支持服务端搜索
# 合集（list）、每周必看（popular）等接口没有搜索参数，因此不在其列
KEYWORD_PARAMS = {
    "space": "keyword",
    "favlist": "keyword",
    "history": "keyword",
    "watch_later": "key"
}

def get_keyword_param(url: str):
    # 取出链接对应解析类型的关键词参数名，不支持服务端搜索时返回空字符串
    for parser_type, pattern in url_patterns:
        if pattern.search(url):
            return KEYWORD_PARAMS.get(parser_type, "")

    return ""

def support_search(url: str):
    return bool(get_keyword_param(url))

def extract_keyword(url: str):
    # 从链接中提取搜索关键词，parse_qs 会自动完成百分号解码
    param = get_keyword_param(url)

    if not param:
        return ""

    query = parse_qs(urlparse(url).query)

    return query.get(param, [""])[0].strip()

def build_search_url(url: str, keyword: str):
    # 将关键词写回链接，关键词为空时移除该参数，即恢复为完整列表
    # 关键词一律随链接传递，翻页、自动解析分页、解析历史都直接复用链接，无需另行维护搜索状态
    param = get_keyword_param(url)

    if not param:
        return url

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    keyword = keyword.strip()

    if keyword:
        query[param] = [keyword]
    else:
        query.pop(param, None)

    return urlunparse(parsed._replace(query = urlencode(query, doseq = True)))
