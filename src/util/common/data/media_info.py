video_quality_map = {
    "auto": 200,                  # 按优先级自动选择
    "8K": 127,                    # 8K 超高清  
    "DOLBY_VISION": 126,          # 杜比视界
    "HDR": 125,                   # HDR 真彩
    "4K": 120,                    # 4K 超高清
    "1080P60": 116,               # 1080P 60帧
    "1080P+": 112,                # 1080P 高码率
    "AI": 100,                    # 智能修复
    "1080P": 80,                  # 1080P 高清
    "720P": 64,                   # 720P 准高清
    "480P": 32,                   # 480P 标清
    "360P": 16,                   # 360P 流畅
}

reversed_video_quality_map = {v: k for k, v in video_quality_map.items()}

audio_quality_map = {
    "auto": 30300,                # 按优先级自动选择
    "HI_RES": 30251,              # Hi-Res 无损
    "DOLBY_ATMOS": 30250,         # 杜比全景声
    "192K": 30280,                # 192 kbps
    "132K": 30232,                # 132 kbps
    "64K": 30216                  # 64 kbps
}

reversed_audio_quality_map = {v: k for k, v in audio_quality_map.items()}

audio_reorder_map = {
    30251: 0,
    30250: 1,
    30280: 2,
    30232: 3,
    30216: 4
}

audio_codec_map = {
    "AAC LC": "mp4a.40.2",
    "FLAC": "fLaC"
}

reversed_audio_codec_map = {v: k for k, v in audio_codec_map.items()}

video_codec_map = {
    "auto": 20,
    "AVC/H.264": 7,
    "HEVC/H.265": 12,
    "AV1": 13
}

video_codec_str_map = {
    7: "AVC",
    12: "HEVC",
    13: "AV1"
}

reversed_video_codec_map = {v: k for k, v in video_codec_map.items()}
