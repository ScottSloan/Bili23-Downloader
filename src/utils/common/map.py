from typing import Any
from datetime import datetime

bangumi_type_map = {
    1: "番剧",
    2: "电影",
    3: "纪录片",
    4: "国创",
    5: "电视剧",
    7: "综艺"
}

video_quality_map = {
    "自动": 200,
    "超高清 8K": 127,
    "杜比视界": 126,
    "真彩 HDR": 125,
    "超清 4K": 120,
    "高清 1080P60": 116,
    "高清 1080P+": 112,
    "智能修复": 100,
    "高清 1080P": 80,
    "高清 720P": 64,
    "清晰 480P": 32,
    "流畅 360P": 16,
}

audio_quality_map = {
    "自动": 30300,
    "Hi-Res 无损": 30251,
    "杜比全景声": 30250,
    "192K": 30280,
    "132K": 30232,
    "64K": 30216
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
    "AVC/H.264": 7,
    "HEVC/H.265": 12,
    "AV1": 13
}

video_codec_preference_map = {
    "AVC/H.264 优先": 7,
    "HEVC/H.265 优先": 12,
    "AV1 优先": 13
}

video_codec_short_map = {
    "H264": 7,
    "H265": 12,
    "AV1": 13
}

live_quality_map = {
    "自动": 40000,
    "杜比": 30000,
    "4K": 20000,
    "原画": 10000,
    "蓝光": 400,
    "高清": 150,
    "流畅": 80
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
    611: "下载时出现问题",
    612: "下载失败达到最大重试次数",
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
    "download_cover_file": "封面"
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
    "总是询问": 2
}

scope_map = {
    "所有类型": 0,
    "投稿视频": 1,
    "剧集": 2,
    "课程": 3,
    "默认": 4
}

field_map = {
    "datetime": {
        "name": "{time:%H-%M-%S}",
        "description": "当前时间（%H-%M-%S）",
        "example": "{time:%H-%M-%S}".format(time = datetime.now()),
        "scope": [0, 1, 2, 3, 4]
    },
    "timestamp": {
        "name": "{timestamp}",
        "description": "当前时间戳",
        "example": str(int(datetime.now().timestamp())),
        "scope": [0, 1, 2, 3, 4]
    },
    "pubdatetime": {
        "name": "{pubtime:%Y-%m-%d}",
        "description": "视频发布时间（%Y-%m-%d）",
        "example": "{pubtime:%Y-%m-%d}".format(pubtime = datetime.fromtimestamp(1667061000)),
        "scope": [0, 1, 2, 3, 4]
    },
    "pubtimestamp": {
        "name": "{pubtimestamp}",
        "description": "视频发布时间戳",
        "example": "1667061000",
        "scope": [0, 1, 2, 3, 4]
    },
    "number": {
        "name": "{number}",
        "description": "序号",
        "example": "1",
        "scope": [0, 1, 2, 3, 4]
    },
    "zero_padding_number": {
        "name": "{zero_padding_number}",
        "description": "补零序号",
        "example": "01",
        "scope": [0, 1, 2, 3, 4]
    },
    "zone": {
        "name": "{zone}",
        "description": "视频分区",
        "example": "综合",
        "scope": [1]
    },
    "subzone": {
        "name": "{subzone}",
        "description": "视频子分区",
        "example": "动漫剪辑",
        "scope": [1]
    },
    "area": {
        "name": "{area}",
        "description": "地区",
        "example": "日本",
        "scope": [2]
    },
    "title": {
        "name": "{title}",
        "description": "视频标题",
        "example": "第1话 孤独的转机",
        "scope": [0, 1, 2, 3, 4]
    },
    "section_title": {
        "name": "{section_title}",
        "description": "章节标题",
        "example": "正片",
        "scope": [0, 1, 2, 3, 4]
    },
    "part_title": {
        "name": "{part_title}",
        "description": "分节标题",
        "example": "分节（请参考说明文档）",
        "scope": [1]
    },
    "list_title": {
        "name": "{list_title}",
        "description": "合集标题",
        "example": "合集（请参考说明文档）",
        "scope": [1],
    },
    "series_title": {
        "name": "{series_title}",
        "description": "剧集名称或课程名称",
        "example": "孤独摇滚！",
        "scope": [2, 3]
    },
    "aid": {
        "name": "{aid}",
        "description": "视频 av 号",
        "example": "944573356",
        "scope": [0, 1, 2, 3, 4]
    },
    "bvid": {
        "name": "{bvid}",
        "description": "视频 BV 号",
        "example": "BV1yW4y1j7Ft",
        "scope": [0, 1, 2, 3, 4]
    },
    "cid": {
        "name": "{cid}",
        "description": "视频 cid",
        "example": "875212290",
        "scope": [0, 1, 2, 3, 4]
    },
    "ep_id": {
        "name": "{ep_id}",
        "description": "视频 ep_id",
        "example": "693247",
        "scope": [2, 3],
    },
    "season_id": {
        "name": "{season_id}",
        "description": "视频 season_id",
        "example": "43164",
        "scope": [2, 3]
    },
    "media_id": {
        "name": "{media_id}",
        "description": "视频 media_id",
        "example": "28339735",
        "scope": [2]
    },
    "video_quality": {
        "name": "{video_quality}",
        "description": "视频清晰度",
        "example": "超清 4K",
        "scope": [0, 1, 2, 3, 4]
    },
    "audio_quality": {
        "name": "{audio_quality}",
        "description": "音质",
        "example": "Hi-Res 无损",
        "scope": [0, 1, 2, 3, 4]
    },
    "video_codec": {
        "name": "{video_codec}",
        "description": "视频编码",
        "example": "H265",
        "scope": [0, 1, 2, 3, 4]
    },
    "duration": {
        "name": "{duration}",
        "description": "视频时长，单位为秒",
        "example": "256",
        "scope": [0, 1, 2, 3, 4]
    },
    "up_name": {
        "name": "{up_name}",
        "description": "UP 主名称",
        "example": "哔哩哔哩番剧",
        "scope": [0, 1, 2, 3, 4]
    },
    "up_mid": {
        "name": "{up_mid}",
        "description": "UP 主 mid",
        "example": "928123",
        "scope": [0, 1, 2, 3, 4]
    }
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

ffmpeg_video_gpu_windows_map = {
    "关闭": 0,
    "NVIDIA": 1,
    "AMD": 2,
    "Intel": 3,
}

ffmpeg_video_gpu_linux_map = {
    "关闭": 0,
    "VAAPI": 1,
}

ffmpeg_video_gpu_darwin_map = {
    "关闭": 0,
    "Apple": 1,
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
    "cinephile": 1001,
    "ent": 1002,
    "music": 1003,
    "dance": 1004,
    "douga": 1005,
    "kichiku": 1007,
    "game": 1008,
    "knowledge": 1010,
    "tech": 1012,
    "car": 1013,
    "fasion": 1014,
    "sports": 1018,
    "food": 1020,
    "animal": 1024
}

def get_mapping_key_by_value(mapping: dict, value: int, default = None):
    mapping_reversed = dict(map(reversed, mapping.items()))

    return mapping_reversed.get(value, default)

def get_mapping_index_by_value(mapping: dict, value: Any):
    return list(mapping.values()).index(value)

def get_mapping_index_by_key(mapping: dict, key: Any):
    return list(mapping.keys()).index(key)