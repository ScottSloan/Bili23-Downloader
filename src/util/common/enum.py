from PySide6.QtCore import QLocale

from enum import Enum, IntEnum, IntFlag

class ToastNotificationCategory(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class QRCodeScanStatus(IntEnum):
    WAITING_FOR_SCAN = 86101             # 等待扫码
    WAITING_FOR_CONFIRMATION = 86090     # 等待确认
    SUCCESS = 0                          # 登录成功
    EXPIRED = 86038                      # 二维码过期

class Scaling(Enum):
    SCALE_100 = "1"
    SCALE_125 = "1.25"
    SCALE_150 = "1.5"
    SCALE_175 = "1.75"
    SCALE_200 = "2"
    AUTO = "Auto"

class Language(Enum):
    CHINESE_SIMPLIFIED = QLocale("zh_CN")
    CHINESE_TRADITIONAL = QLocale("zh_TW")
    ENGLISH = QLocale("en_US")

    AUTO = QLocale()

class WhenClose(Enum):
    EXIT = 1
    MINIMIZE = 2
    ALWAYS_ASK = 3

class FileConflictResolution(Enum):
    AUTO_RENAME = 1
    OVERWRITE = 2

class DanmakuType(Enum):
    XML = "xml"
    ASS = "ass"
    JSON = "json"

class SubtitleType(Enum):
    SRT = "srt"
    LRC = "lrc"
    TXT = "txt"
    ASS = "ass"
    JSON = "json"

class CoverType(Enum):
    JPG = "jpg"
    PNG = "png"
    AVIF = "avif"
    WEBP = "webp"

class MetadataType(Enum):
    NFO = "nfo"
    JSON = "json"

class ProxyType(Enum):
    HTTP = "http"
    # SOCKS4 = "socks4"
    # SOCKS5 = "socks5"

class FFmpegSource(Enum):
    BUNDLED = "bundled"
    SYSTEM = "system"
    CUSTOM = "custom"

class NumberingType(Enum):
    FROM_SPECIFIED = 0
    CONTINUOUS = 1

class Channel(IntEnum):
    UNKNOWN = 0
    PORTABLE = 1
    INSTALLER = 2
    PACKAGE = 3

class ConventionType(IntEnum):
    NORMAL = 11
    PART = 12
    COLLECTION = 13
    BANGUMI = 20
    CHEESE = 30

class MediaType(IntEnum):
    UNKNOWN = 0
    DASH = 1
    MP4 = 2
    FLV = 3

class DownloadStatus(IntEnum):
    QUEUED = 0                      # 排队中
    PARSING = 1                     # 解析中
    DOWNLOADING = 2                 # 下载中
    PAUSED = 3                      # 已暂停
    COMPLETED = 4                   # 已完成

    FFMPEG_QUEUED = 5               # 等待 FFmpeg 处理中
    MERGING = 6                     # 合并中

    CONVERTING = 7                  # 转换中

    ADDITIONAL_PROCESSING = 8       # 额外处理（如提取封面、生成字幕等）

    FAILED = 100                    # 下载失败
    FFMPEG_FAILED = 101             # FFmpeg 处理失败

    INVALID = 1000                  # 无效状态，在下载未完成时，移动文件导致找不到临时文件

class DownloadType(IntFlag):
    VIDEO            = 1 << 0       # 下载独立视频流
    AUDIO            = 1 << 1       # 下载独立音频流
    DANMAKU          = 1 << 2       # 下载弹幕
    SUBTITLE         = 1 << 3       # 下载字幕
    COVER            = 1 << 4       # 下载封面
    METADATA         = 1 << 5       # 下载元数据

class VideoContainer(Enum):
    MP4 = "mp4"
    MKV = "mkv"
