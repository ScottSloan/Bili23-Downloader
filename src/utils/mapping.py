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

supported_gpu_mapping = {
    "NVIDIA": 1,
    "AMD": 2,
    "Intel": 3
}