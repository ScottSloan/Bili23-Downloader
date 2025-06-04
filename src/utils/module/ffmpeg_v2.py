import os
import subprocess

from utils.common.data_type import Command, Process, Callback
from utils.common.enums import StatusCode, Platform
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
        
        def run(command: str, callback: Callback, cwd: str = None):
            def run_process():
                p = subprocess.run(command, shell = True, cwd = cwd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, stdin = subprocess.PIPE, text = True, encoding = "utf-8")

                process = Process()
                process.return_code = p.returncode
                process.output = p.stdout

                return process
            
            process = run_process()
                
            if not process.return_code:
                callback.onSuccess(pocess = process)
            else:
                raise GlobalException(code = StatusCode.FFmpeg.value, stack_trace = process.output, callback = callback.onError, args = (process, ))
    
    class Env:
        def check_file(path: str):
            return os.path.isfile(path) and os.access(path, os.X_OK)
        
        def get_env_path():
            path_env = os.environ.get("PATH", "")

            for directory in path_env.split(os.pathsep):
                possible_path = os.path.join(directory, FFmpeg.ffmpeg_file)

                if FFmpeg.Env.check_file(possible_path):
                    return possible_path

        def get_cwd_path():
            possible_path = os.path.join(os.getcwd(), FFmpeg.ffmpeg_file)
            
            if FFmpeg.Env.check_file(possible_path):
                return possible_path

        def get_ffmpeg_path():
            pass
    
    class Utils:
        def cut(info: dict, callback: Callback):
            command = FFmpeg.Command.get_cut_command(info)

            FFmpeg.Command.run(command, callback)

    @property
    def ffmpeg_file():
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return "ffmpeg.exe"
            
            case Platform.Linux | Platform.macOS:
                return "ffmpeg"