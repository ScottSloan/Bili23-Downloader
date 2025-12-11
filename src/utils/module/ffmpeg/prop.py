import os

from utils.common.formatter.file_name_v2 import FileNameFormatter

from utils.common.model.task_info import DownloadTaskInfo

class FFProp:
    def __init__(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

    def video_temp_file(self):
        return f"video_{self.task_info.id}.{self.task_info.video_type}"
    
    def flv_temp_file(self):
        return f"flv_{self.task_info.id}.flv"

    def audio_temp_file(self):
        return f"audio_{self.task_info.id}.{self.task_info.audio_type}"

    def output_temp_file(self, file_type: str = None):
        return f"output_{self.task_info.id}.{file_type if file_type else self.task_info.output_type}"
    
    def output_file_name(self, file_type: str = None):
        return FileNameFormatter.check_file_name_length(f"{self.task_info.file_name}.{file_type if file_type else self.task_info.output_type}")
    
    def flv_list_file(self):
        return f"flv_list_{self.task_info.id}.txt"
    
    def flv_list_path(self):
        return os.path.join(self.task_info.download_path, self.flv_list_file())
