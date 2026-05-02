from util.common.enum import MediaType

class PreviewerInfo:
    error_occurred = False
    error_message = ""
    
    media_type = MediaType.UNKNOWN
    
    video_quality_choice_data = {}
    audio_quality_choice_data = {}
    video_codec_choice_data = {}
    
    attribute = 0

class Previewer:
    def __init__(self):
        pass
