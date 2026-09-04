from ...common.enum import MediaType

class PreviewerInfo:
    info_data = {}
    media_type = MediaType.UNKNOWN
    attribute = 0

    # 当前媒体信息取自哪个视频。首选项是充电专属、付费等无权限的视频时会自动换用备选，
    # 此时下载选项中显示的清晰度、编码其实来自另一个视频，需要让用户知情
    episode_title = ""
    episode_number = ""
    from_fallback = False

    # 当前预览的稿件标识，按需补取缺失画质的视频流时要用来重新请求 playurl
    bvid = ""
    cid = 0

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
    