from ...common.enum import MediaType

class PreviewerInfo:
    info_data = {}
    media_type = MediaType.UNKNOWN
    attribute = 0

    # 预览请求的代号，每次切换剧集时递增。异步请求带着发起时的代号回来，
    # 与当前值不一致说明用户已经切到了别的剧集，结果必须丢弃，
    # 否则先发后到的旧响应会把上一个剧集的媒体信息写进当前预览
    generation = 0

    error_occurred = True
    error_message = ""

    video_quality_choice_data = {}
    audio_quality_choice_data = {}
    video_codec_choice_data = {}

    cache = {
        "video": {},
        "audio": {}
    }
    