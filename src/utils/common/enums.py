from enum import Enum

class ParseType(Enum):
    Video = 1                # 投稿视频
    Bangumi = 2              # 番组
    Live = 3                 # 直播
    Cheese = 4               # 课程
    Danmaku = 20             # 弹幕
    Subtitle = 21            # 字幕
    Cover = 22               # 封面

class VideoType(Enum):
    Single = 1               # 单个视频
    Part = 2                 # 分 P 视频
    Collection = 3           # 合集

class EpisodeDisplayType(Enum):
    Single = 1               # 获取单个视频
    In_Section = 2           # 获取视频所在的列表
    All = 3                  # 获取全部相关视频

class LiveStatus(Enum):
    Not_Started = 0          # 未开播
    Live = 1                 # 直播中
    Replay = 2               # 轮播中

class ProxyMode(Enum):
    Disable = 0              # 不使用
    Follow = 1               # 跟随系统
    Custom = 2               # 手动设置

class DanmakuType(Enum):
    XML = 0                  # XML 格式
    Protobuf = 1             # Protobuf 格式

class SubtitleType(Enum):
    SRT = 0                  # SRT 格式
    TXT = 1                  # TXT 格式
    LRC = 2                  # LRC 格式
    JSON = 3                 # JSON 格式

class PlayerMode(Enum):
    Default = 0              # 系统默认
    Custom = 1               # 自定义

class CDNMode(Enum):
    Auto = 0                 # 自动切换
    Custom = 1               # 手动设置

class StreamType(Enum):
    Dash = 0                 # dash 流
    Flv = 1                  # flv 流

class DownloadStatus(Enum):
    Waiting = 0              # 等待下载
    Downloading = 1          # 下载中
    Pause = 2                # 暂停中
    Merging = 3              # 合成中
    Complete = 4             # 下载完成
    DownloadError = 5        # 下载失败
    MergeError = 6           # 合成失败

    Alive = [Waiting, Downloading, Pause]
    Alive_Ex = [Waiting, Downloading, Pause, MergeError, DownloadError]

class StatusCode(Enum):
    Success = 0              # 请求成功
    Vip = 600                # 会员认证
    Pay = 601                # 付费购买
    URL = 602                # 无效链接
    Redirect = 603           # 跳转链接
    FFmpegCall = 610         # 调用出错
    Download = 611           # 下载失败
    MaxRety = 612            # 最大重试
    Area_Limit = -10403      # 区域限制

class VideoQualityID(Enum):
    _360P = 16
    _480P = 32
    _720P = 64
    _1080P = 80
    _1080P_P = 112
    _1080P_60 = 116
    _4K = 120
    _HDR = 125
    _Dolby_Vision = 126
    _8K = 127
    _Auto = 200

class AudioQualityID(Enum):
    _None = 0
    _64K = 30216
    _132K = 30232
    _192K = 30280
    _Dolby_Atoms = 30250
    _Hi_Res = 30251
    _Auto = 30300

class VideoCodecID(Enum):
    AVC = 7
    HEVC = 12
    AV1 = 13

class DownloadOption(Enum):
    OnlyVideo = 1
    OnlyAudio = 2
    VideoAndAudio = 3
    FLV = 4
    NONE = 5

class OverrideOption(Enum):
    Override = 1
    Rename = 2