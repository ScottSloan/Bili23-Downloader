from enum import Enum

class ParseType(Enum):
    Video = 1             # 投稿视频
    Bangumi = 2           # 番组
    Live = 3              # 直播

class VideoType(Enum):
    Single = 1            # 单个视频
    Part = 2              # 分 P 视频
    Collection = 3        # 合集

class MergeType(Enum):
    Video_And_Audio = 0   # 合成视频和音频
    Only_Video = 1        # 只下载视频
    Only_Audio = 2        # 只下载音频
    No_Merge = 3          # 不进行合成操作

class EpisodeDisplayType(Enum):
    Single = 1            # 获取单个视频
    In_Section = 2         # 获取视频所在的合集
    All = 3               # 获取全部相关视频

class LiveStatus(Enum):
    Not_Started = 1        # 未开播
    Live = 2              # 直播中
    Replay = 3            # 轮播中