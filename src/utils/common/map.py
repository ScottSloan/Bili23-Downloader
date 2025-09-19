bangumi_type_map = {
    1: "番剧",
    2: "电影",
    3: "纪录片",
    4: "国创",
    5: "电视剧",
    7: "综艺"
}

video_quality_map = {
    200: "自动",
    127: "超高清 8K",
    126: "杜比视界",
    125: "HDR 真彩",
    120: "4K 超高清",
    116: "1080P 60帧",
    112: "1080P 高码率",
    100: "智能修复",
    80: "1080P 高清",
    64: "720P 准高清",
    32: "480P 标清",
    16: "360P 流畅",
}

audio_quality_map = {
    30300: "自动",
    30251: "Hi-Res 无损",
    30250: "杜比全景声",
    30280: "192K",
    30232: "132K",
    30216: "64K"
}

audio_quality_sort_map = {
    30300: 1,
    30251: 2,
    30250: 3,
    30280: 4,
    30232: 5,
    30216: 6
}

audio_file_type_map = {
    30251: "flac",
    30250: "ec3",
    30280: "m4a",
    30232: "m4a",
    30216: "m4a"
}

video_codec_map = {
    20: "自动",
    7: "AVC/H.264",
    12: "HEVC/H.265",
    13: "AV1"
}

video_codec_short_map = {
    7: "H264",
    12: "H265",
    13: "AV1"
}

live_status_map = {
    0: "未开播",
    1: "直播中",
    2: "轮播中"
}

danmaku_format_map = {
    "xml": 0,
    "protobuf": 1,
    "json": 2,
    "ass": 3
}

subtitle_format_map = {
    "srt": 0,
    "txt": 1,
    "lrc": 2,
    "json": 3,
    "ass": 4
}

cover_format_map = {
    "jpg": 0,
    "png": 1,
    "webp": 2,
    "avif": 3
}

metadata_format_map = {
    "nfo": 0,
    "json": 1,
}

cheese_status_map = {
    1: "全集试看",
    2: "付费",
    3: "部分试看"
}

status_code_map = {
    0: "请求成功",
    1: "未找到该房间",
    -400: "请求错误",
    -403: "权限不足",
    -404: "视频不存在",
    -509: "请求过于频繁，请稍后再试",
    -10403: "根据版权方要求，您所在的地区无法观看本片",
    600: "大会员专享限制",
    601: "应版权方要求本片需购买",
    602: "无效的链接",
    603: "跳转链接",
    610: "执行外部命令失败",
    611: "下载失败",
    612: "下载失败达到最大重试次数",
    613: "用户终止解析操作",
    614: "该内容采用 WideVine DRM 技术加密，不支持下载",
    62002: "稿件不可见",
    62004: "稿件审核中",
    62012: "仅 UP 主自己可见",
    19002003: "房间信息不存在"
}

override_option_map = {
    "覆盖原文件": 0,
    "重命名文件": 1
}

extra_map = {
    "download_danmaku_file": "弹幕",
    "download_subtitle_file": "字幕",
    "download_cover_file": "封面",
    "download_metadata_file": "元数据"
}

download_type_map = {
    1: "投稿视频",
    2: "剧集",
    3: "直播",
    4: "课程",
    5: "弹幕、字幕或封面"
}

number_type_map = {
    "总是从 1 开始": 0,
    "连贯递增": 1,
    "使用剧集列表序号": 2
}

exit_option_map = {
    "隐藏到托盘": 0,
    "直接退出": 1,
    "总是询问": 2,
    "首次询问": 3
}

time_ratio_map = {
    "0.1s": 0,
    "0.5s": 1,
    "1s": 2
}

ffmpeg_video_codec_map = {
    "AVC/H.264": {
        "windows": {
            "关闭": "libx264",
            "NVIDIA": "h264_nvenc",
            "AMD": "h264_amf",
            "Intel": "h264_qsv"
        },
        "linux": {
            "关闭": "libx264",
            "VAAPI": "h264_vaapi"
        },
        "darwin": {
            "关闭": "libx264",
            "Apple": "h264_videotoolbox"
        }
    },
    "HEVC/H.265": {
        "windows": {
            "关闭": "libx265",
            "NVIDIA": "hevc_nvenc",
            "AMD": "hevc_amf",
            "Intel": "hevc_qsv"
        },
        "linux": {
            "关闭": "libx265",
            "VAAPI": "hevc_vaapi",
        },
        "darwin": {
            "关闭": "libx265",
            "Apple": "hevc_videotoolbox"
        }
    },
    "AV1": {
        "windows": {
            "关闭": "libaom-av1",
            "NVIDIA": "av1_nvenc",
            "AMD": "av1_amf",
            "Intel": "av1_qsv"
        },
        "linux": {
            "关闭": "libaom-av1",
            "VAAPI": "av1_vaapi"
        },
        "darwin": {
            "关闭": "libaom-av1",
            "Apple": None,
        }
    },
    "Copy": "copy"
}

