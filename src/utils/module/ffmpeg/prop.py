from utils.common.formatter.file_name_v2 import FileNameFormatter

from utils.common.model.task_info import DownloadTaskInfo

class FFProp:
    def __init__(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

    def dash_video_temp_file(self):
        return f"video_{self.task_info.id}.{self.task_info.video_type}"

    def dash_audio_temp_file(self):
        return f"audio_{self.task_info.id}.{self.task_info.audio_type}"

    def dash_output_temp_file(self):
        return f"output_{self.task_info.id}.{self.task_info.output_type}"
    
    def output_file_name(self):
        return FileNameFormatter.check_file_name_length(f"{self.task_info.file_name}.{self.task_info.output_type}")
