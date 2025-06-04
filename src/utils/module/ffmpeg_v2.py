import os
import subprocess

from utils.common.data_type import Command, Process, Callback, DownloadTaskInfo, MergeCallback
from utils.common.enums import StatusCode, Platform, StreamType, OverrideOption
from utils.common.exception import GlobalException
from utils.common.file_name import FileNameManager
from utils.common.download_path import DownloadPathManager

from utils.config import Config
from utils.tool_v2 import UniversalTool

class FFmpeg:
    class Command:
        def get_merge_dash_command(task_info: DownloadTaskInfo):
            def convert_audio():
                if task_info.output_type == "m4a" and Config.Merge.m4a_to_mp3:
                    command.add(FFmpeg.Command.get_convert_audio_command(task_info, "libmp3lame"))

                    return FFmpeg.Prop.dash_output_temp_file(task_info)

                elif task_info.output_type == "flac":
                    command.add(FFmpeg.Command.get_convert_audio_command(task_info, "flac"))

                    return FFmpeg.Prop.dash_output_temp_file(task_info)
                else:
                    return FFmpeg.Prop.dash_audio_temp_file(task_info)

            command = Command()

            match task_info.download_option.copy():
                case ["video", "audio"]:
                    command.add(FFmpeg.Command.get_merge_video_and_audio_command(task_info))
                    command.add(FFmpeg.Command.get_rename_command(FFmpeg.Prop.dash_output_temp_file(task_info), FFmpeg.Prop.full_file_name(task_info)))

                case ["video"]:
                    command.add(FFmpeg.Command.get_rename_command(FFmpeg.Prop.dash_video_temp_file(task_info), FFmpeg.Prop.full_file_name(task_info)))

                case ["audio"]:
                    src = convert_audio()
                    command.add(FFmpeg.Command.get_rename_command(src, FFmpeg.Prop.full_file_name(task_info)))

            return command.format()

        def get_merge_flv_command(task_info: DownloadTaskInfo):
            command = Command()

            return command.format()

        def get_merge_video_and_audio_command(task_info: DownloadTaskInfo):
            command = Command()

            video_temp_file = FFmpeg.Prop.dash_video_temp_file(task_info)
            audio_temp_file = FFmpeg.Prop.dash_audio_temp_file(task_info)
            output_temp_file = FFmpeg.Prop.dash_output_temp_file(task_info)

            command.add(f'"{Config.Merge.ffmpeg_path}" -y -i {video_temp_file} -i {audio_temp_file} -acodec copy -vcodec copy -strict experimental {output_temp_file}')

            return command.format()

        def get_convert_audio_command(task_info: DownloadTaskInfo, codec: str):
            command = Command()

            audio_temp_file = FFmpeg.Prop.dash_audio_temp_file(task_info)
            output_temp_file = FFmpeg.Prop.dash_output_temp_file(task_info)

            command.add(f'"{Config.Merge.ffmpeg_path}" -y -i {audio_temp_file} -c:a {codec} -q:a 0 {output_temp_file}')

            return command.format()

        def get_cut_command(info: dict):
            command = Command()

            start_time = info.get("start_time")
            end_time = info.get("end_time")

            input_path = info.get("input_path")
            output_path = info.get("output_path")

            command.add(f'"{Config.Merge.ffmpeg_path}" -ss {start_time} -to {end_time} -i "{input_path}" -acodec copy -vcodec copy "{output_path}"')

            return command.format()
        
        def get_test_command():
            command = Command()

            command.add(f'"{Config.Merge.ffmpeg_path}" -version')

            return command.format()

        def get_rename_command(src: str, dst: str):
            command = Command()

            rename_command = FFmpeg.Prop.rename_command()
            escape_character = FFmpeg.Prop.escape_character()

            command.add(f'{rename_command} "{src}" {escape_character}"{dst}"')

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
                possible_path = os.path.join(directory, FFmpeg.Prop.ffmpeg_file())

                if FFmpeg.Env.check_file(possible_path):
                    return possible_path

        def get_cwd_path():
            possible_path = os.path.join(os.getcwd(), FFmpeg.Prop.ffmpeg_file())
            
            if FFmpeg.Env.check_file(possible_path):
                return possible_path

        def get_ffmpeg_path():
            return {
                "env_path": FFmpeg.Env.get_env_path(),
                "cwd_path": FFmpeg.Env.get_cwd_path(),
            }

        def detect():
            if not Config.Merge.ffmpeg_path:
                ffmpeg_path = FFmpeg.Env.get_ffmpeg_path()

                env_path, cwd_path = ffmpeg_path["env_path"], ffmpeg_path["cwd_path"]

                Config.Merge.ffmpeg_path = env_path if env_path else Config.Merge.ffmpeg_path
                Config.Merge.ffmpeg_path = cwd_path if cwd_path else Config.Merge.ffmpeg_path

        def check_availability():
            class callback(Callback):
                def onSuccess(*args, **kwargs):
                    Config.Merge.ffmpeg_available = True

                def onError(*args, **kwargs):
                    Config.Merge.ffmpeg_available = False

            command = FFmpeg.Command.get_test_command()

            FFmpeg.Command.run(command, callback)

    class Utils:
        def cut(info: dict, callback: Callback):
            command = FFmpeg.Command.get_cut_command(info)

            FFmpeg.Command.run(command, callback)

        def merge(task_info: DownloadTaskInfo, callback: MergeCallback):
            def check_file_existance():
                index = 0
                path =  os.path.join(FFmpeg.Prop.download_path(), FFmpeg.Prop.full_file_name(task_info))

                while os.path.exists(path):
                    match OverrideOption(Config.Merge.override_option):
                        case OverrideOption.Rename:
                            index += 1

                            task_info.suffix = f"_{index}"

                        case OverrideOption.Override:
                            UniversalTool.remove_files([path])
                
                callback.onUpdateSuffix()

            match StreamType(task_info.stream_type):
                case StreamType.Dash:
                    command = FFmpeg.Command.get_merge_dash_command()

                case StreamType.Flv:
                    command = FFmpeg.Command.get_merge_flv_command()

            check_file_existance()

            FFmpeg.Command.run(command, callback, FFmpeg.Prop.download_path(task_info))

    class Prop:
        def ffmpeg_file():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return "ffmpeg.exe"
                
                case Platform.Linux | Platform.macOS:
                    return "ffmpeg"
        
        def download_path(task_info: DownloadTaskInfo):
            return DownloadPathManager.get_download_path(task_info)

        def dash_video_temp_file(task_info: DownloadTaskInfo):
            return f"video_{task_info.id}.{task_info.video_type}"

        def dash_audio_temp_file(task_info: DownloadTaskInfo):
            return f"audio_{task_info.id}.{task_info.audio_type}"
        
        def dash_output_temp_file(task_info: DownloadTaskInfo):
            return f"output_{task_info.id}.{task_info.output_type}"
        
        def output_file_name(task_info: DownloadTaskInfo):
            file_name_mgr = FileNameManager(task_info)

            return file_name_mgr.get_full_file_name(Config.Advanced.file_name_template, Config.Advanced.auto_adjust_field)

        def full_file_name(task_info: DownloadTaskInfo):
            output_file_name = FFmpeg.Prop.output_file_name(task_info)

            return FileNameManager.check_file_name_legnth(f"{output_file_name}{task_info.suffix}.{task_info.output_type}")

        def escape_character():
            match Platform(Config.Sys.platform):
                case Platform.Windows | Platform.macOS:
                    return ""
                
                case Platform.Linux:
                    return "-- "
                
        def rename_command():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return "rename"
                
                case Platform.Linux | Platform.macOS:
                    return "mv"