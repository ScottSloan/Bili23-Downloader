from enum import Enum

class ParseType(Enum):
    Video = 1                     # 投稿视频
    Bangumi = 2                   # 番组
    Live = 3                      # 直播
    Cheese = 4                    # 课程
    Extra = 100                   # 弹幕、字幕、封面等类型文件

class VideoType(Enum):
    Single = 1                    # 单个视频
    Part = 2                      # 分 P 视频
    Collection = 3                # 合集

class EpisodeDisplayType(Enum):
    Single = 1                    # 获取单个视频
    In_Section = 2                # 获取视频所在的列表
    All = 3                       # 获取全部相关视频

class LiveStatus(Enum):
    Not_Started = 0               # 未开播
    Live = 1                      # 直播中
    Replay = 2                    # 轮播中

class ProxyMode(Enum):
    Disable = 0                   # 不使用
    Follow = 1                    # 跟随系统
    Custom = 2                    # 手动设置

class DanmakuType(Enum):
    XML = 0                       # XML 格式
    Protobuf = 1                  # Protobuf 格式
    JSON = 2                      # JSON 格式
    ASS = 3                       # ASS 格式

class SubtitleType(Enum):
    SRT = 0                       # SRT 格式
    TXT = 1                       # TXT 格式
    LRC = 2                       # LRC 格式
    JSON = 3                      # JSON 格式
    ASS = 4                       # ASS 格式

class CoverType(Enum):
    JPG = 0                       # jpg 格式
    PNG = 1                       # png 格式
    WEBP = 2                      # Webp 格式
    AVIF = 3                      # avif 格式

class StreamType(Enum):
    Dash = 0                      # dash 流
    Flv = 1                       # flv 流

class DownloadStatus(Enum):
    Waiting = 0                   # 等待下载
    Downloading = 1               # 下载中
    Generating = 10               # 生成中
    Pause = 2                     # 暂停中
    Merging = 3                   # 合成中
    Complete = 4                  # 下载完成
    DownloadError = 5             # 下载失败
    MergeError = 6                # 合成失败
    Invalid = 7                   # 视频失效

    Alive = [Waiting, Downloading, Pause]
    Alive_Ex = [Waiting, Downloading, Pause, MergeError, DownloadError]

class StatusCode(Enum):
    Success = 0                   # 请求成功
    Vip = 600                     # 会员认证
    Pay = 601                     # 付费购买
    URL = 602                     # 无效链接
    Redirect = 603                # 跳转链接
    CallError = 610               # 调用出错
    DownloadError = 611           # 下载失败
    MaxRetry = 612                # 最大重试
    Area_Limit = -10403           # 区域限制

class VideoQualityID(Enum):
    _None = 0                     # 无视频
    _360P = 16                    # 360P
    _480P = 32                    # 480P
    _720P = 64                    # 720P
    _1080P = 80                   # 1080P
    _1080P_P = 112                # 1080P 高码率
    _1080P_60 = 116               # 1080P 60帧
    _4K = 120                     # 4K
    _HDR = 125                    # HDR
    _Dolby_Vision = 126           # 杜比视界
    _8K = 127                     # 8K
    _Auto = 200                   # 自动

class AudioQualityID(Enum):
    _None = 0                     # 无音频
    _64K = 30216                  # 64K
    _132K = 30232                 # 132K
    _192K = 30280                 # 192K
    _Dolby_Atoms = 30250          # 杜比全景声
    _Hi_Res = 30251               # Hi-Res 无损
    _Auto = 30300                 # 自动

class VideoCodecID(Enum):
    AVC = 7                       # H264
    HEVC = 12                     # H265
    AV1 = 13                      # AV1

class OverrideOption(Enum):
    Override = 0                  # 覆盖文件
    Rename = 1                    # 重命名

class Platform(Enum):
    Windows = "windows"           # Windows
    Linux = "linux"               # Linux
    macOS = "darwin"              # macOS

class ParseStatus(Enum):
    Finish = 0                    # 解析完成
    Parsing = 1                   # 解析中
    Error = 2                     # 解析失败

class LiveQualityID(Enum):
    _Auto = 40000                 # 自动
    _Dolby_Vision = 30000         # 杜比视界
    _4K = 20000                   # 4K
    _1080P = 10000                # 1080P
    _blue_ray = 400               # 蓝光
    _hd = 150                     # HD
    _sd = 80                      # SD

class NumberType(Enum):
    From_1 = 0                    # 从 1 开始
    Coherent = 1                  # 连续序号
    Episode_List = 2              # 剧集列表序号

class ProcessingType(Enum):
    Normal = 1                    # 正常
    Parse = 2                     # 解析
    Interact = 3                  # 解析互动视频

class ExitOption(Enum):
    TaskIcon = 0                  # 托盘图标
    Exit = 1                      # 直接退出

class SubtitleLanOption(Enum):
    All_Subtitles_With_AI = 0     # 下载全部字幕 + AI 字幕
    All_Subtitles = 1             # 下载全部字幕
    Custom = 2                    # 自定义

class ScopeID(Enum):
    All = 0                       # 所有类型
    Video = 1                     # 投稿视频
    Bangumi = 2                   # 剧集
    Cheese = 3                    # 课程
    Default = 4                   # 默认