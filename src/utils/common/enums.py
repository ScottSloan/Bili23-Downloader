from enum import Enum

class ParseType(Enum):
    Video = 1             # 投稿视频
    Bangumi = 2           # 番组
    Live = 3              # 直播
    Cheese = 4            # 课程

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
    In_Section = 2        # 获取视频所在的合集
    All = 3               # 获取全部相关视频

class LiveStatus(Enum):
    Not_Started = 0       # 未开播
    Live = 1              # 直播中
    Replay = 2            # 轮播中

class ProxyMode(Enum):
    Disable = 0           # 不使用
    Follow = 1            # 跟随系统
    Custom = 2            # 手动设置

class DanmakuType(Enum):
    XML = 0               # XML 格式
    Protobuf = 1          # Protobuf 格式

class SubtitleType(Enum):
    SRT = 0               # SRT 格式
    TXT = 1               # TXT 格式
    JSON = 2              # JSON 格式

class PlayerMode(Enum):
    Default = 0           # 系统默认
    Custom = 1            # 自定义

class CDNMode(Enum):
    Auto = 0              # 自动切换
    Custom = 1            # 手动设置

class DownloadStatus(Enum):
    Waiting = 0           # 等待下载
    Downloading = 1       # 下载中
    Pause = 2             # 暂停中
    Merging = 3           # 合成中
    Complete = 4          # 下载完成
    Download_Failed = 5   # 下载失败
    Merge_Failed = 6      # 合成失败

    Alive = [Waiting, Downloading, Pause]
    Alive_Ex = [Waiting, Downloading, Pause, Merge_Failed, Download_Failed]

class StatusCode(Enum):
    Success = 0              # 请求成功
    Vip = 600                # 会员认证
    Pay = 601                # 付费购买
    URL = 602                # 无效链接
    Redirect = 603           # 跳转链接
    Area_Limit = -10403      # 区域限制