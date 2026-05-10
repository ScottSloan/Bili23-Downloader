from util.common.enum import MediaType
from util.common.data import video_quality_map, audio_quality_map, video_codec_map

class PreviewerInfo:
    error_occurred = False
    error_message = ""
    
    media_type = MediaType.UNKNOWN
    
    video_quality_choice_data = video_quality_map.copy()
    audio_quality_choice_data = audio_quality_map.copy()
    video_codec_choice_data = video_codec_map.copy()
    
    attribute = 0

class Previewer:
    def __init__(self):
        pass
