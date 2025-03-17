from typing import Any

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

video_codec_map = {
    "AVC/H.264": 7,
    "HEVC/H.265": 12,
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

supported_gpu_map = {
    "NVIDIA": 1,
    "AMD": 2,
    "Intel": 3
}

video_sw_encoder_map = {
    0: "libx264",
    1: "libx265",
    2: "libaom-av1"
}

video_hw_encoder_map = {
    0: {
        0: "h264_nvenc",
        1: "hevc_nvenc",
        2: "av1_nvenc"
    },
    1: {
        0: "h264_amf",
        1: "hevc_amf",
        2: "av1_amf"
    },
    2: {
        0: "h264_qsv",
        1: "hevc_qsv",
        2: "av1_qsv"
    }
}

danmaku_format_map = {
    "xml": 0,
    "protobuf": 1
}

subtitle_format_map = {
    "srt": 0,
    "txt": 1,
    "lrc": 2,
    "json": 3
}

download_status_map = {
    0: "等待下载",
    1: "正在获取下载信息...",
    2: "暂停中",
    3: "正在合成视频",
    4: "下载完成",
    5: "下载失败",
    6: "视频合成失败"
}

cdn_map = {
    0: {
        "cdn": "upos-sz-mirror08c.bilivideo.com",
        "provider": "华为云",
        "order": 1
    },
    1: {
        "cdn": "upos-sz-mirrorhw.bilivideo.com",
        "provider": "华为云",
        "order": 4
    },
    2: {
        "cdn": "upos-sz-mirror08h.bilivideo.com",
        "provider": "华为云",
        "order": 5
    },
    3: {
        "cdn": "upos-sz-mirrorcoso1.bilivideo.com",
        "provider": "腾讯云",
        "order": 2
    },
    4: {
        "cdn": "upos-sz-mirrorcos.bilivideo.com",
        "provider": "腾讯云",
        "order": 6
    },
    5: {
        "cdn": "upos-sz-mirrorcosb.bilivideo.com",
        "provider": "腾讯云",
        "order": 7
    },
    6: {
        "cdn": "upos-sz-mirrorali.bilivideo.com",
        "provider": "阿里云",
        "order": 3
    },
    7: {
        "cdn": "upos-sz-mirrorali02.bilivideo.com",
        "provider": "阿里云",
        "order": 8
    },
    8: {
        "cdn": "upos-sz-mirroralib.bilivideo.com",
        "provider": "阿里云",
        "order": 9
    },
    9: {
        "cdn": "upos-sz-mirroraliov.bilivideo.com",
        "provider": "阿里云（海外）",
        "order": 10
    },
    10: {
        "cdn": "upos-sz-mirrorcosov.bilivideo.com",
        "provider": "腾讯云（海外）",
        "order": 11
    },
    11: {
        "cdn": "upos-hz-mirrorakam.akamaized.net",
        "provider": "Akamai（海外）",
        "order": 12
    },
    12: {
        "cdn": "upos-sz-mirrorcf1ov.bilivideo.com",
        "provider": "Cloudflare（海外）",
        "order": 13
    },
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
    -10403: "根据版权方要求，您所在的地区无法观看本片",
    600: "大会员专享限制",
    601: "应版权方要求本片需购买",
    602: "无效的链接",
    603: "跳转链接",
    610: "调用 FFmpeg 时出错",
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

def get_mapping_key_by_value(mapping: dict, value: int, default = None):
    mapping_reversed = dict(map(reversed, mapping.items()))

    return mapping_reversed.get(value, default)

def get_mapping_index_by_value(mapping: dict, value: Any):
    return list(mapping.values()).index(value)

def get_mapping_index_by_key(mapping: dict, key: Any):
    return list(mapping.keys()).index(key)