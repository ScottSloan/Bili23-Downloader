"""
下载列表的搜索与类型筛选判定

下载中列表在内存里逐条判定，已完成列表把同一份判定注册成 SQLite 函数、在数据库里执行
（见 TaskDatabase._setup_connection）。两边必须共用这一份实现：各写一套的话，迟早会出现
同一个关键词在一个列表里搜得到、换到另一个列表就搜不到的情况
"""

from ...common.enum import DownloadType
from ...common._json import loads
from ...parse.episode.tree import Attribute

from functools import lru_cache

# 可搜索的字段：(data 列中的 JSON 路径, 从 TaskInfo 取值的函数)
# 只收建任务时就定下来、用户认得出的字段。task_id 是内部哈希，info_label / status_label
# 是随界面语言与下载进度变化的展示文案（「3 秒后重试」），搜得到反而让结果忽隐忽现
SEARCH_FIELDS = (
    ("$.Basic.show_title", lambda task_info: task_info.Basic.show_title),
    ("$.File.name", lambda task_info: task_info.File.name),
    ("$.Episode.uploader", lambda task_info: task_info.Episode.uploader),
    ("$.Episode.bvid", lambda task_info: task_info.Episode.bvid),
    ("$.Episode.parent_title", lambda task_info: task_info.Episode.parent_title),
    ("$.Episode.collection_title", lambda task_info: task_info.Episode.collection_title),
    ("$.Episode.series_title", lambda task_info: task_info.Episode.series_title),
    ("$.Episode.season_title", lambda task_info: task_info.Episode.season_title),
    ("$.Episode.favorites_name", lambda task_info: task_info.Episode.favorites_name),
)

# 注册到 SQLite 的函数名与它要读的 JSON 路径：可搜索字段在前，媒体类型判定用的两个字段在最后。
# 多路径的 json_extract 只解析一次 JSON、返回一个数组，比逐字段各调一次快
SQL_MATCH_FUNCTION = "bili23_task_matches"
SQL_MATCH_PATHS = tuple(path for path, _ in SEARCH_FIELDS) + ("$.Episode.attribute", "$.Download.type")

def media_type_key(attribute: int, download_type: int):
    """
    任务的媒体类型，取值为 MEDIA_TYPE_BADGE 的 key，判断不出时返回空串

    封面角标与列表的类型筛选共用这一份判断：两边各写一套的话，迟早会出现
    角标写着「音频」、按音频筛选却筛不出来的情况
    """
    attribute = attribute or 0
    download_type = download_type or 0

    # 仅下载音频时，产物就是音频文件，无论来源是投稿、番剧还是课程，都直接标「音频」
    audio_only = download_type & DownloadType.AUDIO and not download_type & DownloadType.VIDEO

    # 先判断更具体的类型：音频、课程、剧集条目也可能同时带着其他通用位
    if audio_only or attribute & Attribute.AUDIO_BIT:
        return "AUDIO"
    elif attribute & (Attribute.CHEESE_BIT | Attribute.LESSON_BIT):
        return "COURSE"
    elif attribute & Attribute.BANGUMI_BIT:
        return "BANGUMI"
    elif attribute & Attribute.INTERACTIVE_BIT:
        return "INTERACTIVE"
    elif attribute & Attribute.VIDEO_BIT:
        return "VIDEO"

    return ""

def get_media_type_key(task_info):
    return media_type_key(task_info.Episode.attribute, task_info.Download.type)

def split_keywords(text: str):
    # 多个关键词按空格分开、同时命中才算匹配：「UP主名 合集名」这种组合用起来最顺手
    return text.strip().casefold().split()

def _join_searchable(values):
    return " ".join(value if isinstance(value, str) else "" for value in values).casefold()

def get_searchable_text(task_info):
    return _join_searchable(getter(task_info) for _, getter in SEARCH_FIELDS)

def matches_keywords(searchable_text: str, keywords):
    return all(keyword in searchable_text for keyword in keywords)

@lru_cache(maxsize = 16)
def _parse_sql_filter(keywords: str, media_types: str):
    # 同一次查询里每一行传进来的筛选条件都一样，解析结果缓存起来，不必逐行重新切分
    return keywords.split(), frozenset(media_types.split(",")) if media_types else None

def sql_task_matches(values_json: str, keywords: str, media_types: str):
    """
    注册为 SQLite 函数的筛选判定，在数据库里逐行调用

    values_json 是 json_extract 按 SQL_MATCH_PATHS 取出的数组；keywords 为空格连接的关键词，
    media_types 为逗号连接的媒体类型，空串表示不按该项筛选
    """
    keyword_list, media_type_set = _parse_sql_filter(keywords, media_types)

    *texts, attribute, download_type = loads(values_json)

    if media_type_set and media_type_key(attribute, download_type) not in media_type_set:
        return 0

    if keyword_list and not matches_keywords(_join_searchable(texts), keyword_list):
        return 0

    return 1
