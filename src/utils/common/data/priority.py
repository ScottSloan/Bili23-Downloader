import gettext

_ = gettext.gettext

video_quality_priority = {
    _("8K 超高清"): 127,
    _("杜比视界"): 126,
    _("HDR 真彩"): 125,
    _("4K 超高清"): 120,
    _("1080P 60帧"): 116,
    _("1080P 高码率"): 112,
    _("智能修复"): 100,
    _("1080P 高清"): 80,
    _("720P 准高清"): 64,
    _("480P 标清"): 32,
    _("360P 流畅"): 16
}

video_quality_priority_short = {
    127: "8K",
    126: "DV",
    125: "HDR",
    120: "4K",
    116: "1080P60",
    112: "1080P+",
    100: "AI",
    80: "1080P",
    64: "720P",
    32: "480P",
    16: "360P"
}

audio_quality_priority = {
    _("Hi-Res 无损"): 30251,
    _("杜比全景声"): 30250,
    "192K": 30280,
    "132K": 30232,
    "64K": 30216
}

audio_quality_priority_short = {
    30251: "Hi-Res",
    30250: "DA",
    30280: "192K",
    30232: "132K",
    30216: "64K"
}

video_codec_priority = {
    "AV1": 13,
    "AVC/H.264": 7,
    "HEVC/H.265": 12
}

video_codec_priority_short = {
    13: "AV1",
    7: "AVC",
    12: "HEVC"
}