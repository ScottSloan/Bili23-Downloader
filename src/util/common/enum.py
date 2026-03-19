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

class Language(Enum):
    CHINESE_SIMPLIFIED = QLocale("zh_CN")
    CHINESE_TRADITIONAL = QLocale("zh_TW")
    ENGLISH = QLocale("en_US")

    AUTO = QLocale()

class WhenClose(Enum):
    EXIT = 1
    MINIMIZE = 2
    ALWAYS_ASK = 3

class DanmakuType(Enum):
    XML = "xml"
    ASS = "ass"
    JSON = "json"

class SubtitleType(Enum):
    SRT = "srt"
    LRC = "lrc"
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
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

class FFmpegSource(Enum):
    BUNDLED = "bundled"
    SYSTEM = "system"
    CUSTOM = "custom"

class NumberingType(Enum):
    FROM_SPECIFIED = 0
    CONTINUOUS = 1
    FROM_EPISODE_LIST = 2

class ZeroPaddingTotalDigits(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

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

class DownloadStatus(IntEnum):
    QUEUED = 0                      # 排队中
    PARSING = 1                     # 解析中
    DOWNLOADING = 2                 # 下载中
    PAUSED = 3                      # 已暂停
    COMPLETED = 4                   # 已完成
    MERGE_QUEUED = 5                # 合并排队中
    MERGING = 6                     # 合并中
    FAILED = 10                     # 下载失败
    MERGE_FAILED = 11               # 合并失败

class DownloadType(IntFlag):
    VIDEO            = 1 << 0       # 下载独立视频流
    AUDIO            = 1 << 1       # 下载独立音频流
    DANMAKU          = 1 << 2       # 下载弹幕
    SUBTITLE         = 1 << 3       # 下载字幕
    COVER            = 1 << 4       # 下载封面
    METADATA         = 1 << 5       # 下载元数据
