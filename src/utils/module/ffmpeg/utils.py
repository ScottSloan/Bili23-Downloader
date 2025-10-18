import subprocess

from utils.common.enums import StreamType, StatusCode
from utils.common.exception import GlobalException

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.model.data_type import Process, Command
from utils.common.model.callback import Callback

from utils.module.ffmpeg.command import FFCommand

class FFUtils:
    @staticmethod
    def run(command: Command, callback: Callback, cwd: str = None, check: bool = True):
        process = Process()

        p = subprocess.run(command.format(), shell = True, cwd = cwd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, stdin = subprocess.PIPE, text = True, encoding = "utf-8")\
        
        process.return_code = p.returncode
        process.output = p.stdout

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
                pass

            case StreamType.Mp4:
                pass

        cls.run(command, callback, cwd = task_info.download_path)
