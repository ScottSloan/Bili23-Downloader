import subprocess

from utils.common.data_type import Command, Process, RunCallback
from utils.common.enums import StatusCode
from utils.common.exception import GlobalException
from utils.config import Config

class FFmpeg:
    class Command:
        def get_merge_flv_command(info: dict):
            command = Command()

            return command.format()

        def get_cut_command(info: dict):
            command = Command()

            start_time = info.get("start_time")
            end_time = info.get("end_time")

            input_path = info.get("input_path")
            output_path = info.get("output_path")

            command.add(f'"{Config.Merge.ffmpeg_path}" -ss {start_time} -to {end_time} -i "{input_path}" -acodec copy -vcodec copy "{output_path}"')

            return command.format()
        
        def run(command: str, callback: RunCallback, cwd: str = None):
            def run_process():
                p = subprocess.run(command, shell = True, cwd = cwd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, stdin = subprocess.PIPE, text = True, encoding = "utf-8")

                process = Process()
                process.return_code = p.returncode
                process.output = p.stdout

                return process
            
            process = run_process()
                
            if not process.return_code:
                callback.onSuccess(process)
            else:
                raise GlobalException(code = StatusCode.FFmpeg.value, stack_trace = process.output, callback = callback.onError, args = (process,))
    
    @classmethod
    def cut(cls, info: dict, callback: RunCallback):
        command = cls.Command.get_cut_command(info)

        cls.Command.run(command, callback)