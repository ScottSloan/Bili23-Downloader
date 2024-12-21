from enum import Enum

class ParseType(Enum):
    Video = 1            # 投稿视频
    Bangumi = 2          # 番组
    Live = 3             # 直播

class VideoType(Enum):
    Single = 1           # 单个视频
    Part = 2             # 分 P 视频
    Collection = 3       # 合集

class EpisodeDisplayType(Enum):
    Single = 1           # 获取单个视频
    InSection = 2        # 获取视频所在的合集
    All = 3              # 获取全部相关视频

class LiveStatus(Enum):
    NotStarted = 1       # 未开播
    Live = 2             # 直播中
    Replay = 3           # 轮播中