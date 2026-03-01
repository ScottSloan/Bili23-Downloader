from util.common.enum import MediaType

class PreviewerInfo:
    info_data = {}
    media_type = MediaType.UNKNOWN
    attribute = 0

    error_occurred = True
    error_message = ""

    video_quality_choice_data = {}
    audio_quality_choice_data = {}
    video_codec_choice_data = {}

    cache = {
        "video": {},
        "audio": {}
    }
    