ffmpeg_video_crf_map = {
    "关闭": None,
    "10（高质量）": 10,
    "12": 12,
    "14": 14,
    "16": 16,
    "18（推荐）": 18,
    "20": 20,
    "22": 22,
    "24": 24,
    "26": 26,
    "28（低质量）": 28,
}

ffmpeg_video_gpu_map = {
    "windows": {
        "关闭": 0,
        "NVIDIA": 1,
        "AMD": 2,
        "Intel": 3,
    },
    "linux": {
        "关闭": 0,
        "VAAPI": 1,
    },
    "darwin": {
        "关闭": 0,
        "Apple": 1,
    }
}

ffmpeg_audio_codec_map = {
    "AAC": "aac",
    "MP3": "libmp3lame",
    "AC3": "ac3_fixed",
    "Copy": "copy"
}

ffmpeg_audio_samplerate_map = {
    "22050 Hz": 22050,
    "24000 Hz": 24000,
    "44100 Hz": 44100,
    "48000 Hz": 48000
}

ffmpeg_audio_channel_map = {
    "1 (Mono)": 1,
    "2 (Stereo)": 2,
    "6 (5.1)": 6,
    "8 (7.1)": 8
}

webpage_option_map = {
    "自动选择": 0,
    "使用系统 Webview 组件": 1,
    "使用系统默认浏览器": 2
}

rid_map = {
    "all": {
        "rid": 0,
        "desc": "全部"
    },
    "cinephile": {
        "rid": 1001,
        "desc": "影视"
    },
    "ent": {
        "rid": 1002,
        "desc": "娱乐"
    },
    "music": {
        "rid": 1003,
        "desc": "音乐"
    },
    "dance": {
        "rid": 1004,
        "desc": "舞蹈"
    },
    "douga": {
        "rid": 1005,
        "desc": "动画"
    },
    "kichiku": {
        "rid": 1007,
        "desc": "鬼畜"
    },
    "game": {
        "rid": 1008,
        "desc": "游戏"
    },
    "knowledge": {
        "rid": 1010,
        "desc": "知识"
    },
    "tech": {
        "rid": 1012,
        "desc": "科技数码"
    },
    "car": {
        "rid": 1013,
        "desc": "汽车"
    },
    "fasion": {
        "rid": 1014,
        "desc": "时尚美妆"
    },
    "sports": {
        "rid": 1018,
        "desc": "体育运动"
    },
    "food": {
        "rid": 1020,
        "desc": "美食"
    },
    "animal": {
        "rid": 1024,
        "desc": "动物"
    }
}

url_pattern_map = [
    ("video", r"bilibili\.com/video/([a-zA-Z0-9]+)"),
    ("bangumi", r"bilibili\.com/bangumi/(play|media)/(ss\d+|ep\d+|md\d+)"),
    ("cheese", r"bilibili\.com/cheese/play/(ss\d+|ep\d+)"),
    ("live", r"live\.bilibili\.com/(\d+)"),
    ("space_list", r"space\.bilibili\.com/(\d+)/lists"),
    ("favlist", r"space\.bilibili\.com/(\d+)/favlist"),
    ("favlist", r"www.bilibili\.com/list/ml(\d+)"),
    ("space", r"space\.bilibili\.com/(\d+)"),
    ("space", r"www\.bilibili\.com/medialist/play/(\d+)"),
    ("space_list", r"bilibili\.com/list/(\d+)"),
    ("popular", r"bilibili\.com/v/popular"),
    ("b23", r"(b23\.tv|bili2233\.cn)"),
    ("festival", r"bilibili\.com/festival"),
    ("video", r"(BV[a-zA-Z0-9]+|av[0-9]+)"),
    ("bangumi", r"(ep[0-9]+|ss[0-9]+)|md[0-9]+")
]

cn_num_map = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "零": 0,
    "百": 100
}

language_map = {
    "English": "en_US",
    "简体中文": "zh_CN",
}

nfo_type_map = {
    "Kodi": 0,
    "Emby": 1,
    "Jellyfin": 2,
    "Plex": 3
}

def get_mapping_key_by_value(mapping: dict, value: int, default = None):
    mapping_reversed = dict(map(reversed, mapping.items()))

    return mapping_reversed.get(value, default)