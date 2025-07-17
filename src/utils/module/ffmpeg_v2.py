import os
import re
import subprocess

from utils.common.data_type import Command, Process, Callback, DownloadTaskInfo, RealTimeCallback
from utils.common.enums import StatusCode, Platform, StreamType, OverrideOption
from utils.common.exception import GlobalException
from utils.common.file_name_v2 import FileNameFormatter
from utils.common.thread import Thread
from utils.common.regex import Regex
from utils.common.formatter import FormatUtils

from utils.config import Config
from utils.tool_v2 import UniversalTool

class FFmpeg:
    class Command:
        @staticmethod
        def get_merge_dash_command(task_info: DownloadTaskInfo):
            def convert_audio():
                if task_info.output_type == "flac":
                    command.add(FFmpeg.Command.get_convert_audio_command(task_info, "flac"))

                    return FFmpeg.Prop.dash_output_temp_file(task_info)
                else:
                    return FFmpeg.Prop.dash_audio_temp_file(task_info)

            command = Command()

            full_file_name = FFmpeg.Prop.full_file_name(task_info)

            match task_info.download_option.copy():
                case ["video", "audio"]:
                    command.add(FFmpeg.Command.get_merge_video_and_audio_command(task_info))
                    command.add(FFmpeg.Command.get_rename_command(FFmpeg.Prop.dash_output_temp_file(task_info), full_file_name))

                case ["video"]:
                    command.add(FFmpeg.Command.get_rename_command(FFmpeg.Prop.dash_video_temp_file(task_info), full_file_name))

                case ["audio"]:
                    src = convert_audio()
                    command.add(FFmpeg.Command.get_rename_command(src, full_file_name))

            return command.format()

        @staticmethod
        def get_merge_flv_command(task_info: DownloadTaskInfo):
            def create_flv_list_file():
                with open(os.path.join(task_info.download_path, flv_list_file), "w", encoding = "utf-8") as f:
                    f.write("\n".join([f"file flv_{task_info.id}_part{i + 1}.flv" for i in range(task_info.flv_video_count)]))

            command = Command()

            flv_list_file = FFmpeg.Prop.flv_list_file(task_info)
            flv_video_temp_file = FFmpeg.Prop.flv_video_temp_file(task_info)
            full_file_name = FFmpeg.Prop.full_file_name(task_info)

            if task_info.flv_video_count > 1:
                create_flv_list_file()

                command.add(f'"{Config.Merge.ffmpeg_path}" -y -f concat -safe 0 -i "{flv_list_file}" -c copy "{full_file_name}"')
            else:
                command.add(FFmpeg.Command.get_rename_command(flv_video_temp_file, full_file_name))

            return command.format()

        @staticmethod
        def get_merge_video_and_audio_command(task_info: DownloadTaskInfo):
            command = Command()

            video_temp_file = FFmpeg.Prop.dash_video_temp_file(task_info)
            audio_temp_file = FFmpeg.Prop.dash_audio_temp_file(task_info)
            output_temp_file = FFmpeg.Prop.dash_output_temp_file(task_info)

            command.add(f'"{Config.Merge.ffmpeg_path}" -y -i {video_temp_file} -i {audio_temp_file} -acodec copy -vcodec copy -strict experimental {output_temp_file}')

            return command.format()

        @staticmethod
        def get_convert_video_and_audio_command(info: dict):
            command = Command()

            vcodec = info.get("vcodec")
            crf = info.get("crf")
            vbitrate = info.get("vbitrate")

            acodec = info.get("acodec")
            asamplerate = info.get("asamplerate")
            achannel = info.get("achannel")
            abitrate = info.get("abitrate")

            input_path = info.get("input_path")
            output_path = info.get("output_path")

            raw = f'"{Config.Merge.ffmpeg_path}" -i "{input_path}" -c:v {vcodec} -c:a {acodec}'

            if vcodec != "copy":
                crf_arg = f"-crf {crf}" if crf else ""
                raw += f" {crf_arg} -b:v: {vbitrate}k"

            if acodec != "copy":
                raw += f" -ac {achannel} -ar {asamplerate} -b:a {abitrate}k"

            command.add(raw + f' "{output_path}"')

            return command.format()

        @staticmethod
        def get_convert_audio_command(task_info: DownloadTaskInfo, codec: str):
            command = Command()

            audio_temp_file = FFmpeg.Prop.dash_audio_temp_file(task_info)
            output_temp_file = FFmpeg.Prop.dash_output_temp_file(task_info)

            command.add(f'"{Config.Merge.ffmpeg_path}" -y -i {audio_temp_file} -c:a {codec} -q:a 0 {output_temp_file}')

            return command.format()

        @staticmethod
        def get_keep_files_command(task_info: DownloadTaskInfo):
            command = Command()

            if "video" in task_info.download_option:
                command.add(FFmpeg.Command.get_rename_command(FFmpeg.Prop.dash_video_temp_file(task_info), f"{task_info.file_name}_video.{task_info.video_type}"))

            if "audio" in task_info.download_option:
                command.add(FFmpeg.Command.get_rename_command(FFmpeg.Prop.dash_audio_temp_file(task_info), f"{task_info.file_name}_audio.{task_info.audio_type}"))

            return command.format()

        @staticmethod
        def get_cut_command(info: dict):
            command = Command()

            start_time = info.get("start_time")
            end_time = info.get("end_time")

            input_path = info.get("input_path")
            output_path = info.get("output_path")

            command.add(f'"{Config.Merge.ffmpeg_path}" -ss {start_time} -to {end_time} -i "{input_path}" -acodec copy -vcodec copy "{output_path}"')

            return command.format()
        
        @staticmethod
        def get_info_command(file_path: str):
            command = Command()

            command.add(f'"{Config.Merge.ffmpeg_path}" -i "{file_path}"')

            return command.format()

        @staticmethod
        def get_extract_audio_command(info: dict):
            command = Command()

            input_path = info.get("input_path")
            output_path = info.get("output_path")

            command.add(f'{Config.Merge.ffmpeg_path} -i "{input_path}" -vn -acodec copy "{output_path}"')

            return command.format()

        @staticmethod
        def get_rename_files_command(task_info: DownloadTaskInfo):
            command = Command()

            if "video" in task_info.download_option:
                command.add(FFmpeg.Command.get_rename_command(FFmpeg.Prop.dash_video_temp_file(task_info), f"{task_info.file_name}.{task_info.video_type}"))

            if "audio" in task_info.download_option:
                command.add(FFmpeg.Command.get_rename_command(FFmpeg.Prop.dash_audio_temp_file(task_info), f"{task_info.file_name}.{task_info.audio_type}"))

            return command.format()

        @staticmethod
        def get_test_command():
            command = Command()

            command.add(f'"{Config.Merge.ffmpeg_path}" -version')

            return command.format()

        @staticmethod
        def get_rename_command(src: str, dst: str):
            command = Command()

            rename_command = FFmpeg.Prop.rename_command()
            escape_character = FFmpeg.Prop.escape_character()

            command.add(f'{rename_command} "{src}" {escape_character}"{dst}"')

            return command.format()

        @staticmethod
        def run(command: str, callback: Callback, cwd: str = None, check = True):
            def run_process():
                p = subprocess.run(command, shell = True, cwd = cwd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, stdin = subprocess.PIPE, text = True, encoding = "utf-8")

                process = Process()
                process.return_code = p.returncode
                process.output = p.stdout

                return process
            
            def get_output():
                return f"{process.output}\n\nCommand:\n{command}"
            
            process = run_process()
                
            if not process.return_code or not check:
                callback.onSuccess(process)
            else:
                raise GlobalException(code = StatusCode.CallError.value, stack_trace = get_output(), callback = callback.onError, args = (process,))

        @staticmethod
        def run_realtime(command: str, callback: RealTimeCallback, cwd: str = None):
            def run_process():
                p = subprocess.Popen(command, shell = True, cwd = cwd, stdout = subprocess.PIPE, stdin = subprocess.PIPE, stderr = subprocess.STDOUT, text = True, universal_newlines = True, bufsize = 1, encoding = "utf-8")
                
                temp_output = []

                while True:
                    if p.poll() is None:
                        output = p.stdout.readline()

                        temp_output.append(output)

                        callback.onReadOutput(output)
                    
                    else:
                        break

                process = Process()
                process.return_code = p.returncode
                process.output = "".join(temp_output)

                p.stdout.close()

                return process

            def get_output():
                return f"{process.output}\n\nCommand:\n{command}"

            process = run_process()

            if not process.return_code:
                callback.onSuccess(process)
            else:
                raise GlobalException(code = StatusCode.CallError.value, stack_trace = get_output(), callback = callback.onError, args = (process, ))
            
    class Env:
        @staticmethod
        def check_file(path: str):
            return os.path.isfile(path) and os.access(path, os.X_OK)
        
        @staticmethod
        def get_env_path():
            path_env = os.environ.get("PATH", "")

            for directory in path_env.split(os.pathsep):
                possible_path = os.path.join(directory, FFmpeg.Prop.ffmpeg_file())

                if FFmpeg.Env.check_file(possible_path):
                    return possible_path

        @staticmethod
        def get_cwd_path():
            possible_path = os.path.join(os.getcwd(), FFmpeg.Prop.ffmpeg_file())
            
            if FFmpeg.Env.check_file(possible_path):
                return possible_path

        @staticmethod
        def get_ffmpeg_path():
            return {
                "env_path": FFmpeg.Env.get_env_path(),
                "cwd_path": FFmpeg.Env.get_cwd_path(),
            }

        @classmethod
        def detect(cls):
            ffmpeg_path = FFmpeg.Env.get_ffmpeg_path()

            env_path, cwd_path = ffmpeg_path["env_path"], ffmpeg_path["cwd_path"]
            
            if not Config.Merge.ffmpeg_path:
                Config.Merge.ffmpeg_path = env_path if env_path else Config.Merge.ffmpeg_path
                Config.Merge.ffmpeg_path = cwd_path if cwd_path else Config.Merge.ffmpeg_path
            else:
                if not cls.check_file(Config.Merge.ffmpeg_path):
                    Config.Merge.ffmpeg_path = cwd_path

        @staticmethod
        def check_availability(callback: Callback):
            command = FFmpeg.Command.get_test_command()

            FFmpeg.Command.run(command, callback)

    class Utils:
        temp_duration = 0

        @staticmethod
        def cut(info: dict, callback: Callback):
            command = FFmpeg.Command.get_cut_command(info)

            FFmpeg.Command.run(command, callback)

        @classmethod
        def merge(cls, task_info: DownloadTaskInfo, callback: Callback):
            match StreamType(task_info.stream_type):
                case StreamType.Dash:
                    command = FFmpeg.Command.get_merge_dash_command(task_info)

                case StreamType.Flv:
                    command = FFmpeg.Command.get_merge_flv_command(task_info)

            cls.check_file_existance(FFmpeg.Prop.full_file_path(task_info), callback)

            FFmpeg.Command.run(command, callback, cwd = task_info.download_path)

        @staticmethod
        def convert(info: dict, callback: RealTimeCallback):
            command = FFmpeg.Command.get_convert_video_and_audio_command(info)

            FFmpeg.Command.run_realtime(command, callback)

        @classmethod
        def info(cls, file_path: str, callback: Callback):
            command = FFmpeg.Command.get_info_command(file_path)

            FFmpeg.Command.run(command, callback, check = False)

        @staticmethod
        def extract_audio(info: dict, callback: Callback):
            command = FFmpeg.Command.get_extract_audio_command(info)

            FFmpeg.Command.run(command, callback)

        @staticmethod
        def parse_media_info(output: str):
            duration_info = Regex.re_findall_in_group(r"Duration: (([\d:.]+))", output, 1)

            start_info = Regex.re_findall_in_group(r"start: (([\d.]+))", output, 1)

            bitrate_info = Regex.re_findall_in_group(r"bitrate: ((\d* kb\/s))", output, 1)
        
            video_stream_info = Regex.re_match_in_group(r"Video: (.*)", output, 4)

            fps_info = Regex.re_findall_in_group(r"((\d+(?:.\d+)? fps))", output, 1)

            audio_stream_info = Regex.re_match_in_group(r"Audio: (.*)", output, 5)

            return {
                "duration": duration_info[0],
                "start": start_info[0],
                "bitrate": bitrate_info[0],
                "vcodec": video_stream_info[0],
                "vformat": video_stream_info[1],
                "resolution": video_stream_info[2],
                "vbitrate": video_stream_info[3],
                "fps": fps_info[0],
                "acodec": audio_stream_info[0],
                "samplerate": audio_stream_info[1],
                "channel": audio_stream_info[2],
                "sampleformat": audio_stream_info[3],
                "abitrate": audio_stream_info[4]
            }

        @classmethod
        def parse_progress_info(cls, output: str):
            def get_time(pattern: str):
                match = re.search(pattern, output)

                if match:
                    hours, minutes, seconds = map(int, match.groups())
                    return hours * 3600 + minutes * 60 + seconds
            
            def get_frame(pattern: str):
                result = re.findall(pattern, output)

                if result:
                    return [result[0]]
                else:
                    return ["--"]

            def get_size(pattern: str):
                result = re.findall(pattern, output)

                if result:
                    size = int(result[0][0])
                    return [FormatUtils.format_size(int(size * 1024))]
                else:
                    return ["--"]

            duration = get_time(r"Duration: (\d{2}):(\d{2}):(\d{2})")

            if duration:
                cls.temp_duration = duration

            current_time = get_time(r"time=(\d{2}):(\d{2}):(\d{2})")
            frame_info = get_frame(r"frame=\s*(\d+)")
            size_info = get_size(r"size=\s*(\d+)(KiB|kB)")

            speed_info = Regex.re_findall_in_group(r"speed=\s*((\d+\.\d+x))", output, 1)

            return {
                "progress": int(current_time / cls.temp_duration * 100) if cls.temp_duration and current_time else 0,
                "frame": frame_info[0],
                "size": size_info[0],
                "speed": speed_info[0]
            }

        @staticmethod
        def clear_temp_files(task_info: DownloadTaskInfo):
            def worker():
                def dash():
                    if "video" in task_info.download_option:
                        temp_files.append(os.path.join(task_info.download_path, FFmpeg.Prop.dash_video_temp_file(task_info)))

                    if "audio" in task_info.download_option:
                        temp_files.append(os.path.join(task_info.download_path, FFmpeg.Prop.dash_audio_temp_file(task_info)))

                    temp_files.append(FFmpeg.Prop.dash_output_temp_file(task_info))

                def flv():
                    temp_files.append(FFmpeg.Prop.flv_list_file(task_info))
                    temp_files.append(FFmpeg.Prop.flv_video_temp_file(task_info))
                    temp_files.extend([os.path.join(task_info.download_path, f"flv_{task_info.id}_part{i + 1}") for i in range(task_info.flv_video_count)])

                temp_files = []

                match StreamType(task_info.stream_type):
                    case StreamType.Dash:
                        dash()

                        if Config.Merge.keep_original_files and os.path.exists(os.path.join(task_info.download_path, FFmpeg.Prop.dash_video_temp_file(task_info))):
                            FFmpeg.Utils.keep_original_files(task_info)

                    case StreamType.Flv:
                        flv()

                UniversalTool.remove_files(temp_files)

            Thread(target = worker).start()
        
        @classmethod
        def keep_original_files(cls, task_info: DownloadTaskInfo):
            callback = cls.get_empty_callback()
            
            command = FFmpeg.Command.get_keep_files_command(task_info)

            FFmpeg.Command.run(command, callback, cwd = task_info.download_path)
        
        @classmethod
        def rename_files(cls, task_info: DownloadTaskInfo):
            callback = cls.get_empty_callback()
            
            command = FFmpeg.Command.get_rename_files_command(task_info)

            FFmpeg.Command.run(command, callback, cwd = task_info.download_path)

        @classmethod
        def check_file_existance(cls, dst: str, callback: Callback):
            if os.path.exists(dst):
                match OverrideOption(Config.Merge.override_option):
                    case OverrideOption.Rename:
                        base, ext = os.path.splitext(os.path.basename(dst))

                        command = FFmpeg.Command.get_rename_command(dst, f"{base}_1{ext}")

                        FFmpeg.Command.run(command, callback)

                    case OverrideOption.Override:
                        UniversalTool.remove_files([dst])

        @staticmethod
        def get_empty_callback():
            class callback(Callback):
                @staticmethod
                def onSuccess(*process):
                    pass
                
                @staticmethod
                def onError(*process):
                    pass

            return callback

    class Prop:
        @staticmethod
        def ffmpeg_file():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return "ffmpeg.exe"
                
                case Platform.Linux | Platform.macOS:
                    return "ffmpeg"
        
        @staticmethod
        def dash_video_temp_file(task_info: DownloadTaskInfo):
            return f"video_{task_info.id}.{task_info.video_type}"

        @staticmethod
        def dash_audio_temp_file(task_info: DownloadTaskInfo):
            return f"audio_{task_info.id}.{task_info.audio_type}"
        
        @staticmethod
        def dash_output_temp_file(task_info: DownloadTaskInfo):
            return f"output_{task_info.id}.{task_info.output_type}"
        
        @staticmethod
        def flv_video_temp_file(task_info: DownloadTaskInfo):
            return f"flv_{task_info.id}.flv"

        @staticmethod
        def flv_list_file(task_info: DownloadTaskInfo):
            return f"flv_list_{task_info.id}.txt"

        @staticmethod
        def output_file_name(task_info: DownloadTaskInfo):
            return FileNameFormatter.format_file_basename(task_info)

        @staticmethod
        def full_file_name(task_info: DownloadTaskInfo):
            return FileNameFormatter.check_file_name_length(f"{task_info.file_name}.{task_info.output_type}")

        @staticmethod
        def full_file_path(task_info: DownloadTaskInfo):
            return os.path.join(task_info.download_path, FFmpeg.Prop.full_file_name(task_info))

        @staticmethod
        def escape_character():
            match Platform(Config.Sys.platform):
                case Platform.Windows | Platform.macOS:
                    return ""
                
                case Platform.Linux:
                    return "-- "
        
        @staticmethod
        def rename_command():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return "rename"
                
                case Platform.Linux | Platform.macOS:
                    return "mv"