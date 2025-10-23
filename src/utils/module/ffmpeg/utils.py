import subprocess

from utils.common.enums import StreamType, StatusCode
from utils.common.exception import GlobalException
from utils.common.thread import Thread
from utils.common.io.file import File

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.model.data_type import Process, Command
from utils.common.model.callback import Callback

from utils.module.ffmpeg.command import FFCommand
from utils.module.ffmpeg.prop import FFProp

class FFUtils:
    @staticmethod
    def run(command: Command, callback: Callback, cwd: str = None, check: bool = True):
        command_line = command.format()

        process = Process()

        if command_line:
            p = subprocess.run(command.format(), shell = True, cwd = cwd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, stdin = subprocess.PIPE, text = True, encoding = "utf-8")\
            
            process.return_code = p.returncode
            process.output = p.stdout
        else:
            process.return_code = 0
            process.output = ""

        if check:
            if not process.return_code:
                command.rename()
                command.remove()

                callback.onSuccess(process)
            else:
                raise GlobalException(code = StatusCode.CallError.value, stack_trace = f"{process.output}\n\nCommand:\n{command}", callback = callback.onError, args = (process,))
        else:
            callback.onSuccess(process)

    @classmethod
    def merge(cls, task_info: DownloadTaskInfo, callback: Callback):
        match StreamType(task_info.stream_type):
            case StreamType.Dash:
                command = FFCommand.get_merge_dash_command(task_info)

            case StreamType.Flv:
                command = FFCommand.get_merge_flv_command(task_info)

            case StreamType.Mp4:
                command = FFCommand.get_merge_mp4_command(task_info)

        cls.run(command, callback, cwd = task_info.download_path)
    
    @staticmethod
    def clear_temp_files(task_info: DownloadTaskInfo):
        temp_files = []

        prop = FFProp(task_info)
        
        try:
            stream_type = StreamType(task_info.stream_type)
        except ValueError:
            stream_type = StreamType.Null
            
        match StreamType:
            case StreamType.Dash:
                if "video" in task_info.download_option:
                    temp_files.append(prop.video_temp_file())

                if "audio" in task_info.download_option:
                    temp_files.append(prop.audio_temp_file())

                temp_files.append(prop.output_temp_file())

            case StreamType.Flv:
                if task_info.flv_video_count > 1:
                    temp_files.append(prop.flv_list_file())
                    temp_files.extend([f"flv_{task_info.id}_part{i + 1}.flv" for i in range(task_info.flv_video_count)])
                else:
                    temp_files.append(prop.flv_temp_file())

                temp_files.append(prop.output_temp_file())

            case StreamType.Mp4:
                temp_files.append(prop.video_temp_file())

        Thread(target = File.remove_files_ex, args = (temp_files, task_info.download_path)).start()
