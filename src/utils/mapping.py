from typing import Dict, Any

bangumi_type_mapping = {
    1: "番剧",
    2: "电影",
    3: "纪录片",
    4: "国创",
    5: "电视剧",
    7: "综艺"
}

video_quality_mapping = {
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

audio_quality_mapping = {
    "自动": 30300,
    "Hi-Res 无损": 30251,
    "杜比全景声": 30250,
    "192K": 30280,
    "132K": 30232,
    "64K": 30216
}

video_codec_mapping = {
    "AVC/H.264": 7,
    "HEVC/H.265": 12,
    "AV1": 13
}

live_quality_mapping = {
    "自动": 40000,
    "杜比": 30000,
    "4K": 20000,
    "原画": 10000,
    "蓝光": 400,
    "高清": 150,
    "流畅": 80
}

live_status_mapping = {
    0: "未开播",
    1: "直播中",
    2: "轮播中"
}

supported_gpu_mapping = {
    "NVIDIA": 1,
    "AMD": 2,
    "Intel": 3
}

video_sw_encoder_mapping = {
    0: "libx264",
    1: "libx265",
    2: "libaom-av1"
}

video_hw_encoder_mapping = {
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

danmaku_format_mapping = {
    "xml": 0,
    "protobuf": 1
}

subtitle_format_mapping = {
    "srt": 0,
    "txt": 1,
    "json": 2
}

download_status_mapping = {
    0: "等待下载",
    1: "正在获取下载信息...",
    2: "暂停中",
    3: "正在合成视频",
    4: "下载完成",
    5: "下载失败",
    6: "视频合成失败"
}

cdn_mapping = {
    0: "upos-sz-mirror08c.bilivideo.com",
    1: "upos-sz-mirrorcoso1.bilivideo.com",
    2: "upos-sz-mirrorhw.bilivideo.com",
    3: "upos-sz-mirrorcos.bilivideo.com",
    4: "upos-sz-mirrorcosb.bilivideo.com",
    5: "upos-sz-mirrorbos.bilivideo.com",
    6: "upos-sz-mirrorhwb.bilivideo.com",
    7: "upos-sz-mirrorali.bilivideo.com"
}

def get_mapping_key_by_value(mapping: Dict, value: int):
    mapping_reversed = dict(map(reversed, mapping.items()))

    return mapping_reversed[value]

def get_mapping_index_by_value(mapping: Dict, value: Any):
    return list(mapping.values()).index(value)

def get_mapping_index_by_key(mapping: Dict, key: Any):
    return list(mapping.keys()).index(key)